import streamlit as st
import pandas as pd
from datetime import date
import hashlib
from supabase import create_client

# --------------------------
# CONFIG
# --------------------------
st.set_page_config(page_title="App Contable PRO", layout="wide")

# --------------------------
# CONEXIÓN SUPABASE
# --------------------------
# Asegúrate de tener estos secretos configurados en Streamlit Cloud o en tu archivo .streamlit/secrets.toml
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --------------------------
# FUNCIONES DE DATOS
# --------------------------
def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def crear_usuario(username, password):
    supabase.table("usuarios").insert({
        "username": username,
        "password": hash_password(password)
    }).execute()

def login(username, password):
    res = supabase.table("usuarios")\
        .select("*")\
        .eq("username", username)\
        .eq("password", hash_password(password))\
        .execute()
    return res.data

def guardar_movimiento(user, data):
    data["username"] = user
    supabase.table("movimientos").insert(data).execute()

def obtener_movimientos(user):
    res = supabase.table("movimientos")\
        .select("*")\
        .eq("username", user)\
        .execute()
    return pd.DataFrame(res.data)

def obtener_inventario(user):
    res = supabase.table("inventario")\
        .select("*")\
        .eq("username", user)\
        .execute()
    return pd.DataFrame(res.data)

def guardar_producto(user, producto, cantidad, costo, precio):
    supabase.table("inventario").insert({
        "username": user,
        "producto": producto,
        "cantidad": cantidad,
        "costo": costo,
        "precio": precio
    }).execute()

def actualizar_stock(user, producto, cantidad):
    inv = obtener_inventario(user)
    row = inv[inv["producto"] == producto].iloc[0]
    nueva_cantidad = row["cantidad"] - cantidad
    supabase.table("inventario")\
        .update({"cantidad": nueva_cantidad})\
        .eq("username", user)\
        .eq("producto", producto)\
        .execute()

# --------------------------
# LÓGICA CONTABLE
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
    else:
        return row["valor"] if row["naturaleza"] == "credito" else -row["valor"]

# --------------------------
# INTERFAZ DE USUARIO (SESSION STATE)
# --------------------------
if "user" not in st.session_state:
    st.session_state.user = None

# --------------------------
# LOGIN / REGISTRO
# --------------------------
if not st.session_state.user:
    st.title("🔐 Acceso al Sistema")
    col_l, col_r = st.columns(2)
    
    with col_l:
        opcion = st.radio("Acción", ["Login", "Registro"])
        user = st.text_input("Usuario")
        pwd = st.text_input("Contraseña", type="password")

        if opcion == "Registro":
            if st.button("Crear cuenta"):
                crear_usuario(user, pwd)
                st.success("Usuario registrado con éxito")

        if opcion == "Login":
            if st.button("Entrar"):
                if login(user, pwd):
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("Error: Usuario o contraseña incorrectos")

# --------------------------
# APP PRINCIPAL
# --------------------------
else:
    st.sidebar.title(f"Bienvenido, {st.session_state.user}")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.user = None
        st.rerun()

    menu = st.sidebar.selectbox("Menú Principal", ["Registro", "Inventario", "Reportes"])

    # 1. REGISTRO CONTABLE
    if menu == "Registro":
        st.title("📥 Registro de Movimientos")
        with st.form("form_registro"):
            tipo = st.selectbox("Tipo de cuenta", list(cuentas.keys()))
            cuenta = st.selectbox("Subcuenta", cuentas[tipo])
            valor = st.number_input("Monto", min_value=0.0, format="%.2f")
            naturaleza = st.selectbox("Naturaleza", ["debito", "credito"])
            fecha = st.date_input("Fecha de operación")
            enviar = st.form_submit_button("Registrar Movimiento")

            if enviar:
                guardar_movimiento(st.session_state.user, {
                    "fecha": str(fecha),
                    "tipo_cuenta": tipo,
                    "cuenta": cuenta,
                    "valor": valor,
                    "naturaleza": naturaleza
                })
                st.success(f"Asiento registrado: {cuenta} por {valor}")

    # 2. INVENTARIO
    elif menu == "Inventario":
        st.title("📦 Gestión de Inventarios")
        
        with st.expander("🆕 Registrar Nuevo Producto"):
            c1, c2 = st.columns(2)
            prod = c1.text_input("Nombre")
            cant = c2.number_input("Stock Inicial", min_value=0.0)
            costo = c1.number_input("Costo Unitario", min_value=0.0)
            precio = c2.number_input("Precio Venta", min_value=0.0)
            if st.button("Agregar a Almacén"):
                guardar_producto(st.session_state.user, prod, cant, costo, precio)
                st.rerun()

        df_inv = obtener_inventario(st.session_state.user)
        if not df_inv.empty:
            st.subheader("Existencias Actuales")
            st.dataframe(df_inv, use_container_width=True)

            st.subheader("🛒 Punto de Venta")
            prod_sel = st.selectbox("Seleccione Producto", df_inv["producto"])
            cant_v = st.number_input("Cantidad", min_value=1.0)
            
            if st.button("Procesar Venta"):
                row = df_inv[df_inv["producto"] == prod_sel].iloc[0]
                if row["cantidad"] >= cant_v:
                    actualizar_stock(st.session_state.user, prod_sel, cant_v)
                    ingreso = cant_v * row["precio"]
                    costo_v = cant_v * row["costo"]

                    # Asientos Automáticos
                    asientos = [
                        {"tipo": "ingreso", "cta": "ventas", "val": ingreso, "nat": "credito"},
                        {"tipo": "activo", "cta": "bancos", "val": ingreso, "nat": "debito"},
                        {"tipo": "costo", "cta": "costo de ventas", "val": costo_v, "nat": "debito"},
                        {"tipo": "activo", "cta": "inventarios", "val": costo_v, "nat": "credito"}
                    ]
                    for a in asientos:
                        guardar_movimiento(st.session_state.user, {
                            "fecha": str(date.today()), "tipo_cuenta": a["tipo"],
                            "cuenta": a["cta"], "valor": a["val"], "naturaleza": a["nat"]
                        })
                    st.success("Venta procesada y contabilizada")
                    st.rerun()
                else:
                    st.error("Sin existencias suficientes")

    # 3. REPORTES (LOS 3 ESTADOS FINANCIEROS)
    elif menu == "Reportes":
        st.title("📊 Estados Financieros")
        df = obtener_movimientos(st.session_state.user)

        if df.empty:
            st.info("No hay datos contables suficientes.")
        else:
            df["fecha"] = pd.to_datetime(df["fecha"])
            df["valor_ajustado"] = df.apply(calcular_valor, axis=1)

            t1, t2, t3 = st.tabs(["Resultados", "Situación Financiera", "Flujo de Efectivo"])

            # --- ESTADO DE RESULTADOS ---
            with t1:
                st.header("Estado de Resultados Integral")
                ing = df[df["tipo_cuenta"] == "ingreso"]["valor_ajustado"].sum()
                cos = df[df["tipo_cuenta"] == "costo"]["valor_ajustado"].sum()
                gas = df[df["tipo_cuenta"] == "gasto"]["valor_ajustado"].sum()
                utilidad_neta = ing - cos - gas

                st.metric("UTILIDAD NETA", f"$ {utilidad_neta:,.2f}")
                st.table(pd.DataFrame({
                    "Concepto": ["(+) Ingresos", "(-) Costos", "(-) Gastos", "(=) Utilidad"],
                    "Valor": [f"{ing:,.2f}", f"{cos:,.2f}", f"{gas:,.2f}", f"{utilidad_neta:,.2f}"]
                }))

            # --- SITUACIÓN FINANCIERA ---
            with t2:
                st.header("Estado de Situación Financiera")
                act = df[df["tipo_cuenta"] == "activo"]["valor_ajustado"].sum()
                pas = df[df["tipo_cuenta"] == "pasivo"]["valor_ajustado"].sum()
                pat_base = df[df["tipo_cuenta"] == "patrimonio"]["valor_ajustado"].sum()
                pat_total = pat_base + utilidad_neta # Cierre contable manual

                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("Activos")
                    st.write(f"Total Activo: **$ {act:,.2f}**")
                    st.dataframe(df[df["tipo_cuenta"] == "activo"].groupby("cuenta")["valor_ajustado"].sum())
                
                with c2:
                    st.subheader("Pasivo + Patrimonio")
                    st.write(f"Total Pasivo: **$ {pas:,.2f}**")
                    st.write(f"Total Patrimonio: **$ {pat_total:,.2f}**")
                    st.divider()
                    st.write(f"Suma P+P: **$ {pas + pat_total:,.2f}**")
                
                if abs(act - (pas + pat_total)) < 0.01:
                    st.success("Balance Cuadrado")
                else:
                    st.error(f"Diferencia en balance: {act - (pas + pat_total):,.2f}")

            # --- FLUJO DE EFECTIVO ---
            with t3:
                st.header("Estado de Flujo de Efectivo")
                st.caption("Movimientos directos de la cuenta 'bancos'")
                df_caja = df[df["cuenta"] == "bancos"]
                
                if not df_caja.empty:
                    entradas = df_caja[df_caja["naturaleza"] == "debito"]["valor"].sum()
                    salidas = df_caja[df_caja["naturaleza"] == "credito"]["valor"].sum()
                    efectivo_neto = entradas - salidas
                    
                    st.metric("Saldo Final en Bancos", f"$ {efectivo_neto:,.2f}")
                    st.write("**Desglose de movimientos de efectivo:**")
                    st.dataframe(df_caja[["fecha", "naturaleza", "valor"]].sort_values("fecha"), use_container_width=True)
                else:
                    st.warning("No se detectan movimientos en la cuenta Bancos.")