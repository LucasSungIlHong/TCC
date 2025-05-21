import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import logging

# Configurar logging para debug
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')

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
for hybrid_degree, file in files.items():
    try:
        # Carregar os dados do CSV
        df = pd.read_csv(file, delimiter=';')
    except Exception as e:
        logging.error(f"Erro ao carregar {file}: {e}")
        continue

    # Verificar se o DataFrame está vazio
    if df.empty:
        logging.warning(f"Arquivo {file} está vazio ou mal formatado.")
        continue

    # Mapear colunas do convencional para corresponder aos híbridos
    if hybrid_degree == 'Convencional':
        # Renomear etap para eta_propeller
        if 'etap' in df.columns:
            df['eta_propeller'] = df['etap']
        else:
            df['eta_propeller'] = 0
            logging.warning(f"Coluna etap ausente em {file}. Definindo eta_propeller como 0.")
        
        # Usar propeller_thrust como thrust_turboprop
        if 'propeller_thrust' in df.columns:
            df['thrust_turboprop'] = df['propeller_thrust']
        else:
            df['thrust_turboprop'] = 0
            logging.warning(f"Coluna propeller_thrust ausente em {file}. Definindo thrust_turboprop como 0.")
        
        # Definir colunas elétricas como 0
        for col in ['thrust_WTP', 'emotor_efficiency', 'electric_throttle', 'battery_energy', 'power_motor_turboprop']:
            df[col] = 0

    # Converter colunas para numérico, tratando vírgulas como ponto decimal
    for col in numeric_columns:
        if col in df.columns:
            if df[col].dtype == object:  # Verifica se a coluna é do tipo string
                df[col] = pd.to_numeric(df[col].str.replace(',', '.'), errors='coerce')
            else:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        else:
            df[col] = 0  # Define como 0 para colunas ausentes
            logging.warning(f"Coluna {col} ausente em {file}. Definindo como 0.")

    # Calcular propulsive efficiency se eta_propeller for 0 ou NaN
    df['eta_propeller'] = df['eta_propeller'].fillna(0)
    if hybrid_degree == 'Convencional':
        # Para convencional, calcular eta_propeller se necessário
        mask = (df['eta_propeller'] == 0) & (df['thrust_turboprop'] > 0) & (df['velocity_m_s'] > 0) & (df['power'] > 0)
        if mask.any():
            df.loc[mask, 'eta_propeller'] = (df.loc[mask, 'thrust_turboprop'] * df.loc[mask, 'velocity_m_s']) / df.loc[mask, 'power']
            df['eta_propeller'] = df['eta_propeller'].clip(lower=0, upper=1)  # Garantir 0 <= eta <= 1
            logging.info(f"Calculada eta_propeller para {file} usando thrust_turboprop, velocity_m_s e power.")
        elif df['eta_propeller'].eq(0).all():
            df['eta_propeller'] = 0.8  # Fallback para valor padrão
            logging.warning(f"Não foi possível calcular eta_propeller para {file}. Usando valor padrão 0.8.")

    # Calcular consumo total de energia ao longo do tempo (em Joules)
    df['total_energy_consumption'] = df['battery_energy'].diff().fillna(0) * -1

    # Calcular empuxo total (em kN)
    if hybrid_degree == 'Convencional':
        df['total_thrust'] = df['propeller_thrust']
        if df['total_thrust'].eq(0).all():
            logging.warning(f"total_thrust é zero para {file}. Verifique thrust_turboprop/propeller_thrust.")
    else:
        df['total_thrust'] = df['propeller_thrust'] + df['thrust_WTP']

    # Calcular rendimento global da aeronave ajustado
    if hybrid_degree == 'Convencional':
        df['global_efficiency'] = df['eta_propeller']
    else:
        df['global_efficiency'] = np.where(
            df['electric_throttle'] > 0,
            df['emotor_efficiency'] * df['eta_propeller'],  # Motor elétrico ativo
            df['eta_propeller']  # Motor elétrico inativo
        )

    # Garantir que global_efficiency esteja entre 0 e 1
    df['global_efficiency'] = df['global_efficiency'].clip(lower=0, upper=1)

    # Calcular consumo específico de energia (energia por distância percorrida, J/m)
    df['distance'] = (df['velocity_m_s'] * df['time'].diff().fillna(0)).cumsum()
    df['specific_energy_consumption'] = df['total_energy_consumption'] / df['distance'].replace(0, np.nan)  # J/m

    # Armazenar o DataFrame processado
    dfs[hybrid_degree] = df

# Definir cores para cada grau de hibridização
colors = {'15%': 'blue', '20%': 'red', '30%': 'green', 'Convencional': 'black'}

# Plot 1: Energia da Bateria vs Tempo (apenas híbridos)
plt.figure(figsize=(8, 6))
for hybrid_degree, df in dfs.items():
    if hybrid_degree != 'Convencional':
        plt.plot(df['time'], df['battery_energy'], color=colors[hybrid_degree], label=f'Energia da Bateria (J) - {hybrid_degree}')
plt.title('Energia da Bateria ao Longo do Tempo')
plt.xlabel('Tempo (s)')
plt.ylabel('Energia (J)')
plt.grid(True)
plt.legend()
plt.savefig('battery_energy_vs_time.png')
plt.close()

# Plot 2: Consumo de Potência vs Tempo
plt.figure(figsize=(8, 6))
for hybrid_degree, df in dfs.items():
    plt.plot(df['time'], df['power'], color=colors[hybrid_degree], label=f'Potência (W) - {hybrid_degree}')
plt.title('Consumo de Potência ao Longo do Tempo')
plt.xlabel('Tempo (s)')
plt.ylabel('Potência (W)')
plt.grid(True)
plt.legend()
plt.savefig('power_consumption_vs_time.png')
plt.close()

# Plot 3: Eficiência do Motor Elétrico vs Tempo (apenas híbridos)
plt.figure(figsize=(8, 6))
for hybrid_degree, df in dfs.items():
    if hybrid_degree != 'Convencional':
        plt.plot(df['time'], df['emotor_efficiency'], color=colors[hybrid_degree], label=f'Eficiência do Motor - {hybrid_degree}')
plt.title('Eficiência do Motor Elétrico ao Longo do Tempo')
plt.xlabel('Tempo (s)')
plt.ylabel('Eficiência')
plt.grid(True)
plt.legend()
plt.savefig('emotor_efficiency_vs_time.png')
plt.close()

# Plot 4: Empuxo Total vs Tempo
plt.figure(figsize=(8, 6))
for hybrid_degree, df in dfs.items():
    plt.plot(df['time'], df['total_thrust'], color=colors[hybrid_degree], label=f'Tração Total (kN) - {hybrid_degree}')
plt.title('Tração Total ao Longo do Tempo')
plt.xlabel('Tempo (s)')
plt.ylabel('Tração (kN)')
plt.grid(True)
plt.legend()
plt.savefig('total_thrust_vs_time.png')
plt.close()

# Plot 5: Perfil de Altitude vs Tempo
plt.figure(figsize=(8, 6))
for hybrid_degree, df in dfs.items():
    plt.plot(df['time'], df['altitude_m'], color=colors[hybrid_degree], label=f'Altitude (m) - {hybrid_degree}')
plt.title('Perfil de Altitude ao Longo do Tempo')
plt.xlabel('Tempo (s)')
plt.ylabel('Altitude (m)')
plt.grid(True)
plt.legend()
plt.savefig('altitude_vs_time.png')
plt.close()

# Plot 6: Rendimento Global da Aeronave vs Tempo
plt.figure(figsize=(8, 6))
for hybrid_degree, df in dfs.items():
    plt.plot(df['time'], df['global_efficiency'], color=colors[hybrid_degree], label=f'Rendimento Global - {hybrid_degree}')
plt.title('Rendimento Global da Aeronave ao Longo do Tempo')
plt.xlabel('Tempo (s)')
plt.ylabel('Rendimento Global')
plt.grid(True)
plt.legend()
plt.savefig('global_efficiency_vs_time.png')
plt.close()

# Plot 7: Consumo Específico de Energia vs Tempo
plt.figure(figsize=(8, 6))
for hybrid_degree, df in dfs.items():
    plt.plot(df['time'], df['specific_energy_consumption'], color=colors[hybrid_degree], label=f'Consumo Específico (J/m) - {hybrid_degree}')
plt.title('Consumo Específico de Energia ao Longo do Tempo')
plt.xlabel('Tempo (s)')
plt.ylabel('Consumo Específico de Energia (J/m)')
plt.grid(True)
plt.legend()
plt.savefig('specific_energy_consumption_vs_time.png')
plt.close()

# Plot 8: Emissões de CO2 Total vs Tempo
plt.figure(figsize=(8, 6))
for hybrid_degree, df in dfs.items():
    plt.plot(df['time'], df['co2_emissions_total'], color=colors[hybrid_degree], label=f'Emissões de CO2 (kg) - {hybrid_degree}')
plt.title('Emissões Totais de CO2 ao Longo do Tempo')
plt.xlabel('Tempo (s)')
plt.ylabel('Emissões de CO2 (kg)')
plt.grid(True)
plt.legend()
plt.savefig('co2_emissions_vs_time.png')
plt.close()

# Plot 9: Eficiência Propulsiva vs Velocidade
plt.figure(figsize=(8, 6))
for hybrid_degree, df in dfs.items():
    plt.scatter(df['velocity_m_s'], df['eta_propeller'], color=colors[hybrid_degree], label=f'Eficiência Propulsiva - {hybrid_degree}', alpha=0.6)
plt.title('Eficiência Propulsiva em Função da Velocidade')
plt.xlabel('Velocidade (m/s)')
plt.ylabel('Eficiência Propulsiva')
plt.grid(True)
plt.legend()
plt.savefig('propulsive_efficiency_vs_velocity.png')
plt.close()

# Plot 10: Perdas Resistivas da Bateria vs Tempo (apenas híbridos)
plt.figure(figsize=(8, 6))
for hybrid_degree, df in dfs.items():
    if hybrid_degree != 'Convencional':
        plt.plot(df['time'], df['battery_resistive_losses'], color=colors[hybrid_degree], label=f'Perdas Resistivas (W) - {hybrid_degree}')
plt.title('Perdas Resistivas da Bateria ao Longo do Tempo')
plt.xlabel('Tempo (s)')
plt.ylabel('Perdas Resistivas (W)')
plt.grid(True)
plt.legend()
plt.savefig('battery_resistive_losses_vs_time.png')
plt.close()

# Salvar os dados calculados em arquivos separados
for hybrid_degree, df in dfs.items():
    output_cols = [
        'time', 'total_energy_consumption', 'power', 'emotor_efficiency',
        'total_thrust', 'altitude_m', 'global_efficiency',
        'specific_energy_consumption', 'co2_emissions_total',
        'eta_propeller', 'battery_resistive_losses'
    ]
    # Filtrar colunas existentes para evitar erros
    existing_cols = [col for col in output_cols if col in df.columns]
    df[existing_cols].to_csv(f'energy_analysis_results_{hybrid_degree.replace("%", "")}.csv', index=False)
