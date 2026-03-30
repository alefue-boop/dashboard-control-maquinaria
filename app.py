import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración de la página
st.set_page_config(page_title="Control y Gestión de Maquinaria", layout="wide")
st.title("🚜 Dashboard de Control y Gestión de Maquinaria")

# Función para cargar y unificar los datos
@st.cache_data
def cargar_datos(report_file, empleados_file):
    
    # --- FUNCIÓN AUXILIAR PARA DETECTAR CSV O EXCEL ---
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

    # --- LECTURA DE ARCHIVOS ---
    report_df = procesar_archivo(report_file)
    employees_df = procesar_archivo(empleados_file)
    
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
        if 'panne' in obs_lower or 'panna' in obs_lower or 'falla' in obs_lower: return 'Panne/Falla'
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

    # --- SECCIÓN: RESUMEN PARA FACTURACIÓN ---
    st.markdown("---")
    st.subheader("🧾 Resumen para Facturación: Días Trabajados vs Inactivos")
    
    if 'Equipo' in df.columns and 'Fecha reporte' in df.columns:
        df_trabajados = df[df['Horas_Efectivas'] > 0].groupby('Equipo')['Fecha reporte'].nunique().reset_index()
        df_trabajados.rename(columns={'Fecha reporte': 'Días Trabajados'}, inplace=True)
        
        df_inactivos_totales = df[df['Horas_Efectivas'] == 0].groupby('Equipo')['Fecha reporte'].nunique().reset_index()
        df_inactivos_totales.rename(columns={'Fecha reporte': 'Total Días Inactivos'}, inplace=True)
        
        df_motivos = df[df['Horas_Efectivas'] == 0].groupby(['Equipo', 'Estado_Equipo'])['Fecha reporte'].nunique().unstack(fill_value=0).reset_index()
        
        resumen_facturacion = pd.merge(df_trabajados, df_inactivos_totales, on='Equipo', how='outer').fillna(0)
        
        if not df_motivos.empty:
            resumen_facturacion = pd.merge(resumen_facturacion, df_motivos, on='Equipo', how='outer').fillna(0)
            
        for col in resumen_facturacion.columns:
            if col != 'Equipo':
                resumen_facturacion[col] = resumen_facturacion[col].astype(int)
                
        resumen_facturacion.insert(1, 'Total Días Mes', resumen_facturacion['Días Trabajados'] + resumen_facturacion['Total Días Inactivos'])
        
        st.dataframe(resumen_facturacion, use_container_width=True)
        
        csv_facturacion = resumen_facturacion.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar Resumen para Facturación (CSV)",
            data=csv_facturacion,
            file_name='resumen_facturacion_maquinaria.csv',
            mime='text/csv',
        )

    # --- NUEVA SECCIÓN: AUDITORÍA DE CAMIONETAS (CD) Y COMBUSTIBLE ---
    st.markdown("---")
    st.subheader("⛽ Auditoría de Combustible y Uso de Camionetas (CD)")

    if 'Equipo' in df.columns:
        # Filtrar solo equipos que empiecen o contengan "CD"
        df_cd = df[df['Equipo'].astype(str).str.contains('CD', na=False, case=False)].copy()

        if not df_cd.empty:
            # Asegurar que las columnas clave para esta auditoría existan y sean numéricas
            cols_necesarias = ['KM. Inicial', 'KM. Final', 'Cantidad (Ingreso Combustible)']
            for col in cols_necesarias:
                if col in df_cd.columns:
                    df_cd[col] = pd.to_numeric(df_cd[col], errors='coerce').fillna(0)
                else:
                    df_cd[col] = 0

            # Cálculos de auditoría
            df_cd['KM_Recorridos'] = df_cd['KM. Final'] - df_cd['KM. Inicial']
            
            # Rendimiento diario referencial
            df_cd['Rendimiento (KM/L)'] = df_cd.apply(
                lambda row: row['KM_Recorridos'] / row['Cantidad (Ingreso Combustible)'] 
                if row['Cantidad (Ingreso Combustible)'] > 0 else 0, 
                axis=1
            )

            # Algoritmo de Detección de Anomalías
            def clasificar_anomalia(row):
                anomalias = []
                if row['KM_Recorridos'] < 0:
                    anomalias.append("Error Odómetro (KM Final < Inicial)")
                if row['KM_Recorridos'] > 500:
                    anomalias.append("Exceso KM Diario (>500 km)")
                if row['Cantidad (Ingreso Combustible)'] > 0 and row['KM_Recorridos'] == 0:
                    anomalias.append("Carga combustible sin movimiento")
                if row['Cantidad (Ingreso Combustible)'] > 0 and row['KM_Recorridos'] > 0:
                    if row['Rendimiento (KM/L)'] < 5:
                        anomalias.append("Rendimiento crítico (< 5 KM/L)")
                    elif row['Rendimiento (KM/L)'] > 15:
                        anomalias.append("Rendimiento irreal (> 15 KM/L)")
                if row['KM. Inicial'] == 0 and row['KM. Final'] == 0 and row['Horas_Efectivas'] > 0:
                    anomalias.append("Trabajó sin registrar KM")
                
                return " | ".join(anomalias) if anomalias else "OK"

            df_cd['Alerta_Auditoria'] = df_cd.apply(clasificar_anomalia, axis=1)

            # Mostrar KPIs de Camionetas
            st.markdown("##### Indicadores Globales de la Flota CD")
            c_cd1, c_cd2, c_cd3, c_cd4 = st.columns(4)
            c_cd1.metric("Total Camionetas", df_cd['Equipo'].nunique())
            c_cd2.metric("Total KM Recorridos", f"{df_cd['KM_Recorridos'].sum():,.0f}")
            c_cd3.metric("Total Litros Combustible", f"{df_cd['Cantidad (Ingreso Combustible)'].sum():,.1f}")
            
            total_km = df_cd['KM_Recorridos'].sum()
            total_lts = df_cd['Cantidad (Ingreso Combustible)'].sum()
            rendimiento_global = total_km / total_lts if total_lts > 0 else 0
            c_cd4.metric("Rendimiento Global Flota (KM/L)", f"{rendimiento_global:.1f}")

            # Filtrar e imprimir las anomalías
            df_anomalias = df_cd[df_cd['Alerta_Auditoria'] != "OK"]
            
            st.markdown(f"##### ⚠️ Alertas Detectadas ({len(df_anomalias)} registros anómalos)")
            
            if not df_anomalias.empty:
                cols_mostrar = ['Fecha reporte', 'Equipo', 'Operador_clean', 'Nombre', 'KM. Inicial', 'KM. Final', 'KM_Recorridos', 'Cantidad (Ingreso Combustible)', 'Rendimiento (KM/L)', 'Alerta_Auditoria']
                cols_mostrar = [c for c in cols_mostrar if c in df_anomalias.columns]
                
                st.dataframe(df_anomalias[cols_mostrar].sort_values('Fecha reporte', ascending=False), use_container_width=True)
                
                csv_auditoria = df_anomalias[cols_mostrar].to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Descargar Reporte de Anomalías (CSV)",
                    data=csv_auditoria,
                    file_name='auditoria_combustible_camionetas.csv',
                    mime='text/csv',
                )
            else:
                st.success("¡Excelente! No se detectaron anomalías en las camionetas bajo los parámetros actuales.")

            # Gráfico Comparativo
            st.markdown("##### Análisis Gráfico: Recorrido vs Consumo de Combustible por Camioneta")
            resumen_grafico = df_cd.groupby('Equipo').agg({
                'KM_Recorridos': 'sum',
                'Cantidad (Ingreso Combustible)': 'sum'
            }).reset_index()
            
            fig_scatter = px.scatter(resumen_grafico, x='KM_Recorridos', y='Cantidad (Ingreso Combustible)', 
                                     text='Equipo', size='Cantidad (Ingreso Combustible)', color='Equipo',
                                     title='Relación KM Recorridos vs Litros Cargados')
            fig_scatter.update_traces(textposition='top center')
            st.plotly_chart(fig_scatter, use_container_width=True)

        else:
            st.info("No hay registros de camionetas ('CD') en este periodo para analizar combustible.")

    # Detalle de Trabajador vs Equipo
    st.markdown("---")
    st.subheader("Detalle General: ¿Qué trabajador está usando qué equipo?")
    
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
