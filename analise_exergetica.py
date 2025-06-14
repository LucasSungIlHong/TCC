import pandas as pd
import numpy as np
import cantera as ct
import warnings
import math

# ANÁLISE EXERGÉTICA #

warnings.filterwarnings("ignore", category=UserWarning)

# Constantes
R_air_J_kgK = 287  # J/kg·K (Constante do gás para o ar)
gamma_air = 1.4 # Expoente isentrópico para o ar
b_fuel_kJ_kg = 45673  # kJ/kg (Exergia química específica do combustível Jet-A)
eficiencia_combustao = 0.98 # Eficiência da combustão
cp_air_J_kgK = 1005 # J/kg.K (Calor específico à pressão constante para o ar)

# Estado morto de referência (constantes)
T0_ref_K = 298.15  # K
P0_ref_Pa = 101325 # Pa

# Temperaturas de operação assumidas para componentes elétricos
T_battery_op_K = 313.15 # 40 C
T_inverter_op_K = 343.15 # 70 C

# Composição molar do ar seco (estado de referência) - Usada por Cantera
composicao_ar_seco_cantera = {
    'O2': 0.2095,
    'N2': 0.7809,
    'AR': 0.0093,
    'CO2': 0.0004,
}

# Massas molares (g/mol) - Usado na função de vazão de ar
massas_molares = {
    'O2': 32.00,
    'N2': 28.0134,
    'Ar': 39.948,
    'CO2': 44.01,
    'H2O': 18.015,
    'POSF10325': 170.34
}

# Composição do combustível para Cantera
fuel_comp_cantera = {"POSF10325": 1.0}

# Funções auxiliares (mantidas como no original, pois a vazão de ar está correta)
def massa_molar_ar():
    temp_comp = {'O2': 0.2095, 'N2': 0.7809, 'Ar': 0.0093, 'CO2': 0.0004}
    return sum(temp_comp[gas] * massas_molares[gas] for gas in temp_comp)

def fracao_massica_O2():
    M_ar = massa_molar_ar()
    temp_comp = {'O2': 0.2095, 'N2': 0.7809, 'Ar': 0.0093, 'CO2': 0.0004}
    return (temp_comp['O2'] * massas_molares['O2']) / M_ar

def calcular_vazao_ar(vazao_combustivel_kg_s, gas_turbine_far):
    mols_O2_por_mol_comb = 16.5
    M_comb = massas_molares['POSF10325'] / 1000
    M_O2 = massas_molares['O2'] / 1000
    frac_mass_O2_ar = fracao_massica_O2()
    AFR_esteq = (mols_O2_por_mol_comb * M_O2) / (M_comb * frac_mass_O2_ar)
    if gas_turbine_far == 0 or vazao_combustivel_kg_s == 0:
        return 0, AFR_esteq, 0, 0, 0
    AFR_real = 1 / gas_turbine_far
    phi = AFR_esteq / AFR_real
    AFR_real_adjusted = AFR_real / eficiencia_combustao
    excesso_ar = (AFR_real_adjusted / AFR_esteq) - 1
    vazao_ar = vazao_combustivel_kg_s * AFR_real_adjusted
    return vazao_ar, AFR_esteq, AFR_real_adjusted, excesso_ar, phi

def exergy_physical_specific_J_kg_latex(T_K, P_Pa, T0_K_ref, P0_Pa_ref, velocity_m_s=0):
    """Calcula a exergia física específica em J/kg usando a fórmula do LaTeX."""
    # A fórmula do LaTeX é: cp(T - T0) - T0(cp * ln(T/T0) - R * ln(P/P0))
    # Adicionando o termo de exergia cinética (velocity_m_s**2) / 2
    
    term_enthalpy = cp_air_J_kgK * (T_K - T0_K_ref)
    term_entropy = T0_K_ref * (cp_air_J_kgK * math.log(T_K / T0_K_ref) - R_air_J_kgK * math.log(P_Pa / P0_Pa_ref))
    
    e_fis_especifica_J_kg = term_enthalpy - term_entropy
    
    if velocity_m_s > 0:
        e_fis_especifica_J_kg += (velocity_m_s**2) / 2
        
    return e_fis_especifica_J_kg

def поток_exergy_physical_kW_latex(mdot_kg_s, T_K, P_Pa, T0_K_ref, P0_Pa_ref, velocity_m_s=0):
    """Calcula o fluxo de exergia física em kW usando a fórmula do LaTeX."""
    if mdot_kg_s == 0:
        return 0
    e_fis_especifica_J_kg = exergy_physical_specific_J_kg_latex(T_K, P_Pa, T0_K_ref, P0_Pa_ref, velocity_m_s)
    return mdot_kg_s * e_fis_especifica_J_kg / 1000

def поток_exergy_heat_kW(Q_heat_kW, T_source_K, T0_K_ref):
    """Calcula o fluxo de exergia associado ao calor em kW."""
    if T_source_K <= T0_K_ref or T_source_K == 0 or Q_heat_kW == 0:
        return 0
    factor_carnot = 1 - (T0_K_ref / T_source_K)
    return Q_heat_kW * factor_carnot

files = {
    '15%': 'resultados_suave_15.csv',
    '20%': 'resultados_suave_20.csv',
    '30%': 'resultados_suave_30.csv',
    'Convencional': 'resultados_suave_convencional.csv'
}

dfs_results_exergy = {}

for hybrid_degree, file_path in files.items():
    try:
        df_input = pd.read_csv(file_path, delimiter=";", decimal=",", skip_blank_lines=True)
        if df_input.empty:
            print(f"Aviso: Arquivo {file_path} está vazio. Pulando...")
            continue

        if 'battery_energy' in df_input.columns and 'time' in df_input.columns:
            df_input['delta_battery_energy_J'] = df_input['battery_energy'].diff()
            df_input['delta_time_s'] = df_input['time'].diff()

            # Tratar NaNs e zeros como valores ausentes
            df_input['delta_battery_energy_J'] = df_input['delta_battery_energy_J'].fillna(0)
            df_input['delta_time_s'] = df_input['delta_time_s'].fillna(0)
    
            # Substitui 0 por pd.NA e aplica forward fill
            df_input['delta_battery_energy_J'] = df_input['delta_battery_energy_J'].replace(0, pd.NA).ffill()
            df_input['delta_time_s'] = df_input['delta_time_s'].replace(0, pd.NA).ffill()

            # Se o primeiro valor ainda for nulo, define como 1.0
            df_input['delta_battery_energy_J'] = df_input['delta_battery_energy_J'].fillna(1.0)
            df_input['delta_time_s'] = df_input['delta_time_s'].fillna(1.0)
        else:
            print(f"AVISO: Colunas 'battery_energy' e/ou 'time' não encontradas em {file_path}. B_Quim_Bat será 0.")
            df_input['delta_battery_energy_J'] = 0
            df_input['delta_time_s'] = 1.0

        results_list_exergy = []

        for idx in range(len(df_input)):
            row = df_input.iloc[idx]

            T_ambient_K = row.get("temperature_C") # Coluna já em Kelvin
            P_ambient_Pa = row.get("pressure_Pa")
            velocity_m_s = row.get("velocity_m_s")
            mach_flight = row.get("mach_number")

            mdot_fuel_kg_s = row.get("mass_flow_kg_s", 0)
            gas_turbine_far_val = row.get("gas_turbine_far", 0)
            mdot_air_kg_s, AFR_esteq_val, AFR_real_adjusted_val, excesso_ar, phi_val = calcular_vazao_ar(mdot_fuel_kg_s, gas_turbine_far_val)

            # --- SISTEMA PROPULSIVO TÉRMICO ---

            # 1. MOTOR TÉRMICO

            # 1.1 Taxa de exergia do combustível
            
            B_Fuel_kW = mdot_fuel_kg_s * b_fuel_kJ_kg

            # 1.2 Taxa de exergia do ar

            T_estag_air = T_ambient_K * ( 1 + ((gamma_air - 1)/2)*mach_flight**2)
            p_estag_air = P_ambient_Pa * ( 1 + ((gamma_air - 1)/2)*mach_flight**2)**(gamma_air/(gamma_air - 1))
            
            B_Air_kW = abs(поток_exergy_physical_kW_latex(mdot_air_kg_s, T_estag_air, p_estag_air, T0_ref_K, P0_ref_Pa, velocity_m_s))

            # 1.3 Potência de eixo do motor térmico

            W_Mec_Engine_kW = row.get("power_turboshaft") / 1000

            # 1.4 Extrações úteis de potência (sist. hidráulico e elétrico)
            
            W_Mec_Hydraulic_kW = 14.914 # kW, dado fornecido pelo SUAVE
            W_Electric_kW_aux_engine = 14.914 # kW, dado fornecido pelo SUAVE
            W_Aux_Engine_kW = W_Mec_Hydraulic_kW + W_Electric_kW_aux_engine

            # 1.5 Extração de ar
            
            mdot_bleed_kg_s = 0.10394825 # kg/s, dado fornecido pelo SUAVE
            P_bleed_Pa = 172369.7 # Pa, dado fornecido pelo SUAVE
            
            # Cálculo de T_bleed_K conforme LaTeX
            T_estag_bleed_K = row.get("gas_turbine_t3") + 273.15 # Convertendo para Kelvin
            P_estag_bleed_Pa = row.get("gas_turbine_p3")
            
            if P_estag_bleed_Pa > 0 and T_estag_bleed_K > 0:
                T_bleed_K = T_estag_bleed_K * (P_bleed_Pa / P_estag_bleed_Pa)**((gamma_air - 1) / gamma_air)
            else:
                T_bleed_K = T_air_inlet_K # Fallback se os dados de estagnação não forem válidos

            B_Bleed_kW = поток_exergy_physical_kW_latex(mdot_bleed_kg_s, T_bleed_K, P_bleed_Pa, T0_ref_K, P0_ref_Pa, 0)

            # Balanço exergético - obtenção da parcela de destruição e perdas

            B_Perda_Dest_Engine_kW = (B_Fuel_kW + B_Air_kW) - (W_Mec_Engine_kW + B_Bleed_kW + W_Aux_Engine_kW)
            B_Perda_Dest_Engine_kW = max(0, B_Perda_Dest_Engine_kW)

            # 2. CAIXA DE TRANSMISSÃO (Gearbox)
            P_mec_MTRB_kW = 0
            eta_emotor_MTRB = 0.9
            combustion_engine_throttle = row.get("combustion_engine_throttle", 0)
            electric_throttle_MTRB = row.get("electric_throttle")

            if not (hybrid_degree == 'Convencional') and electric_throttle_MTRB == -1:
                P_mec_MTRB_kW = row.get("power_motor_turboprop") / 1000
                eta_emotor_MTRB = row.get("emotor_efficiency")

            # 2.1 Potência recebida na caixa de transmissão (depende da associação de motores)

            W_Entrada_CT_kW = 0
            if combustion_engine_throttle > 0 and electric_throttle_MTRB == 0: # Operação apenas do motor térmico
                W_Entrada_CT_kW = W_Mec_Engine_kW
            elif combustion_engine_throttle > 0 and electric_throttle_MTRB == -1: # Operação simultânea de motores térmico e elétrico
                # Se P_mec_MTRB_kW é positivo, MTRB é motor. Se negativo, MTRB é gerador.
                # Se MTRB é gerador, ele subtrai da entrada da CT (energia vai para o inversor).
                # Se MTRB é motor, ele soma à entrada da CT.
                W_Entrada_CT_kW = W_Mec_Engine_kW + P_mec_MTRB_kW
            elif combustion_engine_throttle == 0 and electric_throttle_MTRB == -1: # Operação apenas do motor elétrico
                W_Entrada_CT_kW = P_mec_MTRB_kW
            
            eta_gearbox = 0.98

            # 2.2 Potência útil resultante da caixa de transmissão
            
            W_Gearbox_out_kW = W_Entrada_CT_kW * eta_gearbox

            # Balanço exergético - obtenção da parcela de destruição e perdas

            B_Perda_Dest_Gearbox_kW = W_Entrada_CT_kW - W_Gearbox_out_kW
            B_Perda_Dest_Gearbox_kW = max(0, B_Perda_Dest_Gearbox_kW)

            # 3. HÉLICE (do sistema térmico)

            # 3.1 Potência recebida na hélice
            
            W_Prop_SysTermico_in_kW = W_Gearbox_out_kW
            thrust_turboprop_N = row.get("thrust_propeller")

            # 3.2 Taxa de exergia da tração da hélice
            
            B_Thrust_Engine_kW = (thrust_turboprop_N * velocity_m_s) / 1000

            # Balanço exergético - obtenção da parcela de destruição e perdas

            B_Perda_Dest_Prop_SysTermico_kW = W_Prop_SysTermico_in_kW - B_Thrust_Engine_kW
            B_Perda_Dest_Prop_SysTermico_kW = max(0, B_Perda_Dest_Prop_SysTermico_kW)

            # --- SISTEMA PROPULSIVO ELÉTRICO ---
            is_conventional = (hybrid_degree == 'Convencional')
            if not is_conventional:

                # 4. BATERIAS
            
                B_Quim_Bat_kW = 0
                W_Bat_Power_kW = 0
                B_Bat_Heat_kW = 0
                B_Dest_Bat_kW = 0

                #if not is_conventional:
                delta_bat_energy_J_val = row.get('delta_battery_energy_J')
                delta_time_s_val = row.get('delta_time_s')
                if delta_time_s_val == 0: delta_time_s_val = 1.0
                    
                # 4.1 Taxa de exergia química das baterias (depleção de carga armazenada)

                B_Quim_Bat_kW = -delta_bat_energy_J_val / (delta_time_s_val * 1000) if delta_time_s_val > 0 else 0

                # 4.2 Potência útil das baterias

                W_Bat_Power_kW = abs(row.get("battery_draw"))/1000

                # 4.3 Taxa de exergia relacionada às perdas por transferência de calor
                Q_Bat_Heat_kW = row.get("battery_resistive_losses")/1000
                B_Bat_Heat_kW = поток_exergy_heat_kW(Q_Bat_Heat_kW, T_battery_op_K, T0_ref_K)

                # Balanço exergético - obtenção da taxa de exergia destruída dentro do volume de controle

                B_Dest_Bat_kW = B_Quim_Bat_kW - W_Bat_Power_kW - B_Bat_Heat_kW
                B_Dest_Bat_kW = max(0, B_Dest_Bat_kW)

                # 5. INVERSOR DC/AC
                Ex_inverter_in_kW = 0
                Ex_inverter_out_kW = 0
                B_Inverter_Heat_kW = 0
                B_Dest_Inverter_kW = 0
                eta_ex_inverter = 0 

                # Inicializando variáveis WTP
                electric_throttle_WTP = row.get("electric_throttle_WTP")
                power_propeller_WTP_kW = row.get("power_propeller_WTP") / 1000
                eta_propeller_WTP = row.get("eta_propellerWTP") 
                eta_emotor_WTP = row.get("emotorWTP_efficiency") 
                P_mec_WTPmotor_kW = 0
                if electric_throttle_WTP > 0:
                    P_mec_WTPmotor_kW = power_propeller_WTP_kW / eta_propeller_WTP
                B_Thrust_Motor_WTP_kW = (row.get("thrust_WTP") * velocity_m_s) / 1000 # Exergia da tração WTP

                if not is_conventional:
                    # Electrical power to/from MTRB
                    W_El_MTRB_in_kW = 0
                    W_El_MTRB_out_kW = 0
                    if electric_throttle_MTRB == -1 and row.get("power_motor_turboprop") != 0:
                        if P_mec_MTRB_kW > 0: # MTRB é motor, consome energia elétrica
                            W_El_MTRB_in_kW = P_mec_MTRB_kW / eta_emotor_MTRB
                        else: # MTRB é gerador, produz energia elétrica
                            W_El_MTRB_out_kW = abs(P_mec_MTRB_kW) * eta_emotor_MTRB
                
                    # Electrical power to WTP (always motor)
                    W_El_WTP_in_kW = 0
                    if electric_throttle_WTP > 0 and power_propeller_WTP_kW > 0:
                        W_El_WTP_in_kW = (power_propeller_WTP_kW / eta_propeller_WTP) / eta_emotor_WTP

                    P_battery_draw_kW = row.get("battery_draw") / 1000 # Sinal mantido para evidenciar o funcionamento motor / gerador
                    total_electrical_output_to_motors_kW = W_El_MTRB_in_kW + W_El_WTP_in_kW

                    # Initialize inverter variables
                    Ex_inverter_in_kW = 0
                    Ex_inverter_out_kW = 0
                    Q_heat_inverter_kW = 0
                    B_Inverter_Heat_kW = 0
                    B_Dest_Inverter_kW = 0
                    eta_ex_inverter = 0

                    assumed_inverter_efficiency = 0.95 # Typical exergy efficiency for inverters/rectifiers

                    if P_battery_draw_kW > 0: # Battery discharging (Inverter: DC to AC)
                        Ex_inverter_in_kW = P_battery_draw_kW
                        Ex_inverter_out_kW = total_electrical_output_to_motors_kW
                    elif P_battery_draw_kW < 0: # Battery charging (Rectifier: AC to DC)
                        Ex_inverter_out_kW = abs(P_battery_draw_kW) # Power delivered to battery
                        Ex_inverter_in_kW = Ex_inverter_out_kW / assumed_inverter_efficiency # Assuming same efficiency for rectifier
                    else: # No net battery power flow (P_battery_draw_kW == 0)
                        if total_electrical_output_to_motors_kW > 0: # Motors are active, power comes from thermal engine directly
                            Ex_inverter_out_kW = total_electrical_output_to_motors_kW
                            Ex_inverter_in_kW = Ex_inverter_out_kW / assumed_inverter_efficiency
                        else: # Inverter is truly inactive
                            Ex_inverter_in_kW = 0
                            Ex_inverter_out_kW = 0

                    # Calculate power loss in inverter
                    Q_heat_inverter_kW = Ex_inverter_in_kW - Ex_inverter_out_kW
                
                    if Ex_inverter_in_kW > 0: # Only calculate if there\'s a valid input
                        if Q_heat_inverter_kW >= 0: # Normal operation: input >= output, positive or zero losses
                            B_Inverter_Heat_kW = поток_exergy_heat_kW(Q_heat_inverter_kW, T_inverter_op_K, T0_ref_K)
                            B_Dest_Inverter_kW = Q_heat_inverter_kW - B_Inverter_Heat_kW
                            B_Dest_Inverter_kW = max(0, B_Dest_Inverter_kW) # Ensure non-negative destruction
                            if Ex_inverter_in_kW > 0: # Avoid division by zero
                                eta_ex_inverter = Ex_inverter_out_kW / Ex_inverter_in_kW
                            else:
                                eta_ex_inverter = 0
                        else: # Inconsistent data: input < output, implies negative losses (should be handled by assumed_inverter_efficiency now)
                            # This block should ideally not be hit if assumed_inverter_efficiency is correctly applied.
                            # If it is, it means there\'s still an issue with the input data or power balance.
                            # For robustness, we can fall back to the assumed efficiency.
                            B_Inverter_Heat_kW = поток_exergy_heat_kW(abs(Q_heat_inverter_kW), T_inverter_op_K, T0_ref_K) # Use abs for heat
                            B_Dest_Inverter_kW = abs(Q_heat_inverter_kW) - B_Inverter_Heat_kW # Use abs for destruction calculation
                            B_Dest_Inverter_kW = max(0, B_Dest_Inverter_kW)
                            eta_ex_inverter = assumed_inverter_efficiency # Fallback to assumed efficiency
                    else: # Ex_inverter_in_kW is 0 (inverter inactive)
                        Q_heat_inverter_kW = 0
                        B_Inverter_Heat_kW = 0
                        B_Dest_Inverter_kW = 0
                        eta_ex_inverter = 0


                # 6. MOTOR ELÉTRICO MTRB
            
                B_Motor_MTRB_Heat_kW = 0
                B_Dest_Motor_MTRB_kW = 0
                P_loss_Motor_MTRB_kW = 0
            
                # A potência elétrica de entrada no MTRB (W_El_MTRB_in_kW) já foi calculada no bloco do inversor
                # Se P_mec_MTRB_kW > 0, MTRB é motor, então W_El_MTRB_in_kW é a entrada elétrica.
                # Se P_mec_MTRB_kW < 0, MTRB é gerador, então W_El_MTRB_out_kW é a saída elétrica.
            
                if not is_conventional and electric_throttle_MTRB == -1 and P_mec_MTRB_kW != 0:
                    if P_mec_MTRB_kW > 0: # MTRB é motor
                        P_loss_Motor_MTRB_kW = W_El_MTRB_in_kW - P_mec_MTRB_kW
                    else: # MTRB é gerador
                        P_loss_Motor_MTRB_kW = abs(P_mec_MTRB_kW) - abs(W_El_MTRB_out_kW) # Perda de energia no gerador

                    P_loss_Motor_MTRB_kW = max(0, P_loss_Motor_MTRB_kW)
                    T_motor_MTRB_op_K = row.get("T_motor_MTRB_op_K", (100+150)/2 + 273.15)
                    B_Motor_MTRB_Heat_kW = поток_exergy_heat_kW(P_loss_Motor_MTRB_kW, T_motor_MTRB_op_K, T0_ref_K)
                
                    # Balanço exergético para o MTRB
                    if P_mec_MTRB_kW > 0: # MTRB é motor
                        B_Dest_Motor_MTRB_kW = W_El_MTRB_in_kW - P_mec_MTRB_kW - B_Motor_MTRB_Heat_kW
                    else: # MTRB é gerador
                        B_Dest_Motor_MTRB_kW = abs(P_mec_MTRB_kW) - abs(W_El_MTRB_out_kW) - B_Motor_MTRB_Heat_kW
                    B_Dest_Motor_MTRB_kW = max(0, B_Dest_Motor_MTRB_kW)
            
                # 7. MOTOR ELÉTRICO WTP
            
                B_Motor_WTP_Heat_kW = 0
                B_Dest_Motor_WTP_kW = 0
                P_loss_Motor_WTP_kW = 0
            
                if not is_conventional and electric_throttle_WTP > 0 and P_mec_WTPmotor_kW > 0:
                    P_loss_Motor_WTP_kW = W_El_WTP_in_kW - P_mec_WTPmotor_kW
                    P_loss_Motor_WTP_kW = max(0, P_loss_Motor_WTP_kW)
                    T_motor_WTP_op_K = row.get("T_motor_WTP_op_K", (100+150)/2 + 273.15)
                    B_Motor_WTP_Heat_kW = поток_exergy_heat_kW(P_loss_Motor_WTP_kW, T_motor_WTP_op_K, T0_ref_K)
                    B_Dest_Motor_WTP_kW = W_El_WTP_in_kW - P_mec_WTPmotor_kW - B_Motor_WTP_Heat_kW
                    B_Dest_Motor_WTP_kW = max(0, B_Dest_Motor_WTP_kW)

                # 8. HÉLICE WTP
            
                B_Prop_Air_WTP_kW = 0
                B_Dest_Prop_WTP_kW = 0
                B_Perda_Dest_WTP_kW = 0 # Inicializa para garantir que sempre tenha um valor
            
                if not is_conventional and electric_throttle_WTP > 0 and P_mec_WTPmotor_kW > 0:
                    # Conforme LaTeX, B_Perda/Dest_WTP é a diferença entre a potência mecânica de entrada e a exergia de tração
                    B_Perda_Dest_WTP_kW = P_mec_WTPmotor_kW - B_Thrust_Motor_WTP_kW
                    B_Perda_Dest_WTP_kW = max(0, B_Perda_Dest_WTP_kW)
                    # Os termos B_Prop_Air_WTP_kW e B_Dest_Prop_WTP_kW não são explicitamente separados no LaTeX para o balanço final
                    # Portanto, B_Perda_Dest_WTP_kW representa a soma de B_Dest_WTP e B_WTP_Air.
                    # Para simplificar e seguir o balanço principal do LaTeX:
                    B_Dest_Prop_WTP_kW = B_Perda_Dest_WTP_kW # Representa a soma de B_Dest_WTP e B_WTP_Air
                    B_Prop_Air_WTP_kW = 0 # Não é calculado separadamente no balanço principal
                else:
                    B_Perda_Dest_WTP_kW = 0
                    B_Dest_Prop_WTP_kW = 0
                    B_Prop_Air_WTP_kW = 0

                B_Thrust_Total_kW = B_Thrust_Engine_kW + B_Thrust_Motor_WTP_kW

            # Eficiências exergéticas
            
            # Eficiência exergética do motor térmico

            if not is_conventional:
                eta_ex_prop_SysTermico = B_Thrust_Engine_kW / W_Prop_SysTermico_in_kW if W_Prop_SysTermico_in_kW > 0 else 0
                eta_ex_bat = W_Bat_Power_kW / B_Quim_Bat_kW if B_Quim_Bat_kW > 0 else 0
                # eta_ex_inverter já calculado no bloco do inversor
            
                # Eficiência exergética do motor MTRB
                if P_mec_MTRB_kW > 0: # MTRB é motor
                    eta_ex_motor_MTRB = P_mec_MTRB_kW / W_El_MTRB_in_kW if W_El_MTRB_in_kW > 0 else 0
                else: # MTRB é gerador
                    eta_ex_motor_MTRB = abs(W_El_MTRB_out_kW) / abs(P_mec_MTRB_kW) if P_mec_MTRB_kW != 0 else 0

                eta_ex_motor_WTP = P_mec_WTPmotor_kW / W_El_WTP_in_kW if W_El_WTP_in_kW > 0 else 0
                eta_ex_prop_WTP = B_Thrust_Motor_WTP_kW / P_mec_WTPmotor_kW if P_mec_WTPmotor_kW > 0 else 0

                # Eficiência exergética total do sistema
                # A eficiência exergética total é a exergia útil (tração total) dividida pela exergia de entrada (combustível + química da bateria)
                # Se o sistema for convencional, a entrada da bateria é zero.
                eta_ex_engine = (W_Mec_Engine_kW + W_Mec_Hydraulic_kW + W_Electric_kW_aux_engine + B_Bleed_kW) / (B_Fuel_kW + B_Air_kW) if (B_Fuel_kW + B_Air_kW) > 0 else 0
            
                eta_ex_gearbox = W_Gearbox_out_kW / W_Entrada_CT_kW if W_Entrada_CT_kW > 0 else 0
                
                total_exergy_input_kW = B_Fuel_kW + B_Air_kW + B_Quim_Bat_kW 
                B_Thrust_Total_kW = B_Thrust_Engine_kW + B_Thrust_Motor_WTP_kW 
                eta_ex_total = (B_Thrust_Total_kW + W_Mec_Hydraulic_kW + W_Electric_kW_aux_engine + B_Bleed_kW) / total_exergy_input_kW if total_exergy_input_kW > 0 else 0
            else:
                eta_ex_engine = (W_Mec_Engine_kW + W_Mec_Hydraulic_kW + W_Electric_kW_aux_engine + B_Bleed_kW) / (B_Fuel_kW + B_Air_kW) if (B_Fuel_kW + B_Air_kW) > 0 else 0
            
                eta_ex_gearbox = W_Gearbox_out_kW / W_Entrada_CT_kW if W_Entrada_CT_kW > 0 else 0
                
                total_exergy_input_kW = B_Fuel_kW + B_Air_kW
                B_Thrust_Total_kW = B_Thrust_Engine_kW
                eta_ex_total = (B_Thrust_Total_kW + W_Mec_Hydraulic_kW + W_Electric_kW_aux_engine + B_Bleed_kW) / total_exergy_input_kW if total_exergy_input_kW > 0 else 0

            results_row = {
                'segment': row.get('segment'),
                'time': row.get('time'),
                'altitude_m': row.get('altitude_m'),
                'mach_number': row.get('mach_number'),
                'velocity_m_s': row.get('velocity_m_s'),
                'pressure_Pa': row.get('pressure_Pa'),
                'temperature_C': row.get('temperature_C'),
                'mdot_fuel_kg_s': mdot_fuel_kg_s,
                'mdot_air_kg_s': mdot_air_kg_s,
                'AFR_esteq': AFR_esteq_val,
                'AFR_real_adjusted': AFR_real_adjusted_val,
                'excesso_ar': excesso_ar,
                'phi': phi_val,
                'B_Fuel_kW': B_Fuel_kW,
                'B_Air_kW': B_Air_kW,
                'W_Mec_Engine_kW': W_Mec_Engine_kW,
                'W_Mec_Hydraulic_kW': W_Mec_Hydraulic_kW,
                'W_Electric_kW_aux_engine': W_Electric_kW_aux_engine,
                'W_Aux_Engine_kW': W_Aux_Engine_kW,
                'mdot_bleed_kg_s': mdot_bleed_kg_s,
                'P_bleed_Pa': P_bleed_Pa,
                'T_estag_bleed_K': T_estag_bleed_K,
                'P_estag_bleed_Pa': P_estag_bleed_Pa,
                'T_bleed_K': T_bleed_K,
                'B_Bleed_kW': B_Bleed_kW,
                'B_Perda_Dest_Engine_kW': B_Perda_Dest_Engine_kW,
                'P_mec_MTRB_kW': P_mec_MTRB_kW,
                'eta_emotor_MTRB': eta_emotor_MTRB,
                'W_Entrada_CT_kW': W_Entrada_CT_kW,
                'W_Gearbox_out_kW': W_Gearbox_out_kW,
                'B_Perda_Dest_Gearbox_kW': B_Perda_Dest_Gearbox_kW,
                'W_Prop_SysTermico_in_kW': W_Prop_SysTermico_in_kW,
                'thrust_turboprop_N': thrust_turboprop_N,
                'B_Thrust_Engine_kW': B_Thrust_Engine_kW,
                'B_Perda_Dest_Prop_SysTermico_kW': B_Perda_Dest_Prop_SysTermico_kW,
                'B_Quim_Bat_kW': B_Quim_Bat_kW,
                'W_Bat_Power_kW': W_Bat_Power_kW,
                'Q_Bat_Heat_kW': Q_Bat_Heat_kW,
                'B_Bat_Heat_kW': B_Bat_Heat_kW,
                'B_Dest_Bat_kW': B_Dest_Bat_kW,
                'Ex_inverter_in_kW': Ex_inverter_in_kW,
                'Ex_inverter_out_kW': Ex_inverter_out_kW,
                'Q_heat_inverter_kW': Q_heat_inverter_kW,
                'B_Inverter_Heat_kW': B_Inverter_Heat_kW,
                'B_Dest_Inverter_kW': B_Dest_Inverter_kW,
                'eta_ex_inverter': eta_ex_inverter,
                'W_El_MTRB_in_kW': W_El_MTRB_in_kW,
                'W_El_MTRB_out_kW': W_El_MTRB_out_kW,
                'P_loss_Motor_MTRB_kW': P_loss_Motor_MTRB_kW,
                'B_Motor_MTRB_Heat_kW': B_Motor_MTRB_Heat_kW,
                'B_Dest_Motor_MTRB_kW': B_Dest_Motor_MTRB_kW,
                'W_El_WTP_in_kW': W_El_WTP_in_kW,
                'P_mec_WTPmotor_kW': P_mec_WTPmotor_kW,
                'P_loss_Motor_WTP_kW': P_loss_Motor_WTP_kW,
                'B_Motor_WTP_Heat_kW': B_Motor_WTP_Heat_kW,
                'B_Dest_Motor_WTP_kW': B_Dest_Motor_WTP_kW,
                'B_Thrust_Motor_WTP_kW': B_Thrust_Motor_WTP_kW,
                'B_Perda_Dest_WTP_kW': B_Perda_Dest_WTP_kW, # Agora representa a soma de B_Dest_WTP e B_WTP_Air
                'B_Thrust_Total_kW': B_Thrust_Total_kW,
                'eta_ex_engine': eta_ex_engine,
                'eta_ex_gearbox': eta_ex_gearbox,
                'eta_ex_prop_SysTermico': eta_ex_prop_SysTermico,
                'eta_ex_bat': eta_ex_bat,
                'eta_ex_motor_MTRB': eta_ex_motor_MTRB,
                'eta_ex_motor_WTP': eta_ex_motor_WTP,
                'eta_ex_prop_WTP': eta_ex_prop_WTP,
                'eta_ex_total': eta_ex_total
            }
            results_list_exergy.append(results_row)

        df_results_exergy = pd.DataFrame(results_list_exergy)
        dfs_results_exergy[hybrid_degree] = df_results_exergy

        output_filename = f"resultados_exergia_{hybrid_degree.replace('%', '')}.csv"
        df_results_exergy.to_csv(output_filename, sep=";", decimal=",", index=False)
        print(f"Resultados de exergia para {hybrid_degree} salvos em {output_filename}")

    except Exception as e:
        print(f"Erro ao processar {file_path}: {e}")

print("Análise exergética concluída.")


