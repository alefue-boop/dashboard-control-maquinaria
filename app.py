import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración de la página
st.set_page_config(page_title="Control y Gestión de Maquinaria", layout="wide")
st.title("🚜 Dashboard de Control y Gestión de Maquinaria")

# Función para cargar y unificar los datos
@st.cache_data
def cargar_datos(report_file, empleados_file):
    
    # --- LECTURA DEL REPORTE DE MAQUINARIA ---
    try:
        report_file.seek(0)
        report_df = pd.read_csv(report_file, encoding='utf-8', on_bad_lines='skip')
    except UnicodeDecodeError:
        report_file.seek(0)
        report_df = pd.read_csv(report_file, encoding='latin-1', on_bad_lines='skip')
    except pd.errors.ParserError:
        report_file.seek(0)
        report_df = pd.read_csv(report_file, encoding='latin-1', sep=';', on_bad_lines='skip')
        
    # --- LECTURA DE LA BASE DE EMPLEADOS ---
    try:
        empleados_file.seek(0)
        employees_df = pd.read_csv(empleados_file, encoding='utf-8', on_bad_lines='skip')
    except UnicodeDecodeError:
        empleados_file.seek(0)
        employees_df = pd.read_csv(empleados_file, encoding='latin-1', on_bad_lines='skip')
    except pd.errors.ParserError:
        empleados_file.seek(0)
        employees_df = pd.read_csv(empleados_file, encoding='latin-1', sep=';', on_bad_lines='skip')
    
    # Limpieza de RUT para hacer el cruce exacto
    if 'Operador' in report_df.columns:
        report_df['Operador_clean'] = report_df['Operador'].astype(str).str.replace('.', '', regex=False).str.upper()
    else:
        report_df['Operador_clean'] = ""
        
    if 'RUT' in employees_df.columns:
        employees_df['RUT_clean'] = employees_df['RUT'].astype(str).str.replace('.', '', regex=False).str.upper()
    else:
        employees_df['RUT_clean'] = ""
    
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
    
    if 'Observaciones' in merged_df.columns:
        merged_df['Estado_Equipo'] = merged_df['Observaciones'].apply(check_status)
    else:
        merged_df['Estado_Equipo'] = 'Sin observación'
    
    # Cálculo de horas efectivas (suma de Hr Operador 1 y 2)
    hr_op1 = merged_df['Hr. Operador 1'].fillna(0) if 'Hr. Operador 1' in merged_df.columns else 0
    hr_op2 = merged_df['Hr. Operador 2'].fillna(0) if 'Hr. Operador 2' in merged_df.columns else 0
    merged_df['Horas_Efectivas'] = hr_op1 + hr_op2
    
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
    
    # Filtro por Unidad de Negocio (Centro Costo 1 de la BD empleados)
    if 'Nombre Centro Costo 1' in df.columns:
        centros_costo = df['Nombre Centro Costo 1'].dropna().unique().tolist()
        centro_seleccionado = st.sidebar.multiselect("Unidad de Negocio (Centro de Costo):", centros_costo, default=centros_costo)
        
        # Aplicar filtros
        if centro_seleccionado:
            df = df[df['Nombre Centro Costo 1'].isin(centro_seleccionado)]
        
    st.subheader("Resumen de KPIs")
    col1, col2, col3, col4 = st.columns(4)
    
    equipos_unicos = df['Equipo'].nunique() if 'Equipo' in df.columns else 0
    trabajadores_unicos = df['RUT'].nunique() if 'RUT' in df.columns else 0
    horas_totales = df['Horas_Efectivas'].sum() if 'Horas_Efectivas' in df.columns else 0
    dias_efectivos = df['Fecha reporte'].nunique() if 'Fecha reporte' in df.columns else 0
    
    col1.metric("Total Equipos Distintos", equipos_unicos)
    col2.metric("Total Trabajadores Involucrados", trabajadores_unicos)
    col3.metric("Total Horas Efectivas Trabajadas", f"{horas_totales:,.1f}")
    col4.metric("Días Efectivos Reportados", dias_efectivos)

    # Gráficos de Estado y Disponibilidad
    st.subheader("Auditoría de Disponibilidad de Equipos")
    colA, colB = st.columns(2)
    
    with colA:
        if 'Estado_Equipo' in df.columns:
            estado_counts = df['Estado_Equipo'].value_counts().reset_index()
            estado_counts.columns = ['Estado', 'Cantidad']
            fig_estado = px.pie(estado_counts, names='Estado', values='Cantidad', 
                                title='Distribución de Estados de Maquinaria', hole=0.4)
            st.plotly_chart(fig_estado, use_container_width=True)
        
    with colB:
        if 'Equipo' in df.columns and 'Horas_Efectivas' in df.columns:
            horas_por_equipo = df.groupby('Equipo')['Horas_Efectivas'].sum().reset_index().sort_values(by='Horas_Efectivas', ascending=False).head(15)
            fig_horas = px.bar(horas_por_equipo, x='Horas_Efectivas', y='Equipo', orientation='h', 
                               title='Top 15 Equipos con Más Horas Efectivas', text='Horas_Efectivas')
            fig_horas.update_traces(textposition='outside')
            st.plotly_chart(fig_horas, use_container_width=True)

    # Detalle de Trabajador vs Equipo
    st.subheader("Detalle: ¿Qué trabajador está usando qué equipo?")
    
    # Asegurarnos de que las columnas existan antes de mostrarlas para evitar errores
    columnas_vista = ['Equipo', 'Estado_Equipo', 'RUT', 'Nombre', 'Cargo', 'Horas_Efectivas', 'Observaciones']
    if 'Nombre Centro Costo 1' in df.columns:
        columnas_vista.insert(6, 'Nombre Centro Costo 1')
        
    columnas_existentes = [col for col in columnas_vista if col in df.columns]
    
    if 'Equipo' in df.columns:
        st.dataframe(df[columnas_existentes].sort_values(by=['Equipo']), use_container_width=True)
    else:
        st.dataframe(df[columnas_existentes], use_container_width=True)
    
else:
    st.info("Por favor, sube ambos archivos en el panel izquierdo para comenzar el análisis y ver el Dashboard.")
