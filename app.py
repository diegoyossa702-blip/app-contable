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

def guardar_producto(user, producto, cantidad, costo, precio):
    supabase.table("inventario").insert({
        "username": user, "producto": producto, "cantidad": cantidad, "costo": costo, "precio": precio
    }).execute()

def actualizar_stock(user, producto, cantidad):
    inv = obtener_inventario(user)
    row = inv[inv["producto"] == producto].iloc[0]
    nueva_cantidad = row["cantidad"] - cantidad
    supabase.table("inventario").update({"cantidad": nueva_cantidad}).eq("username", user).eq("producto", producto).execute()

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
# APP
# --------------------------
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.title("🔐 Login / Registro")
    opcion = st.selectbox("Opción", ["Login", "Registro"])
    user = st.text_input("Usuario")
    pwd = st.text_input("Contraseña", type="password")

    if opcion == "Registro" and st.button("Crear usuario"):
        crear_usuario(user, pwd)
        st.success("Usuario creado")
    if opcion == "Login" and st.button("Ingresar"):
        if login(user, pwd):
            st.session_state.user = user
            st.rerun()
        else:
            st.error("Credenciales incorrectas")

else:
    st.sidebar.success(f"👤 {st.session_state.user}")
    if st.sidebar.button("Cerrar sesión"):
        st.session_state.user = None
        st.rerun()

    menu = st.sidebar.selectbox("Menú", ["Registro", "Inventario", "Reportes"])

    if menu == "Registro":
        st.title("📥 Registro Contable")
        tipo = st.selectbox("Tipo de cuenta", list(cuentas.keys()))
        cuenta = st.selectbox("Cuenta", cuentas[tipo])
        valor = st.number_input("Valor", min_value=0.0)
        naturaleza = st.selectbox("Movimiento", ["debito", "credito"])
        fecha = st.date_input("Fecha")
        if st.button("Guardar"):
            guardar_movimiento(st.session_state.user, {"fecha": str(fecha), "tipo_cuenta": tipo, "cuenta": cuenta, "valor": valor, "naturaleza": naturaleza})
            st.success("Movimiento guardado")

    elif menu == "Inventario":
        st.title("📦 Inventario")
        with st.expander("➕ Agregar producto"):
            prod = st.text_input("Nombre")
            cant = st.number_input("Cantidad", min_value=0.0)
            costo = st.number_input("Costo", min_value=0.0)
            precio = st.number_input("Precio", min_value=0.0)
            if st.button("Guardar producto"):
                guardar_producto(st.session_state.user, prod, cant, costo, precio)
                st.rerun()

        df_inv = obtener_inventario(st.session_state.user)
        if not df_inv.empty:
            st.dataframe(df_inv)
            st.subheader("🛒 Venta")
            prod_sel = st.selectbox("Producto", df_inv["producto"])
            cant_v = st.number_input("Cantidad a vender", min_value=1.0)
            if st.button("Registrar venta"):
                row = df_inv[df_inv["producto"] == prod_sel].iloc[0]
                if row["cantidad"] >= cant_v:
                    actualizar_stock(st.session_state.user, prod_sel, cant_v)
                    ing = cant_v * row["precio"]
                    cos = cant_v * row["costo"]
                    # Asientos automáticos
                    for t, c, v, n in [("ingreso","ventas",ing,"credito"), ("activo","bancos",ing,"debito"), ("costo","costo de ventas",cos,"debito"), ("activo","inventarios",cos,"credito")]:
                        guardar_movimiento(st.session_state.user, {"fecha": str(date.today()), "tipo_cuenta": t, "cuenta": c, "valor": v, "naturaleza": n})
                    st.success("Venta registrada")
                    st.rerun()

    elif menu == "Reportes":
        st.title("📊 Estados Financieros")
        df = obtener_movimientos(st.session_state.user)
        if df.empty:
            st.warning("No hay datos")
        else:
            df["fecha"] = pd.to_datetime(df["fecha"])
            df["valor_ajustado"] = df.apply(calcular_valor, axis=1)
            t1, t2, t3 = st.tabs(["Resultados", "Situación Financiera", "Flujo de Efectivo"])
            
            with t1:
                ing = df[df["tipo_cuenta"] == "ingreso"]["valor_ajustado"].sum()
                cos =