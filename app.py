import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="App Contable", layout="wide")

# --------------------------
# SIDEBAR
# --------------------------
st.sidebar.title("📌 Navegación")
menu = st.sidebar.selectbox(
    "Selecciona una opción",
    ["Inicio", "Registro", "Inventario", "Reportes"]
)

# --------------------------
# BASES DE DATOS
# --------------------------
if "data" not in st.session_state:
    st.session_state.data = []

if "productos" not in st.session_state:
    st.session_state.productos = []

# --------------------------
# PLAN DE CUENTAS (MEJORADO)
# --------------------------
cuentas = {
    "ingreso": [
        "ventas",
        "ingresos por servicios",
        "ingresos financieros",
        "otros ingresos"
    ],
    "costo": [
        "costo de ventas"
    ],
    "gasto": [
        "gastos administrativos",
        "gastos de ventas",
        "arriendo",
        "servicios públicos",
        "nómina",
        "depreciación",
        "gastos financieros",
        "impuestos",
        "otros gastos"
    ],
    "activo": [
        "efectivo",
        "bancos",
        "cuentas por cobrar",
        "inventarios",
        "propiedad planta y equipo",
        "equipos de cómputo",
        "vehículos",
        "otros activos"
    ],
    "pasivo": [
        "cuentas por pagar",
        "proveedores",
        "pasivos financieros",
        "impuestos por pagar",
        "obligaciones laborales",
        "otros pasivos"
    ],
    "patrimonio": [
        "capital",
        "utilidades retenidas",
        "resultado del ejercicio"
    ]
}

# --------------------------
# INICIO
# --------------------------
if menu == "Inicio":
    st.title("💼 App Contable")
    st.write("Sistema contable con estados financieros detallados")

# --------------------------
# REGISTRO CONTABLE
# --------------------------
elif menu == "Registro":
    st.title("📥 Registro Contable")

    tipo_cuenta = st.selectbox("Tipo de Cuenta", list(cuentas.keys()))
    cuenta = st.selectbox("Cuenta", cuentas[tipo_cuenta])
    valor = st.number_input("Valor", min_value=0)
    fecha = st.date_input("Fecha")

    if st.button("Guardar"):
        st.session_state.data.append({
            "fecha": str(fecha),
            "tipo_cuenta": tipo_cuenta,
            "cuenta": cuenta,
            "valor": valor
        })
        st.success("Movimiento guardado")

    if st.session_state.data:
        st.dataframe(pd.DataFrame(st.session_state.data))

# --------------------------
# INVENTARIO (SIMPLE)
# --------------------------
elif menu == "Inventario":
    st.title("📦 Inventario")

    nombre = st.text_input("Producto")
    cantidad = st.number_input("Cantidad", min_value=0)
    costo = st.number_input("Costo unitario", min_value=0.0)

    if st.button("Agregar"):
        st.session_state.productos.append({
            "producto": nombre,
            "cantidad": cantidad,
            "costo": costo
        })

    if st.session_state.productos:
        df_inv = pd.DataFrame(st.session_state.productos)
        df_inv["total"] = df_inv["cantidad"] * df_inv["costo"]
        st.dataframe(df_inv)

# --------------------------
# REPORTES
# --------------------------
elif menu == "Reportes":
    st.title("📊 Estados Financieros")

    if not st.session_state.data:
        st.warning("No hay datos")
    else:
        df = pd.DataFrame(st.session_state.data)
        df["fecha"] = pd.to_datetime(df["fecha"])

        # --------------------------
        # FILTROS
        # --------------------------
        col1, col2 = st.columns(2)

        with col1:
            fecha_inicio = st.date_input("Inicio", value=date(2025,1,1))
            fecha_fin = st.date_input("Fin", value=date.today())

        with col2:
            fecha_corte = st.date_input("Fecha de corte", value=date.today())

        # --------------------------
        # ESTADO DE RESULTADOS
        # --------------------------
        df_res = df[
            (df["fecha"] >= pd.to_datetime(fecha_inicio)) &
            (df["fecha"] <= pd.to_datetime(fecha_fin))
        ]

        st.subheader("📊 Estado de Resultados")

        ingresos = df_res[df_res["tipo_cuenta"] == "ingreso"].groupby("cuenta")["valor"].sum()
        costos = df_res[df_res["tipo_cuenta"] == "costo"].groupby("cuenta")["valor"].sum()
        gastos = df_res[df_res["tipo_cuenta"] == "gasto"].groupby("cuenta")["valor"].sum()

        st.write("**Ingresos**")
        st.write(ingresos)

        st.write("**Costos**")
        st.write(costos)

        st.write("**Gastos**")
        st.write(gastos)

        total_ingresos = ingresos.sum()
        total_costos = costos.sum()
        total_gastos = gastos.sum()

        utilidad = total_ingresos - total_costos - total_gastos

        st.write(f"**Utilidad Neta: {utilidad}**")

        # --------------------------
        # BALANCE GENERAL
        # --------------------------
        df_bal = df[df["fecha"] <= pd.to_datetime(fecha_corte)]

        st.subheader("🧾 Estado de Situación Financiera")

        activos = df_bal[df_bal["tipo_cuenta"] == "activo"].groupby("cuenta")["valor"].sum()
        pasivos = df_bal[df_bal["tipo_cuenta"] == "pasivo"].groupby("cuenta")["valor"].sum()
        patrimonio = df_bal[df_bal["tipo_cuenta"] == "patrimonio"].groupby("cuenta")["valor"].sum()

        st.write("**Activos**")
        st.write(activos)

        st.write("**Pasivos**")
        st.write(pasivos)

        st.write("**Patrimonio**")
        st.write(patrimonio)

        st.write(f"Total Activos: {activos.sum()}")
        st.write(f"Total Pasivos: {pasivos.sum()}")
        st.write(f"Total Patrimonio: {patrimonio.sum()}")

        # --------------------------
        # FLUJO DE EFECTIVO
        # --------------------------
        st.subheader("💸 Flujo de Efectivo")

        entradas = df_res[df_res["tipo_cuenta"] == "ingreso"]["valor"].sum()
        salidas = df_res[df_res["tipo_cuenta"].isin(["gasto", "costo"])]["valor"].sum()

        flujo = entradas - salidas

        st.write(f"Entradas: {entradas}")
        st.write(f"Salidas: {salidas}")
        st.write(f"Flujo Neto: {flujo}")
        