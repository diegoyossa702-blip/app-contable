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
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --------------------------
# FUNCIONES
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
# SESSION
# --------------------------
if "user" not in st.session_state:
    st.session_state.user = None

# --------------------------
# LOGIN / REGISTRO
# --------------------------
if not st.session_state.user:
    st.title("🔐 Login / Registro")
    opcion = st.selectbox("Opción", ["Login", "Registro"])
    user = st.text_input("Usuario")
    pwd = st.text_input("Contraseña", type="password")

    if opcion == "Registro":
        if st.button("Crear usuario"):
            crear_usuario(user, pwd)
            st.success("Usuario creado")

    if opcion == "Login":
        if st.button("Ingresar"):
            if login(user, pwd):
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Credenciales incorrectas")

# --------------------------
# APP PRINCIPAL
# --------------------------
else:
    st.sidebar.success(f"👤 {st.session_state.user}")
    if st.sidebar.button("Cerrar sesión"):
        st.session_state.user = None
        st.rerun()

    menu = st.sidebar.selectbox("Menú", ["Registro", "Inventario", "Reportes"])

    # --------------------------
    # PLAN DE CUENTAS
    # --------------------------
    cuentas = {
        "activo": ["bancos", "inventarios", "cuentas por cobrar", "propiedad planta y equipo"],
        "pasivo": ["proveedores", "obligaciones financieras", "pasivos financieros"],
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

    # --- SECCIÓN REGISTRO ---
    if menu == "Registro":
        st.title("📥 Registro Contable")
        tipo = st.selectbox("Tipo de cuenta", list(cuentas.keys()))
        cuenta = st.selectbox("Cuenta", cuentas[tipo])
        valor = st.number_input("Valor", min_value=0.0)
        naturaleza = st.selectbox("Movimiento", ["debito", "credito"])
        fecha = st.date_input("Fecha")

        if st.button("Guardar"):
            guardar_movimiento(st.session_state.user, {
                "fecha": str(fecha),
                "tipo_cuenta": tipo,
                "cuenta": cuenta,
                "valor": valor,
                "naturaleza": naturaleza
            })
            st.success("Movimiento guardado")

    # --- SECCIÓN INVENTARIO ---
    elif menu == "Inventario":
        st.title("📦 Inventario")
        with st.expander("➕ Agregar producto"):
            prod = st.text_input("Nombre del producto")
            cant = st.number_input("Cantidad", min_value=0.0)
            costo = st.number_input("Costo unitario", min_value=0.0)
            precio = st.number_input("Precio de venta", min_value=0.0)
            if st.button("Guardar producto"):
                guardar_producto(st.session_state.user, prod, cant, costo, precio)
                st.success("Producto guardado")

        df_inv = obtener_inventario(st.session_state.user)
        if not df_inv.empty:
            st.subheader("📋 Inventario actual")
            st.dataframe(df_inv)
            st.subheader("🛒 Venta")
            prod_sel = st.selectbox("Producto", df_inv["producto"])
            cant_v = st.number_input("Cantidad a vender", min_value=1.0)

            if st.button("Registrar venta"):
                row = df_inv[df_inv["producto"] == prod_sel].iloc[0]
                if row["cantidad"] >= cant_v:
                    actualizar_stock(st.session_state.user, prod_sel, cant_v)
                    ingreso, costo_v = (cant_v * row["precio"]), (cant_v * row["costo"])
                    
                    asientos = [
                        ("ingreso", "ventas", ingreso, "credito"),
                        ("activo", "bancos", ingreso, "debito"),
                        ("costo", "costo de ventas", costo_v, "debito"),
                        ("activo", "inventarios", costo_v, "credito")
                    ]
                    for t, c, v, n in asientos:
                        guardar_movimiento(st.session_state.user, {
                            "fecha": str(date.today()), "tipo_cuenta": t, "cuenta": c, "valor": v, "naturaleza": n
                        })
                    st.success("Venta registrada correctamente")
                    st.rerun()
                else:
                    st.error("Stock insuficiente")

    # --- SECCIÓN REPORTES (MEJORADA) ---
    elif menu == "Reportes":
        st.title("📊 Estados Financieros Detallados")
        df = obtener_movimientos(st.session_state.user)

        if df.empty:
            st.warning("No hay datos registrados para este usuario.")
        else:
            df["fecha"] = pd.to_datetime(df["fecha"])
            df["valor_ajustado"] = df.apply(calcular_valor, axis=1)

            t1, t2, t3 = st.tabs(["📉 Estado de Resultados", "⚖️ Balance General", "💸 Flujo de Caja"])

            with t1:
                st.subheader("Resultados del Periodo")
                df_res = df[df["tipo_cuenta"].isin(["ingreso", "costo", "gasto"])]
                res_tabla = df_res.groupby(["tipo_cuenta", "cuenta"])["valor_ajustado"].sum().reset_index()
                
                ing_t = res_tabla[res_tabla["tipo_cuenta"]=="ingreso"]["valor_ajustado"].sum()
                cos_t = res_tabla[res_tabla["tipo_cuenta"]=="costo"]["valor_ajustado"].sum()
                gas_t = res_tabla[res_tabla["tipo_cuenta"]=="gasto"]["valor_ajustado"].sum()
                utilidad_neta = ing_t - cos_t - gas_t
                
                st.table(res_tabla.rename(columns={"tipo_cuenta":"Tipo", "cuenta":"Cuenta", "valor_ajustado":"Saldo"}))
                st.metric("Utilidad del Ejercicio", f"$ {utilidad_neta:,.2f}")

            with t2:
                st.subheader("Situación Financiera")
                df_bal = df[df["tipo_cuenta"].isin(["activo", "pasivo", "patrimonio"])]
                bal_tabla = df_bal.groupby(["tipo_cuenta", "cuenta"])["valor_ajustado"].sum().reset_index()
                
                col_a, col_p = st.columns(2)
                with col_a:
                    st.write("**ACTIVOS**")
                    st.table(bal_tabla[bal_tabla["tipo_cuenta"]=="activo"][["cuenta", "valor_ajustado"]])
                    total_act = bal_tabla[bal_tabla["tipo_cuenta"]=="activo"]["valor_ajustado"].sum()
                    st.write(f"**Total Activo: $ {total_act:,.2f}**")

                with col_p:
                    st.write("**PASIVO + PATRIMONIO**")
                    pas_tab = bal_tabla[bal_tabla["tipo_cuenta"]=="pasivo"]
                    pat_tab = bal_tabla[bal_tabla["tipo_cuenta"]=="patrimonio"]
                    if not pas_tab.empty: st.table(pas_tab[["cuenta", "valor_ajustado"]])
                    if not pat_tab.empty: st.table(pat_tab[["cuenta", "valor_ajustado"]])
                    st.write(f"Utilidad Neta: $ {utilidad_neta:,.2f}")
                    
                    total_p_p = bal_tabla[bal_tabla["tipo_cuenta"].isin(["pasivo", "patrimonio"])]["valor_ajustado"].sum() + utilidad_neta
                    st.write(f"**Total Pasivo + Pat: $ {total_p_p:,.2f}**")
                
                st.divider()
                if abs(total_act - total_p_p) < 0.01: st.success("Balance Cuadrado ✅")
                else: st.error("Balance Descuadrado ❌")

            with t3:
                st.subheader("Movimientos de Efectivo")
                df_caja = df[df["cuenta"] == "bancos"].copy()
                if not df_caja.empty:
                    st.dataframe(df_caja[["fecha", "cuenta", "valor", "naturaleza"]], use_container_width=True)
                    st.metric("Saldo Final en Bancos", f"$ {df_caja['valor_ajustado'].sum():,.2f}")
                else:
                    st.info("No se registran movimientos en la cuenta 'bancos'.")