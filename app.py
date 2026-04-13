import streamlit as st
import pandas as pd
from datetime import date
import hashlib
from supabase import create_client

# --------------------------
# CONFIG & CONEXIÓN
# --------------------------
st.set_page_config(page_title="App Contable PRO", layout="wide")

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error("Error de conexión: Verifica tus secrets de Supabase.")

# --------------------------
# LÓGICA DE DATOS
# --------------------------
def hash_password(pwd): return hashlib.sha256(pwd.encode()).hexdigest()

def login(username, password):
    res = supabase.table("usuarios").select("*").eq("username", username).eq("password", hash_password(password)).execute()
    return res.data

def guardar_movimiento(user, data):
    data["username"] = user
    supabase.table("movimientos").insert(data).execute()

def obtener_movimientos(user):
    res = supabase.table("movimientos").select("*").eq("username", user).execute()
    return pd.DataFrame(res.data)

def obtener_inventario(user):
    res = supabase.table("inventario").select("*").eq("username", user).execute()
    return pd.DataFrame(res.data)

def actualizar_stock(user, producto, cantidad):
    inv = obtener_inventario(user)
    nueva_cant = inv[inv["producto"] == producto].iloc[0]["cantidad"] - cantidad
    supabase.table("inventario").update({"cantidad": nueva_cant}).eq("username", user).eq("producto", producto).execute()

# --------------------------
# PLAN DE CUENTAS
# --------------------------
cuentas = {
    "activo": ["bancos", "inventarios", "cuentas por cobrar", "propiedad planta y equipo"],
    "pasivo": ["proveedores", "obligaciones financieras", "cuentas por pagar", "pasivos financieros"],
    "patrimonio": ["capital", "utilidades acumuladas"],
    "ingreso": ["ventas", "otros ingresos"],
    "costo": ["costo de ventas"],
    "gasto": ["nómina", "arriendo", "servicios", "depreciación"]
}

def calcular_valor(row):
    if row["tipo_cuenta"] in ["activo", "gasto", "costo"]:
        return row["valor"] if row["naturaleza"] == "debito" else -row["valor"]
    return row["valor"] if row["naturaleza"] == "credito" else -row["valor"]

# --------------------------
# INTERFAZ (SESSION STATE)
# --------------------------
if "user" not in st.session_state: st.session_state.user = None

if not st.session_state.user:
    st.title("🔐 Acceso")
    user = st.text_input("Usuario")
    pwd = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if login(user, pwd):
            st.session_state.user = user
            st.rerun()
        else: st.error("Fallo de inicio")
else:
    st.sidebar.success(f"Usuario: {st.session_state.user}")
    if st.sidebar.button("Salir"):
        st.session_state.user = None
        st.rerun()
    
    menu = st.sidebar.selectbox("Navegación", ["Registro", "Inventario", "Reportes"])

    # --- REGISTRO ---
    if menu == "Registro":
        st.title("📥 Nuevo Asiento")
        with st.form("f"):
            tipo = st.selectbox("Tipo", list(cuentas.keys()))
            cta = st.selectbox("Cuenta", cuentas[tipo])
            val = st.number_input("Monto", min_value=0.0)
            nat = st.selectbox("Naturaleza", ["debito", "credito"])
            if st.form_submit_button("Guardar"):
                guardar_movimiento(st.session_state.user, {"fecha": str(date.today()), "tipo_cuenta": tipo, "cuenta": cta, "valor": val, "naturaleza": nat})
                st.success("Registrado")

    # --- INVENTARIO ---
    elif menu == "Inventario":
        st.title("📦 Almacén")
        df_inv = obtener_inventario(st.session_state.user)
        if not df_inv.empty:
            st.dataframe(df_inv)
            st.subheader("Vender Producto")
            p_sel = st.selectbox("Producto", df_inv["producto"])
            c_v = st.number_input("Cant", min_value=1.0)
            if st.button("Vender"):
                row = df_inv[df_inv["producto"] == p_sel].iloc[0]
                if row["cantidad"] >= c_v:
                    actualizar_stock(st.session_state.user, p_sel, c_v)
                    ing, cos = (c_v * row["precio"]), (c_v * row["costo"])
                    asientos = [("ingreso","ventas",ing,"credito"), ("activo","bancos",ing,"debito"), ("costo","costo de ventas",cos,"debito"), ("activo","inventarios",cos,"credito")]
                    for t, c, v, n in asientos:
                        guardar_movimiento(st.session_state.user, {"fecha":str(date.today()), "tipo_cuenta":t, "cuenta":c, "valor":v, "naturaleza":n})
                    st.success("Venta Exitosa")
                    st.rerun()
    
    # --- REPORTES (ESTADOS FINANCIEROS DESGLOSADOS) ---
    elif menu == "Reportes":
        st.title("📊 Estados Financieros Detallados")
        df = obtener_movimientos(st.session_state.user)
        
        if df.empty:
            st.warning("No hay datos para mostrar.")
        else:
            df["val_adj"] = df.apply(calcular_valor, axis=1)
            t1, t2, t3 = st.tabs(["📉 Estado de Resultados", "⚖️ Situación Financiera", "💸 Flujo de Efectivo"])
            
            # --- 1. ESTADO DE RESULTADOS ---
            with t1:
                st.subheader("Estado de Resultados Integral")
                
                # Desglose de cuentas
                df_res = df[df["tipo_cuenta"].isin(["ingreso", "costo", "gasto"])]
                res_resumen = df_res.groupby(["tipo_cuenta", "cuenta"])["val_adj"].sum().reset_index()
                
                ing_t = res_resumen[res_resumen["tipo_cuenta"]=="ingreso"]["val_adj"].sum()
                cos_t = res_resumen[res_resumen["tipo_cuenta"]=="costo"]["val_adj"].sum()
                gas_t = res_resumen[res_resumen["tipo_cuenta"]=="gasto"]["val_adj"].sum()
                utilidad_neta = ing_t - cos_t - gas_t
                
                st.dataframe(res_resumen.rename(columns={"tipo_cuenta":"Categoría", "cuenta":"Cuenta", "val_adj":"Saldo"}), use_container_width=True)
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Ingresos Totales", f"$ {ing_t:,.2f}")
                c2.metric("Costos/Gastos", f"$ {cos_t + gas_t:,.2f}")
                c3.metric("Utilidad Neta", f"$ {utilidad_neta:,.2f}", delta_color="normal")

            # --- 2. SITUACIÓN FINANCIERA (BALANCE) ---
            with t2:
                st.subheader("Estado de Situación Financiera")
                
                # Desglose de Activos, Pasivos y Patrimonio
                df_bal = df[df["tipo_cuenta"].isin(["activo", "pasivo", "patrimonio"])]
                bal_resumen = df_bal.groupby(["tipo_cuenta", "cuenta"])["val_adj"].sum().reset_index()
                
                act_t = bal_resumen[bal_resumen["tipo_cuenta"]=="activo"]["val_adj"].sum()
                pas_t = bal_resumen[bal_resumen["tipo_cuenta"]=="pasivo"]["val_adj"].sum()
                pat_t = bal_resumen[bal_resumen["tipo_cuenta"]=="patrimonio"]["val_adj"].sum() + utilidad_neta
                
                col_act, col_pas = st.columns(2)
                
                with col_act:
                    st.write("**ACTIVOS**")
                    st.table(bal_resumen[bal_resumen["tipo_cuenta"]=="activo"][["cuenta", "val_adj"]].rename(columns={"cuenta":"Cuenta", "val_adj":"Monto"}))
                    st.write(f"**Total Activos: $ {act_t:,.2f}**")
                
                with col_pas:
                    st.write("**PASIVOS**")
                    st.table(bal_resumen[bal_resumen["tipo_cuenta"]=="pasivo"][["cuenta", "val_adj"]])
                    st.write(f"**Total Pasivos: $ {pas_t:,.2f}**")
                    st.divider()
                    st.write("**PATRIMONIO**")
                    st.table(bal_resumen[bal_resumen["tipo_cuenta"]=="patrimonio"][["cuenta", "val_adj"]])
                    st.write(f"Utilidad del Ejercicio: $ {utilidad_neta:,.2f}")
                    st.write(f"**Total Patrimonio: $ {pat_t:,.2f}**")
                
                st.divider()
                st.info(f"Ecuación: Activo ({act_t:,.2f}) = Pasivo + Patrimonio ({(pas_t + pat_t):,.2f})")
                if abs(act_t - (pas_t + pat_t)) < 0.01: st.success("Balance Cuadrado ✅")
                else: st.error("Balance Descuadrado ❌")

            # --- 3. FLUJO DE EFECTIVO ---
            with t3:
                st.subheader("Estado de Flujo de Efectivo (Método Directo)")
                # Filtramos solo movimientos que afectaron 'bancos'
                df_efectivo = df[df["cuenta"] == "bancos"].copy()
                
                if not df_efectivo.empty:
                    df_efectivo["Tipo"] = df_efectivo["naturaleza"].apply(lambda x: "Entrada" if x=="debito" else "Salida")
                    entradas = df_efectivo[df_efectivo["Tipo"]=="Entrada"]["valor"].sum()
                    salidas = df_efectivo[df_efectivo["Tipo"]=="Salida"]["valor"].sum()
                    
                    st.write("**Detalle de Movimientos de Caja:**")
                    st.dataframe(df_efectivo[["fecha", "Tipo", "valor"]].sort_values("fecha"), use_container_width=True)
                    
                    c1, c2, c3 = st.columns(3)
                    c1.write(f"Total Entradas: $ {entradas:,.2f}")
                    c2.write(f"Total Salidas: $ {salidas:,.2f}")
                    c3.subheader(f"Saldo Final: $ {entradas - salidas:,.2f}")
                else:
                    st.info("No hay movimientos de efectivo registrados en la cuenta 'bancos'.")