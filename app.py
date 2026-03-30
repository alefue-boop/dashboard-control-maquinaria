import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración de la página
st.set_page_config(page_title="Control y Gestión de Maquinaria", layout="wide")
st.title("🚜 Dashboard de Control y Gestión de Maquinaria")

# Función para cargar y unificar los datos
@st.cache_data
def cargar_datos(report_file, empleados_file):
    report_df = pd.read_csv(report_file)
    employees_df = pd.read_csv(empleados_file)
    
    # Limpieza de RUT para hacer el cruce exacto
    report_df['Operador_clean'] = report_df['Operador'].astype(str).str.replace('.', '', regex=False).str.upper()
    employees_df['RUT_clean'] = employees_df['RUT'].astype(str).str.replace('.', '', regex=False).str.upper()
    
    # Cruce de bases de datos
    merged_df = pd.merge(report_df, employees_df, left_on='Operador_clean', right_on='RUT_clean', how='left')
    
    # Clasificación de la disponibilidad del equipo basado en las observaciones
    def check_status(obs):
        if pd.isna(obs): return 'Sin observación'
        obs_lower = str(obs).lower()
        if 'panne' in obs_lower or 'panna' in obs_lower: return 'Panne/Falla'
        if 'revisión técnica' in obs_lower or 'revision tecnica' in obs_lower: return 'Revisión Técnica'
        if 'estacionada' in obs_lower or 'estacionado' in obs_lower: return 'Estacionada'
        if 'lluvia' in obs_lower: return 'Disponible por Lluvia'
        if 'disponible' in obs_lower: return 'Disponible'
        return 'Operativo / Trabajando'
    
    merged_df['Estado_Equipo'] = merged_df['Observaciones'].apply(check_status)
    
    # Cálculo de horas efectivas (suma de Hr Operador 1 y 2)
    merged_df['Horas_Efectivas'] = merged_df['Hr. Operador 1'].fillna(0) + merged_df['Hr. Operador 2'].fillna(0)
    
    # Limpieza de fechas
    if 'Fecha reporte' in merged_df.columns:
        merged_df['Fecha reporte'] = pd.to_datetime(merged_df['Fecha reporte'], errors='coerce')
        
    return merged_df

st.sidebar.header("Carga de Archivos")
report_file = st.sidebar.file_uploader("Sube el archivo de Reporte de Maquinaria (CSV o Excel)", type=['csv', 'xlsx'])
empleados_file = st.sidebar.file_uploader("Sube la base de datos de Empleados (CSV o Excel)", type=['csv', 'xlsx'])

if report_file and empleados_file:
    with st.spinner("Procesando y unificando información..."):
        df = cargar_datos(report_file, empleados_file)
        
    st.sidebar.header("Filtros")
    # Filtro por Unidad de Negocio (Centro Costo 1 de la BD empleados o Consorcio)
    centros_costo = df['Nombre Centro Costo 1'].dropna().unique().tolist()
    centro_seleccionado = st.sidebar.multiselect("Unidad de Negocio (Centro de Costo):", centros_costo, default=centros_costo)
    
    # Aplicar filtros
    if centro_seleccionado:
        df = df[df['Nombre Centro Costo 1'].isin(centro_seleccionado)]
        
    st.subheader("Resumen de KPIs")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Equipos Distintos", df['Equipo'].nunique())
    col2.metric("Total Trabajadores Involucrados", df['RUT'].nunique())
    col3.metric("Total Horas Efectivas Trabajadas", f"{df['Horas_Efectivas'].sum():,.1f}")
    col4.metric("Días Efectivos Reportados", df['Fecha reporte'].nunique())

    # Gráficos de Estado y Disponibilidad
    st.subheader("Auditoría de Disponibilidad de Equipos")
    colA, colB = st.columns(2)
    
    with colA:
        estado_counts = df['Estado_Equipo'].value_counts().reset_index()
        estado_counts.columns = ['Estado', 'Cantidad']
        fig_estado = px.pie(estado_counts, names='Estado', values='Cantidad', 
                            title='Distribución de Estados de Maquinaria', hole=0.4)
        st.plotly_chart(fig_estado, use_container_width=True)
        
    with colB:
        horas_por_equipo = df.groupby('Equipo')['Horas_Efectivas'].sum().reset_index().sort_values(by='Horas_Efectivas', ascending=False).head(15)
        fig_horas = px.bar(horas_por_equipo, x='Horas_Efectivas', y='Equipo', orientation='h', 
                           title='Top 15 Equipos con Más Horas Efectivas', text='Horas_Efectivas')
        fig_horas.update_traces(textposition='outside')
        st.plotly_chart(fig_horas, use_container_width=True)

    # Detalle de Trabajador vs Equipo
    st.subheader("Detalle: ¿Qué trabajador está usando qué equipo?")
    columnas_vista = ['Equipo', 'Estado_Equipo', 'RUT', 'Nombre', 'Cargo', 'Horas_Efectivas', 'Nombre Centro Costo 1', 'Observaciones']
    st.dataframe(df[columnas_vista].sort_values(by=['Equipo']), use_container_width=True)
    
else:
    st.info("Por favor, sube ambos archivos en el panel izquierdo para comenzar el análisis y ver el Dashboard.")
