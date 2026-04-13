import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="App Contable PRO", layout="wide")

# --------------------------
# BASES DE DATOS (Session State)
# --------------------------
if "data" not in st.session_state:
    st.session_state.data = []

if "productos" not in st.session_state:
    st.session_state.productos = []

# --------------------------
# PLAN DE CUENTAS EXTENDIDO
# --------------------------
cuentas = {
    "ingreso": ["ventas", "ingresos por servicios", "ingresos financieros", "otros ingresos"],
    "costo": ["costo de ventas"],
    "gasto": ["gastos administrativos", "gastos de ventas", "arriendo", "servicios públicos", "nómina", "depreciación", "gastos financieros", "impuestos", "otros gastos"],
    "activo": ["efectivo", "bancos", "cuentas por cobrar", "inventarios", "propiedad planta y equipo", "equipos de cómputo", "vehículos", "otros activos"],
    "pasivo": ["cuentas por pagar", "proveedores", "pasivos financieros", "impuestos por pagar", "obligaciones laborales", "otros pasivos"],
    "patrimonio": ["capital", "utilidades retenidas", "resultado del ejercicio"]
}

# --------------------------
# SIDEBAR
# --------------------------
st.sidebar.title("📌 Panel de Control")
menu = st.sidebar.selectbox("Selecciona una opción", ["Inicio", "Registro", "Inventario", "Reportes"])

# --------------------------
# LÓGICA DE INICIO
# --------------------------
if menu == "Inicio":
    st.title("💼 Sistema Contable Profesional")
    st.write("Bienvenido. Utilice el menú lateral para registrar movimientos o consultar los Estados Financieros.")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Registros totales", len(st.session_state.data))
    col2.metric("Items en Inventario", len(st.session_state.productos))

# --------------------------
# REGISTRO CONTABLE
# --------------------------
elif menu == "Registro":
    st.title("📥 Registro de Operaciones")
    
    with st.form("registro_form"):
        col_a, col_b = st.columns(2)
        tipo_cuenta = col_a.selectbox("Categoría", list(cuentas.keys()))
        cuenta = col_a.selectbox("Subcuenta", cuentas[tipo_cuenta])
        valor = col_b.number_input("Monto ($)", min_value=0.0, step=100.0)
        fecha = col_b.date_input("Fecha de transacción", value=date.today())
        
        submit = st.form_submit_button("Confirmar Registro")
        
        if submit:
            st.session_state.data.append({
                "fecha": pd.to_datetime(fecha),
                "tipo_cuenta": tipo_cuenta,
                "cuenta": cuenta,
                "valor": valor
            })
            st.success(f"Registrado: {cuenta} por ${valor:,.2f}")

    if st.session_state.data:
        st.subheader("Historial Reciente")
        st.dataframe(pd.DataFrame(st.session_state.data).sort_values("fecha", ascending=False), use_container_width=True)

# --------------------------
# INVENTARIO
# --------------------------
elif menu == "Inventario":
    st.title("📦 Control de Existencias")
    
    with st.expander("Añadir nuevo producto"):
        c1, c2, c3 = st.columns(3)
        nombre = c1.text_input("Nombre del ítem")
        cantidad = c2.number_input("Cantidad", min_value=0)
        costo = c3.number_input("Costo Unitario", min_value=0.0)
        
        if st.button("Registrar en Inventario"):
            st.session_state.productos.append({"producto": nombre, "cantidad": cantidad, "costo": costo})
            st.rerun()

    if st.session_state.productos:
        df_inv = pd.DataFrame(st.session_state.productos)
        df_inv["Valor Total"] = df_inv["cantidad"] * df_inv["costo"]
        st.table(df_inv)

# --------------------------
# REPORTES (ESTADOS FINANCIEROS)
# --------------------------
elif menu == "Reportes":
    st.title("📊 Estados Financieros Detallados")

    if not st.session_state.data:
        st.warning("No hay registros contables para generar reportes.")
    else:
        df = pd.DataFrame(st.session_state.data)
        
        # Filtros de fecha
        col_f1, col_f2 = st.columns(2)
        f_inicio = pd.to_datetime(col_f1.date_input("Desde", value=date(2025,1,1)))
        f_fin = pd.to_datetime(col_f2.date_input("Hasta", value=date.today()))

        # --- 1. ESTADO DE RESULTADOS ---
        st.markdown("---")
        st.header("1. Estado de Resultados Integral")
        df_er = df[(df["fecha"] >= f_inicio) & (df["fecha"] <= f_fin)]
        
        def obtener_tabla(tipo):
            res = df_er[df_er["tipo_cuenta"] == tipo].groupby("cuenta")["valor"].sum().reset_index()
            return res.rename(columns={"cuenta": "Cuenta", "valor": "Monto"})

        ingresos_df = obtener_tabla("ingreso")
        costos_df = obtener_tabla("costo")
        gastos_df = obtener_tabla("gasto")

        col_er1, col_er2 = st.columns([2, 1])
        with col_er1:
            st.write("**INGRESOS**")
            st.table(ingresos_df)
            st.write("**COSTOS Y GASTOS**")
            st.table(pd.concat([costos_df, gastos_df]))

        total_ing = ingresos_df["Monto"].sum()
        total_cg = costos_df["Monto"].sum() + gastos_df["Monto"].sum()
        utilidad_neta = total_ing - total_cg

        with col_er2:
            st.metric("Utilidad / Pérdida", f"$ {utilidad_neta:,.2f}")

        # --- 2. BALANCE GENERAL ---
        st.markdown("---")
        st.header("2. Estado de Situación Financiera")
        
        df_bal = df[df["fecha"] <= f_fin]
        
        activos_df = df_bal[df_bal["tipo_cuenta"] == "activo"].groupby("cuenta")["valor"].sum().reset_index()
        pasivos_df = df_bal[df_bal["tipo_cuenta"] == "pasivo"].groupby("cuenta")["valor"].sum().reset_index()
        patrimonio_df = df_bal[df_bal["tipo_cuenta"] == "patrimonio"].groupby("cuenta")["valor"].sum().reset_index()

        c_bal1, c_bal2 = st.columns(2)
        
        with c_bal1:
            st.subheader("Activos")
            st.table(activos_df.rename(columns={"cuenta":"Cuenta", "valor":"Monto"}))
            st.info(f"**Total Activos: $ {activos_df['valor'].sum():,.2f}**")

        with c_bal2:
            st.subheader("Pasivos")
            st.table(pasivos_df.rename(columns={"cuenta":"Cuenta", "valor":"Monto"}))
            st.write(f"Total Pasivos: $ {pasivos_df['valor'].sum():,.2f}")
            
            st.subheader("Patrimonio")
            st.table(patrimonio_df.rename(columns={"cuenta":"Cuenta", "valor":"Monto"}))
            st.write(f"Resultado del Ejercicio: $ {utilidad_neta:,.2f}")
            
            total_pp = pasivos_df['valor'].sum() + patrimonio_df['valor'].sum() + utilidad_neta
            st.success(f"**Total Pasivo + Pat: $ {total_pp:,.2f}**")

        # --- 3. FLUJO DE EFECTIVO ---
        st.markdown("---")
        st.header("3. Flujo de Efectivo")
        
        entradas = total_ing
        salidas = total_cg
        
        f1, f2, f3 = st.columns(3)
        f1.metric("Entradas de Efectivo", f"$ {entradas:,.2f}")
        f2.metric("Salidas de Efectivo", f"$ {salidas:,.2f}")
        f3.metric("Flujo Neto", f"$ {entradas - salidas:,.2f}")