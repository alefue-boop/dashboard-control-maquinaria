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
            return pd.DataFrame() # Retorna DataFrame vacío si no es formato válido

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
