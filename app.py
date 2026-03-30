import pandas as pd
import re
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# 1. CONFIGURACIÓN DE ESTILO CORPORATIVO
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman'] + plt.rcParams['font.serif']
sns.set_style("white")

# Paleta: Burdeo (#800020), Verde (#008000), Gris (#808080)
CORP_BURDEO = '#800020'
CORP_VERDE = '#008000'
CORP_GRIS = '#808080'

def extract_data(df):
    """Extrae litros y km desde la columna Observaciones."""
    def get_liters(text):
        if pd.isna(text): return 0.0
        match = re.search(r'litros:\s*(\d+(?:\.\d+)?)', str(text))
        return float(match.group(1)) if match else 0.0

    def get_km(text):
        if pd.isna(text): return 0.0
        match = re.search(r'total km recorridos:\s*(\d+(?:\.\d+)?)', str(text))
        return float(match.group(1)) if match else 0.0

    df['Litros'] = df['Observaciones'].apply(get_liters)
    df['KM'] = df['Observaciones'].apply(get_km)
    return df

def generate_report(file_path):
    # Cargar y filtrar datos de CD
    df = pd.read_csv(file_path)
    cd_data = df[df['Equipo'].str.contains('CD', na=False, case=False)].copy()
    cd_data = extract_data(cd_data)

    # Agrupar por equipo
    summary = cd_data.groupby('Equipo').agg({'Litros': 'sum', 'KM': 'sum'}).reset_index()
    summary['Rendimiento'] = (summary['KM'] / summary['Litros']).replace([np.inf, -np.inf], 0).fillna(0)
    
    # Filtrar solo equipos con carga para el gráfico de rendimiento
    plot_df = summary[summary['Litros'] > 0].sort_values('Rendimiento')

    # 2. CREACIÓN DEL DASHBOARD VISUAL
    fig = plt.figure(figsize=(16, 10), facecolor='#F0F0F0')
    gs = fig.add_gridspec(2, 2, height_ratios=[3, 1], width_ratios=[2, 1])

    # Gráfico Principal: Rendimiento
    ax1 = fig.add_subplot(gs[0, 0])
    colors = [CORP_BURDEO if x < 8 else CORP_VERDE if x > 14 else CORP_GRIS for x in plot_df['Rendimiento']]
    
    bars = ax1.bar(plot_df['Equipo'], plot_df['Rendimiento'], color=colors)
    ax1.axhline(plot_df['Rendimiento'].mean(), color=CORP_GRIS, linestyle='--', alpha=0.7)
    ax1.set_title('RENDIMIENTO POR EQUIPO (KM/L)', fontsize=14, fontweight='bold', pad=20)
    ax1.set_ylabel('KM / Litro', fontweight='bold')
    plt.setp(ax1.get_xticklabels(), rotation=45, ha='right')

    # Panel de Hallazgos (Texto)
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.axis('off')
    hallazgos = (
        "HALLAZGOS CLAVE (AUDITORÍA)\n\n"
        "● INCOHERENCIA CRÍTICA:\nEquipos con KM pero 0 Litros.\n(CD-191, CD-PAPA, CD-215)\n\n"
        "● BAJO RENDIMIENTO:\nCD-212 presenta 5.19 KM/L.\nPosible error de registro.\n\n"
        "● ALTA EFICIENCIA:\nCD-195, CD-201 (>15 KM/L).\nVerificar cargas completas."
    )
    ax2.text(0.1, 0.5, hallazgos, fontsize=12, va='center', bbox=dict(facecolor='white', alpha=0.5, boxstyle='round,pad=1'))

    # Tabla de Resumen Inferior
    ax3 = fig.add_subplot(gs[1, :])
    ax3.axis('off')
    table_data = summary.sort_values('KM', ascending=False).head(5).values.tolist()
    column_labels = ["EQUIPO", "LITROS TOTALES", "KM TOTALES", "RENDIMIENTO (KM/L)"]
    
    table = ax3.table(cellText=table_data, colLabels=column_labels, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2)

    plt.suptitle('ANÁLISIS DE COHERENCIA: CONSUMO DE COMBUSTIBLE CD', fontsize=18, fontweight='bold', color=CORP_BURDEO)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    # Guardar imagen para GitHub
    plt.savefig('reporte_coherencia_cd.png', dpi=300)
    print("Reporte generado exitosamente: reporte_coherencia_cd.png")

if __name__ == "__main__":
    # Reemplazar con el nombre de tu archivo cargado
    generate_report('2026-03-30T15-44_export.csv')
