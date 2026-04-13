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
# Asegúrate de tener estos definidos en tu .streamlit/secrets.toml
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
# APP
# --------------------------
else:
    st.sidebar.success(f"👤 {st.session_state.user}")
    if st.sidebar.button("Cerrar sesión"):
        st.session_state.user = None
        st.rerun()

    menu = st.sidebar.selectbox("Menú", ["Registro", "Inventario", "Reportes"])

    cuentas = {
        "activo": ["bancos", "inventarios"],
        "pasivo": ["proveedores", "obligaciones financieras"],
        "patrimonio": ["capital"],
        "ingreso": ["ventas"],
        "costo": ["costo de ventas"],
        "gasto": ["nómina", "arriendo", "servicios"]
    }

    def calcular_valor(row):
        if row["tipo_cuenta"] in ["activo", "gasto"]:
            return row["valor"] if row["naturaleza"] == "debito" else -row["valor"]
        else:
            return row["valor"] if row["naturaleza"] == "credito" else -row["valor"]

    # --------------------------
    # REGISTRO CONTABLE (CON NUEVO CAMPO)
    # --------------------------
    if menu == "Registro":
        st.title("📥 Registro Contable")
        
        col1, col2 = st.columns(2)
        with col1:
            tipo = st.selectbox("Tipo de cuenta", list(cuentas.keys()))
            cuenta = st.selectbox("Cuenta", cuentas[tipo])
            valor = st.number_input("Valor", min_value=0.0)
        with col2:
            naturaleza = st.selectbox("Movimiento", ["debito", "credito"])
            fecha = st.date_input("Fecha")
            # NUEVO CAMPO AQUÍ
            concepto = st.text_input("Concepto o descripción", placeholder="Ej: Pago de servicios mes abril")

        if st.button("Guardar Movimiento"):
            if concepto:
                guardar_movimiento(st.session_state.user, {
                    "fecha": str(fecha),
                    "tipo_cuenta": tipo,
                    "cuenta": cuenta,
                    "valor": valor,
                    "naturaleza": naturaleza,
                    "concepto": concepto # Se envía a la DB
                })
                st.success("✅ Movimiento guardado correctamente")
            else:
                st.warning("Por favor escribe un concepto para el registro.")

    # --------------------------
    # INVENTARIO
    # --------------------------
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
            st.dataframe(df_inv, use_container_width=True)

            st.subheader("🛒 Venta")
            prod_sel = st.selectbox("Producto a vender", df_inv["producto"])
            cant_v = st.number_input("Cantidad a vender", min_value=1.0)

            if st.button("Registrar venta"):
                row = df_inv[df_inv["producto"] == prod_sel].iloc[0]
                if row["cantidad"] >= cant_v:
                    actualizar_stock(st.session_state.user, prod_sel, cant_v)
                    ingreso = cant_v * row["precio"]
                    costo_v = cant_v * row["costo"]
                    desc_venta = f"Venta de {cant_v} unidades de {prod_sel}"

                    # CONTABILIDAD AUTOMÁTICA CON CONCEPTO
                    guardar_movimiento(st.session_state.user, {
                        "fecha": str(date.today()), "tipo_cuenta": "ingreso", "cuenta": "ventas",
                        "valor": ingreso, "naturaleza": "credito", "concepto": desc_venta
                    })
                    guardar_movimiento(st.session_state.user, {
                        "fecha": str(date.today()), "tipo_cuenta": "activo", "cuenta": "bancos",
                        "valor": ingreso, "naturaleza": "debito", "concepto": desc_venta
                    })
                    guardar_movimiento(st.session_state.user, {
                        "fecha": str(date.today()), "tipo_cuenta": "costo", "cuenta": "costo de ventas",
                        "valor": costo_v, "naturaleza": "debito", "concepto": f"Costo de venta: {prod_sel}"
                    })
                    guardar_movimiento(st.session_state.user, {
                        "fecha": str(date.today()), "tipo_cuenta": "activo", "cuenta": "inventarios",
                        "valor": costo_v, "naturaleza": "credito", "concepto": f"Salida inv: {prod_sel}"
                    })
                    st.success("Venta registrada y contabilidad actualizada")
                    st.rerun()
                else:
                    st.error("Stock insuficiente")

    # --------------------------
    # REPORTES
    # --------------------------
    elif menu == "Reportes":
        st.title("📊 Estados Financieros")
        df = obtener_movimientos(st.session_state.user)

        if df.empty:
            st.warning("No hay datos")
        else:
            df["fecha"] = pd.to_datetime(df["fecha"])
            df["valor_ajustado"] = df.apply(calcular_valor, axis=1)

            with st.expander("👀 Ver historial de movimientos"):
                # Mostramos la tabla incluyendo la nueva columna concepto
                st.dataframe(df[["fecha", "tipo_cuenta", "cuenta", "concepto", "valor", "naturaleza"]], use_container_width=True)

            st.subheader("📈 Estado de Resultados")
            ingresos = df[df["tipo_cuenta"] == "ingreso"]["valor_ajustado"].sum()
            costos = df[df["tipo_cuenta"] == "costo"]["valor_ajustado"].sum()
            gastos = df[df["tipo_cuenta"] == "gasto"]["valor_ajustado"].sum()
            utilidad = ingresos - costos - gastos

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Ingresos", f"${ingresos:,.2f}")
            c2.metric("Costos", f"${costos:,.2f}")
            c3.metric("Gastos", f"${gastos:,.2f}")
            c4.metric("Utilidad", f"${utilidad:,.2f}", delta=float(utilidad))
            
            

