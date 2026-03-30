import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS CORPORATIVOS ---
st.set_page_config(page_title="Control y Gestión de Maquinaria", layout="wide")

st.markdown("""
    <style>
    /* Tipografía corporativa Times New Roman */
    html, body, [class*="css"], [class*="st-"] {
        font-family: 'Times New Roman', Times, serif !important;
    }
    
    /* Títulos en color Burdeo */
    h1, h2, h3, h4, h5, h6 {
        color: #800020 !important; 
    }
    
    /* Valores de KPIs en Verde Corporativo */
    [data-testid="stMetricValue"] {
        color: #2E7D32 !important; 
    }
    
    /* Etiquetas de KPIs en Gris oscuro */
    [data-testid="stMetricLabel"] {
        color: #555555 !important;
        font-weight: bold;
    }
    
    /* Fondo barra lateral Gris claro */
    [data-testid="stSidebar"] {
        background-color: #F4F6F6 !important;
    }
    </style>
    """, unsafe_allow_html=True)

colores_corporativos = ['#800020', '#2E7D32', '#7F8C8D', '#BDC3C7', '#A9DFBF', '#D98880']

st.title("🚜 Dashboard de Control y Gestión de Maquinaria")

# --- 2. MOTOR DE PROCESAMIENTO DE DATOS ---
@st.cache_data
def cargar_datos(report_file, empleados_file):
    
    def procesar_archivo(uploaded_file):
        nombre_archivo = uploaded_file.name.lower()
        if nombre_archivo.endswith('.csv'):
            try:
                uploaded_file.seek(0)
                return pd.read_csv(uploaded_file, encoding='utf-8', on_bad_lines='skip')
            except UnicodeDecodeError:
                uploaded_file.seek(0)
                return pd.read_csv(uploaded_file, encoding='latin-1', on_bad_lines='skip')
            except pd.errors.ParserError:
                uploaded_file.seek(0)
                return pd.read_csv(uploaded_file, encoding='latin-1', sep=';', on_bad_lines='skip')
        elif nombre_archivo.endswith('.xlsx') or nombre_archivo.endswith('.xls'):
            uploaded_file.seek(0)
            return pd.read_excel(uploaded_file)
        else:
            return pd.DataFrame()

    report_df = procesar_archivo(report_file)
    employees_df = procesar_archivo(empleados_file)
    
    # Limpieza de RUTs
    if 'Operador' in report_df.columns:
        report_df['Operador_clean'] = report_df['Operador'].astype(str).str.replace('.', '', regex=False).str.strip().str.upper()
    else:
        report_df['Operador_clean'] = ""
        
    if 'RUT' in employees_df.columns:
        employees_df['RUT_clean'] = employees_df['RUT'].astype(str).str.replace('.', '', regex=False).str.strip().str.upper()
    else:
        employees_df['RUT_clean'] = ""
    
    merged_df = pd.merge(report_df, employees_df, left_on='Operador_clean', right_on='RUT_clean', how='left')
    
    # --- FORMATEO INTELIGENTE DE NOMBRES ---
    def formatear_nombre(nombre_crudo):
        if pd.isna(nombre_crudo) or str(nombre_crudo).strip() == "":
            return "Sin Registro"
        
        # Convierte a Formato Título y separa por espacios
        partes = str(nombre_crudo).strip().title().split()
        
        # Si tiene 3 o más palabras (Ej: Perez Rojas Juan Carlos) -> Invertimos a (Juan Carlos Perez Rojas)
        if len(partes) >= 3:
            nombres = " ".join(partes[2:])
            apellidos = " ".join(partes[:2])
            return f"{nombres} {apellidos}"
        return str(nombre_crudo).title()

    if 'Nombre' in merged_df.columns:
        merged_df['Nombre'] = merged_df['Nombre'].apply(formatear_nombre)
    
    # Estandarización de Unidad de Negocio
    if 'Nombre Centro Costo 1' in merged_df.columns:
        merged_df['Unidad_Negocio'] = merged_df['Nombre Centro Costo 1'].fillna('Sin Unidad Asignada')
    else:
        merged_df['Unidad_Negocio'] = 'Sin Unidad Asignada'

    # Motor de estado de maquinaria
    def check_status(obs):
        if pd.isna(obs): return 'Sin observación'
        obs_lower = str(obs).lower()
        if 'panne' in obs_lower or 'panna' in obs_lower or 'falla' in obs_lower: return 'Panne / Falla'
        if 'revisión técnica' in obs_lower or 'revision tecnica' in obs_lower: return 'Revisión Técnica'
        if 'estacionada' in obs_lower or 'estacionado' in obs_lower: return 'Estacionada'
        if 'lluvia' in obs_lower: return 'Disponible por Lluvia'
        if 'disponible' in obs_lower: return 'Disponible'
        return 'Operativo / Trabajando'
    
    if 'Observaciones' in merged_df.columns:
        merged_df['Estado_Equipo'] = merged_df['Observaciones'].apply(check_status)
    else:
        merged_df['Estado_Equipo'] = 'Sin observación'
    
    # Horas Efectivas
    hr_op1 = pd.to_numeric(merged_df['Hr. Operador 1'], errors='coerce').fillna(0) if 'Hr. Operador 1' in merged_df.columns else 0
    hr_op2 = pd.to_numeric(merged_df['Hr. Operador 2'], errors='coerce').fillna(0) if 'Hr. Operador 2' in merged_df.columns else 0
    merged_df['Horas_Efectivas'] = hr_op1 + hr_op2
    
    # Fechas
    if 'Fecha reporte' in merged_df.columns:
        merged_df['Fecha reporte'] = pd.to_datetime(merged_df['Fecha reporte'], errors='coerce').dt.date
        
    return merged_df

# --- 3. INTERFAZ Y FILTROS ---
st.sidebar.header("Carga de Archivos")
report_file = st.sidebar.file_uploader("Sube el archivo de Reporte de Maquinaria", type=['csv', 'xlsx'])
empleados_file = st.sidebar.file_uploader("Sube la base de Empleados", type=['csv', 'xlsx'])

if report_file and empleados_file:
    with st.spinner("Procesando lógicas corporativas..."):
        df = cargar_datos(report_file, empleados_file)
        
    st.sidebar.header("Filtros")
    unidades_disponibles = sorted(df['Unidad_Negocio'].unique().tolist())
    unidad_seleccionada = st.sidebar.multiselect("Unidad de Negocio (Centro de Costo):", unidades_disponibles, default=unidades_disponibles)
    
    if unidad_seleccionada:
        df = df[df['Unidad_Negocio'].isin(unidad_seleccionada)]
        
    # --- 4. KPIs GENERALES ---
    st.subheader("Resumen de KPIs")
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric("Total Equipos Distintos", df['Equipo'].nunique() if 'Equipo' in df.columns else 0)
    col2.metric("Total Trabajadores Involucrados", df['RUT_clean'].nunique() if 'RUT_clean' in df.columns else 0)
    col3.metric("Total Horas Efectivas Trabajadas", f"{df['Horas_Efectivas'].sum():,.1f}" if 'Horas_Efectivas' in df.columns else "0")
    col4.metric("Días Efectivos Reportados", df['Fecha reporte'].nunique() if 'Fecha reporte' in df.columns else 0)

    # --- 5. AUDITORÍA DE DISPONIBILIDAD ---
    st.subheader("Auditoría de Disponibilidad de Equipos")
    colA, colB = st.columns(2)
    
    with colA:
        if 'Estado_Equipo' in df.columns:
            estado_counts = df['Estado_Equipo'].value_counts().reset_index()
            estado_counts.columns = ['Estado', 'Cantidad']
            fig_estado = px.pie(estado_counts, names='Estado', values='Cantidad', 
                                title='Distribución de Estados de Maquinaria', hole=0.4,
                                color_discrete_sequence=colores_corporativos)
            st.plotly_chart(fig_estado, use_container_width=True)
        
    with colB:
        if 'Equipo' in df.columns and 'Horas_Efectivas' in df.columns:
            horas_por_equipo = df.groupby('Equipo')['Horas_Efectivas'].sum().reset_index().sort_values(by='Horas_Efectivas', ascending=False).head(15)
            fig_horas = px.bar(horas_por_equipo, x='Horas_Efectivas', y='Equipo', orientation='h', 
                               title='Top 15 Equipos con Más Horas Efectivas', text='Horas_Efectivas',
                               color_discrete_sequence=['#800020'])
            fig_horas.update_traces(textposition='outside')
            st.plotly_chart(fig_horas, use_container_width=True)

    # --- 6. MÓDULO DE FACTURACIÓN (AGRUPADO POR UNIDAD Y EQUIPO) ---
    st.markdown("---")
    st.subheader("🧾 Resumen para Facturación: Días Trabajados vs Inactivos")
    
    if 'Equipo' in df.columns and 'Fecha reporte' in df.columns:
        # Agrupamos por Unidad de Negocio Y Equipo
        df_trabajados = df[df['Horas_Efectivas'] > 0].groupby(['Unidad_Negocio', 'Equipo'])['Fecha reporte'].nunique().reset_index()
        df_trabajados.rename(columns={'Fecha reporte': 'Días Trabajados (Con Horas)'}, inplace=True)
        
        df_inactivos = df[df['Horas_Efectivas'] == 0].groupby(['Unidad_Negocio', 'Equipo'])['Fecha reporte'].nunique().reset_index()
        df_inactivos.rename(columns={'Fecha reporte': 'Total Días Inactivos (0 Horas)'}, inplace=True)
        
        df_motivos = df[df['Horas_Efectivas'] == 0].groupby(['Unidad_Negocio', 'Equipo', 'Estado_Equipo'])['Fecha reporte'].nunique().unstack(fill_value=0).reset_index()
        
        resumen_facturacion = pd.merge(df_trabajados, df_inactivos, on=['Unidad_Negocio', 'Equipo'], how='outer').fillna(0)
        if not df_motivos.empty:
            resumen_facturacion = pd.merge(resumen_facturacion, df_motivos, on=['Unidad_Negocio', 'Equipo'], how='outer').fillna(0)
            
        for col in resumen_facturacion.columns:
            if col not in ['Unidad_Negocio', 'Equipo']:
                resumen_facturacion[col] = resumen_facturacion[col].astype(int)
                
        resumen_facturacion.insert(2, 'Total Días Auditados', resumen_facturacion['Días Trabajados (Con Horas)'] + resumen_facturacion['Total Días Inactivos (0 Horas)'])
        
        st.dataframe(resumen_facturacion.sort_values(by=['Unidad_Negocio', 'Equipo']), use_container_width=True)
        
        csv_facturacion = resumen_facturacion.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar Resumen para Facturación",
            data=csv_facturacion,
            file_name='resumen_facturacion_maquinaria_por_unidad.csv',
            mime='text/csv',
        )

    # --- 7. AUDITORÍA DE CAMIONETAS Y COMBUSTIBLE ---
    st.markdown("---")
    st.subheader("⛽ Auditoría de Combustible y Uso de Camionetas (CD)")

    if 'Equipo' in df.columns:
        df_cd = df[df['Equipo'].astype(str).str.contains('CD', na=False, case=False)].copy()

        if not df_cd.empty:
            cols_necesarias = ['KM. Inicial', 'KM. Final', 'Cantidad (Ingreso Combustible)']
            for col in cols_necesarias:
                if col in df_cd.columns:
                    df_cd[col] = pd.to_numeric(df_cd[col], errors='coerce').fillna(0)
                else:
                    df_cd[col] = 0

            df_cd['KM_Recorridos'] = df_cd['KM. Final'] - df_cd['KM. Inicial']
            
            df_cd['Rendimiento (KM/L)'] = df_cd.apply(
                lambda row: row['KM_Recorridos'] / row['Cantidad (Ingreso Combustible)'] 
                if row['Cantidad (Ingreso Combustible)'] > 0 else 0, axis=1
            )

            def clasificar_anomalia(row):
                anomalias = []
                if row['KM_Recorridos'] < 0: anomalias.append("Error Odómetro (Inversión)")
                if row['KM_Recorridos'] > 500: anomalias.append("Exceso KM (>500)")
                if row['Cantidad (Ingreso Combustible)'] > 0 and row['KM_Recorridos'] <= 0: anomalias.append("Carga combustible sin movimiento")
                if row['Cantidad (Ingreso Combustible)'] > 0 and row['KM_Recorridos'] > 0:
                    if row['Rendimiento (KM/L)'] < 4: anomalias.append("Alerta Fuga (< 4 KM/L)")
                    elif row['Rendimiento (KM/L)'] > 16: anomalias.append("Error Registro (> 16 KM/L)")
                if row['KM. Inicial'] == 0 and row['KM. Final'] == 0 and row['Horas_Efectivas'] > 0: anomalias.append("Trabajó sin registrar Odómetro")
                
                return " | ".join(anomalias) if anomalias else "Conforme"

            df_cd['Alerta_Auditoria'] = df_cd.apply(clasificar_anomalia, axis=1)

            c_cd1, c_cd2, c_cd3, c_cd4 = st.columns(4)
            c_cd1.metric("Total Camionetas (CD)", df_cd['Equipo'].nunique())
            c_cd2.metric("Total KM Recorridos", f"{df_cd['KM_Recorridos'].sum():,.0f}")
            c_cd3.metric("Total Lts. Cargados", f"{df_cd['Cantidad (Ingreso Combustible)'].sum():,.1f}")
            
            total_km = df_cd['KM_Recorridos'].sum()
            total_lts = df_cd['Cantidad (Ingreso Combustible)'].sum()
            rendimiento_global = total_km / total_lts if total_lts > 0 else 0
            c_cd4.metric("Rendimiento Promedio (KM/L)", f"{rendimiento_global:.1f}")

            df_anomalias = df_cd[df_cd['Alerta_Auditoria'] != "Conforme"]
            st.markdown(f"**⚠️ Inconsistencias Detectadas ({len(df_anomalias)} registros críticos)**")
            
            if not df_anomalias.empty:
                # Incluimos Unidad de Negocio en el reporte de anomalías
                cols_mostrar = ['Fecha reporte', 'Unidad_Negocio', 'Equipo', 'Nombre', 'KM. Inicial', 'KM. Final', 'KM_Recorridos', 'Cantidad (Ingreso Combustible)', 'Rendimiento (KM/L)', 'Alerta_Auditoria']
                cols_mostrar = [c for c in cols_mostrar if c in df_anomalias.columns]
                
                st.dataframe(df_anomalias[cols_mostrar].sort_values('Fecha reporte', ascending=False), use_container_width=True)
                
                csv_auditoria = df_anomalias[cols_mostrar].to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Descargar Reporte de Auditoría",
                    data=csv_auditoria,
                    file_name='auditoria_combustible_camionetas_por_unidad.csv',
                    mime='text/csv',
                )
            else:
                st.success("Toda la flota CD opera conforme a los parámetros de auditoría.")

            st.markdown("**Análisis Gráfico: Recorrido vs Consumo (Agrupado por Camioneta)**")
            resumen_grafico = df_cd.groupby(['Unidad_Negocio', 'Equipo']).agg({
                'KM_Recorridos': 'sum',
                'Cantidad (Ingreso Combustible)': 'sum'
            }).reset_index()
            
            fig_scatter = px.scatter(resumen_grafico, x='KM_Recorridos', y='Cantidad (Ingreso Combustible)', 
                                     text='Equipo', size='Cantidad (Ingreso Combustible)', color='Unidad_Negocio',
                                     title='Relación KM Recorridos vs Litros Cargados (Por Unidad de Negocio)',
                                     color_discrete_sequence=colores_corporativos)
            fig_scatter.update_traces(textposition='top center')
            st.plotly_chart(fig_scatter, use_container_width=True)

        else:
            st.info("No hay registros de camionetas ('CD') procesables en la data subida.")

    # --- 8. DETALLE GENERAL CONSOLIDADO ---
    st.markdown("---")
    st.subheader("Base Consolidada: Trazabilidad Operador vs Equipo")
    
    # Aseguramos que Unidad_Negocio y Nombre (formateado) salgan bien
    columnas_vista = ['Fecha reporte', 'Unidad_Negocio', 'Equipo', 'Estado_Equipo', 'RUT_clean', 'Nombre', 'Cargo', 'Horas_Efectivas', 'Observaciones']
    columnas_existentes = [col for col in columnas_vista if col in df.columns]
    
    if 'Equipo' in df.columns:
        st.dataframe(df[columnas_existentes].sort_values(by=['Unidad_Negocio', 'Equipo', 'Fecha reporte']), use_container_width=True)
    else:
        st.dataframe(df[columnas_existentes], use_container_width=True)
    
else:
    st.info("Por favor, sube ambos archivos (Reporte de Maquinaria y Base de Empleados) en el panel lateral para iniciar la auditoría.")
