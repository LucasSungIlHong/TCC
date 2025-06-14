import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import logging
from scipy.signal import savgol_filter # Importar Savitzky-Golay

# ANÁLISE ENERGÉTICA #

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Lista de arquivos e graus de hibridização
files = {
    '15%': 'resultados_suave_15.csv',
    '20%': 'resultados_suave_20.csv',
    '30%': 'resultados_suave_30.csv',
    'Convencional': 'resultados_suave_convencional.csv'
}

# Lista de colunas numéricas a serem convertidas
numeric_columns = [
    'time', 'altitude_m', 'mach_number', 'velocity_m_s', 'pressure_Pa',
    'density_kg_m3', 'temperature_C', 'lift_coefficient', 'drag_coefficient',
    'angle_of_attack_rad', 'flight_path_angle_rad', 'mass_kg', 'mass_flow_kg_s',
    'CG_m', 'CG_percent', 'throttle', 'battery_energy', 'battery_voltage',
    'battery_voltage_under_load', 'battery_voltage_open_circuit',
    'state_of_charge', 'rpm', 'rpm_wtp', 'battery_resistive_losses',
    'emotor_efficiency', 'emotorWTP_efficiency', 'combustion_engine_throttle',
    'beta_propeller', 'eta_propeller', 'cp_propeller', 'ct_propeller',
    'j_propeller', 'rpm_propeller', 'thrust_propeller', 'beta_propellerWTP',
    'eta_propellerWTP', 'cp_propellerWTP', 'ct_propellerWTP', 'j_propellerWTP',
    'rpm_propellerWTP', 'thrust_propellerWTP', 'power_WTP', 'propeller_rpm',
    'battery_current', 'battery_draw', 'propeller_motor_torque',
    'propeller_torque', 'battery_specfic_power', 'propeller_tip_mach',
    'propeller_power_coefficient', 'gas_turbine_p3', 'gas_turbine_t3',
    'gas_turbine_far', 'electric_throttle', 'electric_throttle_WTP',
    'disc_loading', 'power_loading', 'propeller_thrust', 'power',
    'heat_load_vcs', 'tms_mdot_air_vcs', 'heat_load_liquid',
    'tms_mdot_air_liquid', 'thrust_turboprop', 'thrust_WTP',
    'power_propeller_turboprop', 'power_turboshaft', 'power_motor_turboprop',
    'power_propeller_WTP', 'propellerWTP_tip_mach', 'co_emissions_index',
    'co2_emissions_index', 'nox_emissions_index', 'co_emissions_total',
    'co2_emissions_total', 'nox_emissions_total', 'l_over_d', 'weight',
    'lift', 'drag', 'etap'
]

# Dicionário para armazenar os DataFrames
dfs = {}

# Carregar e processar cada planilha
for hybrid_degree, file_path in files.items():
    try:
        df = pd.read_csv(file_path, delimiter=';')
    except Exception as e:
        logging.error(f"Erro ao carregar {file_path}: {e}")
        continue

    if df.empty:
        logging.warning(f"Arquivo {file_path} está vazio ou mal formatado.")
        continue

    if hybrid_degree == 'Convencional':
        if 'etap' in df.columns:
            df['eta_propeller'] = df['etap']
        else:
            df['eta_propeller'] = 0
        if 'propeller_thrust' in df.columns:
            df['thrust_turboprop'] = df['propeller_thrust']
        else:
            df['thrust_turboprop'] = 0
        for col_to_zero in ['thrust_WTP', 'emotor_efficiency', 'electric_throttle',
                            'battery_energy', 'power_motor_turboprop', 'power_propeller_WTP']:
            df[col_to_zero] = 0
        if 'power_propeller_turboprop' not in df.columns or df['power_propeller_turboprop'].fillna(0).sum() == 0:
             if 'power' in df.columns:
                df['power_propeller_turboprop'] = df['power']

    for col in numeric_columns:
        if col in df.columns:
            if df[col].dtype == object:
                df[col] = pd.to_numeric(df[col].str.replace(',', '.'), errors='coerce')
            else:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            if df[col].isnull().any():
                df[col] = df[col].fillna(0)
        else:
            df[col] = 0

    df['eta_propeller'] = df['eta_propeller'].fillna(0)
    if hybrid_degree == 'Convencional':
        mask = (df['eta_propeller'] == 0) & \
               (df['thrust_turboprop'].fillna(0) > 0) & \
               (df['velocity_m_s'].fillna(0) > 0) & \
               (df['power'].fillna(0).replace(0, np.nan).notna())

        if mask.any():
            power_divisor = df.loc[mask, 'power'].replace(0, np.nan)
            df.loc[mask, 'eta_propeller'] = (df.loc[mask, 'thrust_turboprop'] * df.loc[mask, 'velocity_m_s']) / power_divisor
            df['eta_propeller'] = df['eta_propeller'].fillna(0).clip(lower=0, upper=1)
        elif df['eta_propeller'].eq(0).all():
            df['eta_propeller'] = 0.8

    df['propeller_thrust'] = df['propeller_thrust'].fillna(0)
    df['thrust_WTP'] = df['thrust_WTP'].fillna(0)
    if hybrid_degree == 'Convencional':
        df['total_thrust'] = df['thrust_propeller']
    else:
        df['total_thrust'] = df['propeller_thrust'] + df['thrust_WTP']

    df['electric_throttle'] = df['electric_throttle'].fillna(0)
    df['emotor_efficiency'] = df['emotor_efficiency'].fillna(0)
    if hybrid_degree == 'Convencional':
        df['global_efficiency'] = df['eta_propeller']
    else:
        df['global_efficiency'] = np.where(
            df['electric_throttle'] > 0,
            df['emotor_efficiency'] * df['eta_propeller'],
            df['eta_propeller']
        )
    df['global_efficiency'] = df['global_efficiency'].fillna(0).clip(lower=0, upper=1)

    delta_time = df['time'].diff().fillna(0)
    df['velocity_m_s'] = df['velocity_m_s'].fillna(0)
    df['distance_interval'] = df['velocity_m_s'] * delta_time
    df['power'] = df['power'].fillna(0)
    df['interval_energy_consumption'] = df['power'] * delta_time
    logging.info(f"{hybrid_degree} ({file_path}): Calculando energia de eixo. 'power' total sum: {df['power'].sum():.2f}, 'interval_energy_consumption' (eixo) sum: {df['interval_energy_consumption'].sum():.2f}")

    df['specific_energy_consumption'] = (df['interval_energy_consumption'] / df['distance_interval'].replace(0, np.nan))
    df.loc[df['distance_interval'] == 0, 'specific_energy_consumption'] = 0
    df['specific_energy_consumption'] = df['specific_energy_consumption'].fillna(0)
    df['specific_energy_consumption'].replace([np.inf, -np.inf], 0, inplace=True)

    df['total_energy_consumption'] = df['interval_energy_consumption']

    if hybrid_degree != 'Convencional' and 'etap' not in df.columns:
        df['etap'] = 0

    dfs[hybrid_degree] = df

colors = {'15%': 'blue', '20%': 'red', '30%': 'green', 'Convencional': 'black'}

# --- DEFINIÇÃO DE TAMANHOS DE FONTE ---
legend_fontsize = 11
axis_label_fontsize = 12
tick_label_fontsize = 10

def place_legend_below(ax=None, ncol=None, fontsize=legend_fontsize):
    if ax is None:
        ax = plt.gca()
    handles, labels = ax.get_legend_handles_labels()
    if not handles:
        return

    num_items = len(handles)
    if ncol is None:
        if num_items <= 2:
            ncol = num_items
        elif num_items <= 4:
            ncol = 2
        else:
            ncol = 3
        if ncol == 0: ncol = 1

    ax.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, -0.22),
              ncol=ncol, fancybox=True, shadow=False, borderaxespad=0., fontsize=fontsize)

# Ajustes de figura e layout
figure_width = 10
figure_height = 10
tight_layout_rect = [0.12, 0.20, 0.95, 0.93]


# Plot 1: Energia da Bateria vs Tempo (apenas híbridos)
plt.figure(figsize=(figure_width, figure_height))
ax1 = plt.gca()
has_hybrid_data_p1 = False
for hybrid_degree, df in dfs.items():
    if hybrid_degree != 'Convencional':
        if 'battery_energy' in df.columns and not df['battery_energy'].fillna(0).eq(0).all():
            ax1.plot(df['time'] / 60, df['battery_energy'] / 1000, color=colors[hybrid_degree], label=f'Energia Bat. (kJ) - {hybrid_degree}')
            has_hybrid_data_p1 = True
plt.title('Energia das Baterias')
plt.xlabel('Tempo (min)', fontsize=axis_label_fontsize)
plt.ylabel('Energia (kJ)', fontsize=axis_label_fontsize)
ax1.tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
plt.grid(True)
if has_hybrid_data_p1:
    place_legend_below(ax1, ncol=3)
else:
    ax1.text(0.5, 0.5, "Sem dados de bateria para exibir", horizontalalignment='center', verticalalignment='center', transform=ax1.transAxes)
plt.tight_layout(rect=tight_layout_rect)
plt.savefig('battery_energy_vs_time.png')
plt.close()

# Plot 2: Consumo de Potência vs Tempo
plt.figure(figsize=(figure_width, figure_height))
ax2 = plt.gca()
for hybrid_degree, df in dfs.items():
    ax2.plot(df['time'] / 60, df['power'] / 1000, color=colors[hybrid_degree], label=f'Potência Eixo Total (kW) - {hybrid_degree}')
plt.title('Potência de Eixo Total')
plt.xlabel('Tempo (min)', fontsize=axis_label_fontsize)
plt.ylabel('Potência de Eixo Total (kW)', fontsize=axis_label_fontsize)
ax2.tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
plt.grid(True)
place_legend_below(ax2)
plt.tight_layout(rect=tight_layout_rect)
plt.savefig('power_consumption_vs_time.png')
plt.close()

# Plot 3: Eficiência do Motor Elétrico vs Tempo (apenas híbridos)
plt.figure(figsize=(figure_width, figure_height))
ax3 = plt.gca()
has_hybrid_data_p3 = False
for hybrid_degree, df in dfs.items():
    if hybrid_degree != 'Convencional':
        if 'emotor_efficiency' in df.columns and not df['emotor_efficiency'].fillna(0).eq(0).all():
            ax3.plot(df['time'] / 60, df['emotor_efficiency'] * 100, color=colors[hybrid_degree], label=f'Eficiência Mot. Elét. (%) - {hybrid_degree}')
            has_hybrid_data_p3 = True
plt.title('Eficiência do Motor Elétrico')
plt.xlabel('Tempo (min)', fontsize=axis_label_fontsize)
plt.ylabel('Eficiência Energética (%)', fontsize=axis_label_fontsize)
ax3.tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
plt.grid(True)
if has_hybrid_data_p3:
    place_legend_below(ax3, ncol=3)
else:
    ax3.text(0.5, 0.5, "Sem dados de eficiência de motor elétrico para exibir", horizontalalignment='center', verticalalignment='center', transform=ax3.transAxes)
plt.tight_layout(rect=tight_layout_rect)
plt.savefig('emotor_efficiency_vs_time.png')
plt.close()

# Plot 3-Zoom: Eficiência do Motor Elétrico vs Tempo (Zoom nos Picos)
plt.figure(figsize=(figure_width, figure_height))
ax3_zoom = plt.gca()
has_hybrid_data_p3_zoom = False

# Encontrar o pico de eficiência para definir o centro do zoom
max_peak_eff = 0
for hybrid_degree, df in dfs.items():
    if hybrid_degree != 'Convencional' and 'emotor_efficiency' in df.columns:
        non_zero_data = df[df['emotor_efficiency'] > 0]['emotor_efficiency'] * 100
        if not non_zero_data.empty:
            max_peak_eff = max(max_peak_eff, non_zero_data.max())

if max_peak_eff > 0:
    for hybrid_degree, df in dfs.items():
        if hybrid_degree != 'Convencional' and 'emotor_efficiency' in df.columns:
            if not df['emotor_efficiency'].fillna(0).eq(0).all():
                ax3_zoom.plot(df['time'] / 60, df['emotor_efficiency'] * 100, color=colors[hybrid_degree], label=f'Eficiência Mot. Elét. (%) - {hybrid_degree}')
                has_hybrid_data_p3_zoom = True

    plt.title('Eficiência do Motor Elétrico')
    plt.xlabel('Tempo (min)', fontsize=axis_label_fontsize)
    plt.ylabel('Eficiência Energética (%)', fontsize=axis_label_fontsize)
    ax3_zoom.tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
    plt.grid(True)

    # Definir a escala do eixo Y para focar apenas nos picos de eficiencia.
    zoom_window_size = 0.1  # Janela de 1 pontos percentuais abaixo do pico
    lower_bound = max(0, max_peak_eff - zoom_window_size)
    upper_bound = min(100, max_peak_eff + 0.02) # Adiciona 1% de espaço acima do pico
    ax3_zoom.set_ylim(lower_bound, upper_bound)

    if has_hybrid_data_p3_zoom:
        place_legend_below(ax3_zoom, ncol=3)

    plt.tight_layout(rect=tight_layout_rect)
    plt.savefig('emotor_efficiency_vs_time_zoom.png')
plt.close()

# Plot 4: Tração Total vs Tempo
plt.figure(figsize=(figure_width, figure_height))
ax4 = plt.gca()
for hybrid_degree, df in dfs.items():
    ax4.plot(df['time'] / 60, df['total_thrust'], color=colors[hybrid_degree], label=f'Tração Total (kN) - {hybrid_degree}')
plt.title('Tração Total')
plt.xlabel('Tempo (min)', fontsize=axis_label_fontsize)
plt.ylabel('Tração Total (kN)', fontsize=axis_label_fontsize)
ax4.tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
plt.grid(True)
place_legend_below(ax4)
plt.tight_layout(rect=tight_layout_rect)
plt.savefig('total_thrust_vs_time.png')
plt.close()

# Plot 5: Perfil de Altitude vs Tempo
plt.figure(figsize=(figure_width, figure_height))
ax5 = plt.gca()
for hybrid_degree, df in dfs.items():
    ax5.plot(df['time'] / 60, df['altitude_m'], color=colors[hybrid_degree], label=f'Altitude (m) - {hybrid_degree}')
plt.title('Perfil da Missão')
plt.xlabel('Tempo (min)', fontsize=axis_label_fontsize)
plt.ylabel('Altitude (m)', fontsize=axis_label_fontsize)
ax5.tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
plt.grid(True)
place_legend_below(ax5)
plt.tight_layout(rect=tight_layout_rect)
plt.savefig('altitude_vs_time.png')
plt.close()

# Plot 6: Eficiência Energética Global do Sistema Propulsivo
plt.figure(figsize=(figure_width, figure_height))
ax6 = plt.gca()
for hybrid_degree, df in dfs.items():
    ax6.plot(df['time'] / 60, df['global_efficiency'] * 100, color=colors[hybrid_degree], label=f'Eficiência Global (%) - {hybrid_degree}')
plt.title('Eficiência Energética Global do Sistema Propulsivo')
plt.xlabel('Tempo (min)', fontsize=axis_label_fontsize)
plt.ylabel('Eficiência Energética (%)', fontsize=axis_label_fontsize)
ax6.tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
plt.grid(True)
ax6.set_ylim(0, 100) # Força a escala do eixo Y de 0 a 100
place_legend_below(ax6)
plt.tight_layout(rect=tight_layout_rect)
plt.savefig('global_efficiency_vs_time.png')
plt.close()

# Plot 7: Consumo Específico de Energia DE EIXO vs Tempo
plt.figure(figsize=(figure_width, figure_height))
ax7 = plt.gca()
savgol_window = 51
savgol_polyorder = 3
logging.info(f"Usando filtro Savitzky-Golay (janela={savgol_window}, ordem={savgol_polyorder}) para Consumo Específico de Energia de Eixo.")

for hybrid_degree, df in dfs.items():
    data_to_plot = df['specific_energy_consumption'].copy()
    if len(data_to_plot) > savgol_window:
        data_to_plot_smooth = savgol_filter(data_to_plot, window_length=savgol_window, polyorder=savgol_polyorder)
    else:
        logging.warning(f"Não há pontos suficientes para o filtro Savitzky-Golay em {hybrid_degree} (got {len(data_to_plot)}, need > {savgol_window}). Usando dados originais.")
        data_to_plot_smooth = data_to_plot.values

    data_to_plot_smooth = pd.Series(data_to_plot_smooth).fillna(0).values

    ax7.plot(df['time'] / 60, data_to_plot_smooth / 1000, color=colors[hybrid_degree], label=f'Cons. Esp. Eixo (kJ/m) - {hybrid_degree}')

plt.title('Consumo Específico de Potência de Eixo')
plt.xlabel('Tempo (min)', fontsize=axis_label_fontsize)
plt.ylabel('Consumo Específico de Potência de Eixo (kJ/m)', fontsize=axis_label_fontsize)
ax7.tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
plt.grid(True)
place_legend_below(ax7)
plt.tight_layout(rect=tight_layout_rect)
plt.savefig('specific_shaft_energy_consumption_vs_time.png')
plt.close()

# Plot 8: Emissões de CO2 Total vs Tempo
plt.figure(figsize=(figure_width, figure_height))
ax8 = plt.gca()
for hybrid_degree, df in dfs.items():
    ax8.plot(df['time'] / 60, df['co2_emissions_total'], color=colors[hybrid_degree], label=f'Emissões CO2 (kg) - {hybrid_degree}')
plt.title('Emissões Totais de CO2')
plt.xlabel('Tempo (min)', fontsize=axis_label_fontsize)
plt.ylabel('Emissões de CO2 (kg)', fontsize=axis_label_fontsize)
ax8.tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
plt.grid(True)
place_legend_below(ax8)
plt.tight_layout(rect=tight_layout_rect)
plt.savefig('co2_emissions_vs_time.png')
plt.close()

# Plot 9: Eficiência Propulsiva vs Velocidade
plt.figure(figsize=(figure_width, figure_height))
ax9 = plt.gca()
for hybrid_degree, df in dfs.items():
    ax9.scatter(df['velocity_m_s'], df['eta_propeller'] * 100, color=colors[hybrid_degree], label=f'Eficiência Propulsiva (%) - {hybrid_degree}', alpha=0.5, s=10)
plt.title('Eficiência Propulsiva')
plt.xlabel('Velocidade (m/s)', fontsize=axis_label_fontsize)
plt.ylabel('Eficiência Energética (%)', fontsize=axis_label_fontsize)
ax9.tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
plt.grid(True)
ax9.set_ylim(0, 100) # Força a escala do eixo Y de 0 a 100
place_legend_below(ax9)
plt.tight_layout(rect=tight_layout_rect)
plt.savefig('propulsive_efficiency_vs_velocity.png')
plt.close()

# Plot 10: Perdas Resistivas da Bateria vs Tempo (apenas híbridos)
plt.figure(figsize=(figure_width, figure_height))
ax10 = plt.gca()
has_hybrid_data_p10 = False
for hybrid_degree, df in dfs.items():
    if hybrid_degree != 'Convencional':
        if 'battery_resistive_losses' in df.columns and not df['battery_resistive_losses'].fillna(0).eq(0).all():
            ax10.plot(df['time'] / 60, df['battery_resistive_losses'], color=colors[hybrid_degree], label=f'Perdas Resistivas (W) - {hybrid_degree}')
            has_hybrid_data_p10 = True
plt.title('Perdas Resistivas das Baterias')
plt.xlabel('Tempo (min)', fontsize=axis_label_fontsize)
plt.ylabel('Perdas Resistivas (W)', fontsize=axis_label_fontsize)
ax10.tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
plt.grid(True)
if has_hybrid_data_p10:
    place_legend_below(ax10, ncol=3)
else:
    ax10.text(0.5, 0.5, "Sem dados de perdas resistivas para exibir", horizontalalignment='center', verticalalignment='center', transform=ax10.transAxes)
plt.tight_layout(rect=tight_layout_rect)
plt.savefig('battery_resistive_losses_vs_time.png')
plt.close()

# Salvar os dados calculados em arquivos separados
for hybrid_degree, df in dfs.items():
    output_cols = [
        'time', 'total_energy_consumption', 'power', 'emotor_efficiency', 'power_propeller_turboprop',
        'total_thrust', 'altitude_m', 'global_efficiency',
        'specific_energy_consumption', 'co2_emissions_total',
        'eta_propeller', 'battery_resistive_losses'
    ]
    df_to_save = df[output_cols].copy()
    df_to_save.to_csv(f'energy_analysis_results_{hybrid_degree.replace("%", "")}.csv', index=False)
