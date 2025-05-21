import pandas as pd
import numpy as np
import cantera as ct
import warnings
import math
import matplotlib.pyplot as plt

# Ignorar warnings do Cantera
warnings.filterwarnings("ignore", category=UserWarning)

# Constantes
R = 0.287  # kJ/kg·K (Constante do gás para o ar)
gamma = 1.4 # Expoente isentrópico para o ar
b_fuel = 45673  # kJ/kg (Exergia química específica do combustível Jet-A)
R_universal = 8.314  # J/(mol·K) (Constante universal dos gases)
g = 9.80665  # m/s² (Aceleração da gravidade)
eficiencia_combustao = 0.98 # Eficiência da combustão

# Composição molar do ar seco (estado de referência)
composicao_ar_seco = {
    'O2': 0.2095,
    'N2': 0.7809,
    'Ar': 0.0093,
    'CO2': 0.0004,
    'H2O': 0.0  # Assumido seco para o estado de referência
}

# Massas molares (g/mol)
massas_molares = {
    'O2': 32.00,
    'N2': 28.0134,
    'Ar': 39.948,
    'CO2': 44.01,
    'H2O': 18.015,
    'POSF10325': 170.34  # Massa molar aproximada para Jet-A (C12H23)
}

# Exergia química padrão (kJ/mol) a 298.15 K, 1 atm
exergia_padrao = {
    'O2': 3.97,
    'N2': 0.72,
    'Ar': 11.69,
    'CO2': 19.87,  # Vapor d'água
    'POSF10325': 7785.0
}

# Funções auxiliares
def massa_molar_ar():
    return sum(composicao_ar_seco[g] * massas_molares[g] for g in composicao_ar_seco)

def fracao_massica_O2():
    M_ar = massa_molar_ar()
    return (composicao_ar_seco['O2'] * massas_molares['O2']) / M_ar

def calcular_vazao_ar(vazao_combustivel_kg_s, gas_turbine_far):
    mols_O2_por_mol_comb = 17.75
    M_comb = massas_molares['POSF10325'] / 1000
    M_O2 = massas_molares['O2'] / 1000
    frac_mass_O2_ar = fracao_massica_O2()
    AFR_esteq = (mols_O2_por_mol_comb * M_O2) / (M_comb * frac_mass_O2_ar)
    if gas_turbine_far == 0:
        return 0, AFR_esteq, 0, 0, 0
    AFR_real = 1 / gas_turbine_far
    phi = AFR_esteq / AFR_real
    AFR_real_adjusted = AFR_real / eficiencia_combustao
    excesso_ar = (AFR_real_adjusted / AFR_esteq) - 1
    vazao_ar = vazao_combustivel_kg_s * AFR_real_adjusted
    return vazao_ar, AFR_esteq, AFR_real_adjusted, excesso_ar, phi

def exergy_physical(mdot, T, T0, p, p0, v=0):
    if mdot == 0: return 0
    gas = ct.Solution("A2highT.cti")
    gas.TPX = T, p, composicao_ar_seco
    h = gas.enthalpy_mass
    s = gas.entropy_mass
    gas.TPX = T0, p0, composicao_ar_seco
    h0 = gas.enthalpy_mass
    s0 = gas.entropy_mass
    e_fis_especifica = (h - h0) - T0 * (s - s0) + (v**2) / 2
    return mdot * e_fis_especifica / 1000

def exergy_heat(Q_heat_kW, T_source_K, T0_K):
    if T_source_K <= T0_K or T_source_K == 0:
        return 0
    factor = 1 - (T0_K / T_source_K)
    return Q_heat_kW * factor

# Lista de arquivos e graus de hibridização
files = {
    '15%': 'resultados_suave_15.csv',
    '20%': 'resultados_suave_20.csv',
    '30%': 'resultados_suave_30.csv',
    'Convencional': 'resultados_suave_convencional.csv'
}

# Dicionário para armazenar os DataFrames de resultados
dfs_results = {}

# Composição do combustível
fuel_comp_cantera = {"POSF10325": 1.0}

# Processar cada planilha
for hybrid_degree, file_path in files.items():
    try:
        # Leitura do arquivo de dados de entrada
        df_suave = pd.read_csv(file_path, delimiter=";", decimal=",", skip_blank_lines=True)
        if df_suave.empty:
            print(f"Aviso: Arquivo {file_path} está vazio. Pulando...")
            continue

        results_list = []

        for idx in range(len(df_suave)):
            row_suave = df_suave.iloc[idx]

            # Condições ambientais (estado morto)
            T0_env = row_suave.get("temperature_C", 25) + 273.15
            p0_env = row_suave.get("pressure_Pa", 101325)
            velocity = row_suave.get("velocity_m_s", 0)
            M_flight = row_suave.get("mach_number", 0)

            # Dados do Motor Térmico
            mdot_fuel = row_suave.get("mass_flow_kg_s", 0)
            power_mech_engine = row_suave.get("power", 0) / 1000  # Convertendo W para kW
            gas_turbine_far = row_suave.get("gas_turbine_far", 0)

            # Dados Elétricos e Bateria (zero para convencional)
            is_conventional = (hybrid_degree == 'Convencional')
            W_Electric_Motor_in = abs(row_suave.get("power_motor_turboprop", 0)) / 1000 if not is_conventional else 0
            eta_motor_el = row_suave.get("emotor_efficiency", 0.95) if not is_conventional and row_suave.get("emotor_efficiency", 0) < 1 else 0.95
            W_Bat_Power_out = abs(row_suave.get("battery_draw", 0)) / 1000 if not is_conventional else 0
            I_bat = abs(row_suave.get("battery_current", 0)) if not is_conventional else 0
            Voc_bat = row_suave.get("battery_voltage_open_circuit", 0) if not is_conventional else 0
            Vload_bat = row_suave.get("battery_voltage_under_load", 0) if not is_conventional else 0
            T_bat_op = (25 + 30) / 2 + 273.15

            # Dados para Hélice
            thrust_total_N = max(row_suave.get("propeller_thrust", 0) + (row_suave.get("thrust_WTP", 0) if not is_conventional else 0), 0)
            eta_propeller = row_suave.get("etap", 0.8) if row_suave.get("etap", 0) > 0 else 0.8

            # --- CÁLCULO VAZÃO DE AR ---
            mdot_air, AFR_esteq, AFR_real, excesso_ar, phi = calcular_vazao_ar(mdot_fuel, gas_turbine_far)

            # --- MOTOR TÉRMICO ---
            B_Fuel = mdot_fuel * b_fuel
            T_in_engine = T0_env * (1 + (gamma - 1) / 2 * M_flight**2)
            p_in_engine = p0_env * (1 + (gamma - 1) / 2 * M_flight**2)**(gamma / (gamma - 1))
            B_Eng_Air = exergy_physical(mdot_air, T_in_engine, T0_env, p_in_engine, p0_env, velocity)
            W_Mec_Engine_out = power_mech_engine
            W_Mec_Hydraulic_Electric_MT = 2 * 14.914
            mdot_bleed_MT = 2 * 0.00623125
            mdot_exhaust_MT = mdot_air + mdot_fuel - mdot_bleed_MT
            B_Eng_Gases = 0
            if mdot_exhaust_MT > 0 and phi > 0:
                gas_comb = ct.Solution("A2highT.cti")
                gas_comb.TP = T_in_engine, p_in_engine
                gas_comb.set_equivalence_ratio(phi, fuel_comp_cantera, composicao_ar_seco)
                gas_comb.equilibrate("HP")
                T_ex_MT = gas_comb.T
                p_ex_MT = gas_comb.P
                B_Eng_Gases = exergy_physical(mdot_exhaust_MT, T_ex_MT, T0_env, p_ex_MT, p0_env, 0)
            p_bleed_MT = 172369.7
            B_Bleed_MT = exergy_physical(mdot_bleed_MT, T_in_engine, T0_env, p_bleed_MT, p0_env, 0)
            B_Dest_Engine = (B_Fuel + B_Eng_Air) - (W_Mec_Engine_out + W_Mec_Hydraulic_Electric_MT + B_Eng_Gases + B_Bleed_MT)
            B_Dest_Engine = max(0, B_Dest_Engine)

            # --- BATERIAS ---
            P_dissipada_Bat_W = I_bat * (Voc_bat - Vload_bat) if Voc_bat > Vload_bat else 0
            P_dissipada_Bat_kW = max(0, P_dissipada_Bat_W / 1000)
            B_Bat_Heat = 0
            B_Dest_Bat = 0
            if T_bat_op > T0_env:
                B_Bat_Heat = exergy_heat(P_dissipada_Bat_kW, T_bat_op, T0_env)
                B_Dest_Bat = P_dissipada_Bat_kW - B_Bat_Heat
            else:
                B_Bat_Heat = 0
                B_Dest_Bat = P_dissipada_Bat_kW
            B_Dest_Bat = max(0, B_Dest_Bat)

            # --- INVERSORES DC/AC ---
            T_inverter_op = (70 + 90) / 2 + 273.15
            P_loss_Inv_kW = W_Bat_Power_out - W_Electric_Motor_in
            P_loss_Inv_kW = max(0, P_loss_Inv_kW)
            B_Inverter_Heat = 0
            B_Dest_Inverter = 0
            if T_inverter_op > T0_env:
                B_Inverter_Heat = exergy_heat(P_loss_Inv_kW, T_inverter_op, T0_env)
                B_Dest_Inverter = P_loss_Inv_kW - B_Inverter_Heat
            else:
                B_Inverter_Heat = 0
                B_Dest_Inverter = P_loss_Inv_kW
            B_Dest_Inverter = max(0, B_Dest_Inverter)

            # --- MOTOR ELÉTRICO ---
            W_Mec_Motor_out = eta_motor_el * W_Electric_Motor_in
            Q_loss_motor_energy_kW = (1 - eta_motor_el) * W_Electric_Motor_in
            Q_loss_motor_energy_kW = max(0, Q_loss_motor_energy_kW)
            T_motor_op = (100 + 150) / 2 + 273.15
            B_Motor_Heat = 0
            B_Dest_Motor = 0
            if T_motor_op > T0_env:
                B_Motor_Heat = exergy_heat(Q_loss_motor_energy_kW, T_motor_op, T0_env)
                B_Dest_Motor = Q_loss_motor_energy_kW - B_Motor_Heat
            else:
                B_Motor_Heat = 0
                B_Dest_Motor = Q_loss_motor_energy_kW
            B_Dest_Motor = max(0, B_Dest_Motor)

            # --- HÉLICE ---
            W_Mec_Total_To_Prop = W_Mec_Engine_out + W_Mec_Motor_out
            B_Thrust = thrust_total_N * velocity / 1000
            B_Thrust = max(0, B_Thrust)
            B_Dest_Prop = 0
            B_Prop_Air = 0
            if W_Mec_Total_To_Prop > 0 and eta_propeller > 0:
                B_Dest_Prop = W_Mec_Total_To_Prop * (1 - eta_propeller)
                B_Prop_Air = W_Mec_Total_To_Prop - B_Thrust - B_Dest_Prop
                B_Prop_Air = max(0, B_Prop_Air)
                B_Dest_Prop = max(0, B_Dest_Prop)
            elif W_Mec_Total_To_Prop > 0:
                B_Dest_Prop = W_Mec_Total_To_Prop - B_Thrust
                B_Prop_Air = 0
                B_Dest_Prop = max(0, B_Dest_Prop)
            else:
                B_Dest_Prop = 0
                B_Prop_Air = 0

            # --- EFICIÊNCIAS EXERGÉTICAS CORRIGIDAS ---
            eta_ex_engine = 0
            if (B_Fuel + B_Eng_Air) > 0:
                eta_ex_engine = (W_Mec_Engine_out + W_Mec_Hydraulic_Electric_MT) / (B_Fuel + B_Eng_Air)
            
            eta_ex_bat = 0
            exergia_entrada_bateria = W_Bat_Power_out + P_dissipada_Bat_kW
            if exergia_entrada_bateria > 0:
                eta_ex_bat = W_Bat_Power_out / exergia_entrada_bateria

            eta_ex_inverter = 0
            if W_Bat_Power_out > 0:
                eta_ex_inverter = (W_Electric_Motor_in / W_Bat_Power_out) - 0.06
            
            eta_ex_motor = 0
            if W_Electric_Motor_in > 0:
                eta_ex_motor = W_Mec_Motor_out / W_Electric_Motor_in
            
            eta_ex_prop = 0
            if W_Mec_Total_To_Prop > 0:
                eta_ex_prop = B_Thrust / W_Mec_Total_To_Prop
            
            # --- EFICIÊNCIA EXERGÉTICA GLOBAL ---
            eta_ex_global = 0
            # Cálculo da entrada exergética do sistema elétrico
            B_Electric_Input = 0
            if W_Bat_Power_out > 0 and eta_ex_bat > 0:
                B_Electric_Input = W_Bat_Power_out / eta_ex_bat
            
            # Cálculo da eficiência exergética global
            total_exergy_input = B_Fuel + B_Eng_Air + B_Electric_Input
            if total_exergy_input > 0:
                eta_ex_global = B_Thrust / total_exergy_input
                
            eta_ex_engine = max(0, min(1, eta_ex_engine))
            eta_ex_bat = max(0, min(1, eta_ex_bat))
            eta_ex_inverter = max(0, min(1, eta_ex_inverter))
            eta_ex_motor = max(0, min(1, eta_ex_motor))
            eta_ex_prop = max(0, min(1, eta_ex_prop))
            eta_ex_global = max(0, min(1, eta_ex_global))

            results = {
                "mission_phase": row_suave.get("segment", "N/A"),
                "B_Fuel_kW": B_Fuel,
                "B_Eng_Air_kW": B_Eng_Air,
                "B_Electric_Input_kW": B_Electric_Input,
                "W_Bat_Power_out_kW": W_Bat_Power_out,
                "W_Electric_Motor_in_kW": W_Electric_Motor_in,
                "W_Mec_Engine_out_kW": W_Mec_Engine_out,
                "W_Mec_Hydraulic_Electric_MT_kW": W_Mec_Hydraulic_Electric_MT,
                "W_Mec_Motor_out_kW": W_Mec_Motor_out,
                "B_Thrust_kW": B_Thrust,
                "B_Eng_Gases_kW": B_Eng_Gases,
                "B_Bleed_MT_kW": B_Bleed_MT,
                "B_Bat_Heat_kW": B_Bat_Heat,
                "B_Inverter_Heat_kW": B_Inverter_Heat,
                "B_Motor_Heat_kW": B_Motor_Heat,
                "B_Prop_Air_kW": B_Prop_Air,
                "B_Dest_Engine_kW": B_Dest_Engine,
                "B_Dest_Bat_kW": B_Dest_Bat,
                "B_Dest_Inverter_kW": B_Dest_Inverter,
                "B_Dest_Motor_kW": B_Dest_Motor,
                "B_Dest_Prop_kW": B_Dest_Prop,
                "P_dissipada_Bat_kW": P_dissipada_Bat_kW,
                "P_loss_Inv_kW": P_loss_Inv_kW,
                "T0_env_K": T0_env,
                "I_bat_A": I_bat,
                "Voc_bat_V": Voc_bat,
                "Vload_bat_V": Vload_bat,
                "eta_ex_engine": eta_ex_engine,
                "eta_ex_bat": eta_ex_bat,
                "eta_ex_inverter": eta_ex_inverter,
                "eta_ex_motor": eta_ex_motor,
                "eta_ex_prop": eta_ex_prop,
                "eta_ex_global": eta_ex_global
            }
            results_list.append(results)

        df_results = pd.DataFrame(results_list)
        output_filename = f"resultados_exergia_final_v4_{hybrid_degree.replace('%', '')}.csv"
        df_results.to_csv(output_filename, sep=",", index=False, float_format="%.6f")
        dfs_results[hybrid_degree] = df_results
    except Exception as e:
        print(f"Erro ao processar {file_path}: {e}")
        continue

# Gerar gráficos com até quatro curvas
colors = {'15%': 'blue', '20%': 'red', '30%': 'green', 'Convencional': 'black'}

# Plot 1: Eficiência Exergética do Motor Térmico vs Tempo
plt.figure(figsize=(10, 7))
for hybrid_degree, df in dfs_results.items():
    plt.plot(df.index, df['eta_ex_engine'], color=colors[hybrid_degree], label=f'Motor Térmico - {hybrid_degree}')
plt.title('Eficiência Exergética do Motor Térmico')
plt.xlabel('Índice do Tempo')
plt.ylabel('Eficiência Exergética')
plt.grid(True)
plt.legend()
plt.savefig('eta_ex_engine_vs_time_v4.png')
plt.close()

# Plot 2: Eficiência Exergética das Baterias vs Tempo (apenas híbridos)
plt.figure(figsize=(10, 7))
for hybrid_degree, df in dfs_results.items():
    if hybrid_degree != 'Convencional':
        plt.plot(df.index, df['eta_ex_bat'], color=colors[hybrid_degree], label=f'Baterias - {hybrid_degree}')
plt.title('Eficiência Exergética das Baterias')
plt.xlabel('Índice do Tempo')
plt.ylabel('Eficiência Exergética')
plt.grid(True)
plt.legend()
plt.savefig('eta_ex_bat_vs_time_v4.png')
plt.close()

# Plot 3: Eficiência Exergética dos Inversores vs Tempo (apenas híbridos)
plt.figure(figsize=(10, 7))
for hybrid_degree, df in dfs_results.items():
    if hybrid_degree != 'Convencional':
        plt.plot(df.index, df['eta_ex_inverter'], color=colors[hybrid_degree], label=f'Inversores - {hybrid_degree}')
plt.title('Eficiência Exergética dos Inversores')
plt.xlabel('Índice do Tempo')
plt.ylabel('Eficiência Exergética')
plt.grid(True)
plt.legend()
plt.savefig('eta_ex_inverter_vs_time_v4.png')
plt.close()

# Plot 4: Eficiência Exergética do Motor Elétrico vs Tempo (apenas híbridos)
plt.figure(figsize=(10, 7))
for hybrid_degree, df in dfs_results.items():
    if hybrid_degree != 'Convencional':
        plt.plot(df.index, df['eta_ex_motor'], color=colors[hybrid_degree], label=f'Motor Elétrico - {hybrid_degree}')
plt.title('Eficiência Exergética do Motor Elétrico')
plt.xlabel('Índice do Tempo')
plt.ylabel('Eficiência Exergética')
plt.grid(True)
plt.legend()
plt.savefig('eta_ex_motor_vs_time_v4.png')
plt.close()

# Plot 5: Eficiência Exergética da Hélice vs Tempo
plt.figure(figsize=(10, 7))
for hybrid_degree, df in dfs_results.items():
    plt.plot(df.index, df['eta_ex_prop'], color=colors[hybrid_degree], label=f'Hélice - {hybrid_degree}')
plt.title('Eficiência Exergética da Hélice')
plt.xlabel('Índice do Tempo')
plt.ylabel('Eficiência Exergética')
plt.grid(True)
plt.legend()
plt.savefig('eta_ex_prop_vs_time_v4.png')
plt.close()

# Plot 6: Eficiência Exergética Global vs Tempo
plt.figure(figsize=(10, 7))
for hybrid_degree, df in dfs_results.items():
    plt.plot(df.index, df['eta_ex_global'], color=colors[hybrid_degree], label=f'Global - {hybrid_degree}')
plt.title('Eficiência Exergética Global do Sistema')
plt.xlabel('Índice do Tempo')
plt.ylabel('Eficiência Exergética')
plt.grid(True)
plt.legend()
plt.savefig('eta_ex_global_vs_time_v4.png')
plt.close()

print("Análise exergética (v4) concluída. Resultados salvos e gráficos gerados.")
