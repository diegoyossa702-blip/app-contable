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
    if row["tipo_cuenta"] in
    