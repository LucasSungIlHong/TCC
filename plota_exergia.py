import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# --- SCRIPT DE PLOTAGEM DOS RESULTADOS DE EXERGIA ---

# Dicionario com os arquivos de entrada e os nomes das configuracoes
files_to_plot = {
    '15%': 'resultados_exergia_15.csv',
    '20%': 'resultados_exergia_20.csv',
    '30%': 'resultados_exergia_30.csv',
    'Convencional': 'resultados_exergia_Convencional.csv'
}

# Dicionario para armazenar os DataFrames lidos
dfs = {}

# Carregar cada planilha de resultados
print("Carregando arquivos de resultados...")
for hybrid_degree, file_path in files_to_plot.items():
    try:
        df = pd.read_csv(file_path, delimiter=';', decimal=',')
        dfs[hybrid_degree] = df
        print(f"Arquivo '{file_path}' carregado com sucesso.")
    except FileNotFoundError:
        print(f"AVISO: O arquivo '{file_path}' nao foi encontrado. Esta configuracao sera ignorada.")
    except Exception as e:
        print(f"ERRO: Nao foi possivel ler o arquivo '{file_path}'. Erro: {e}")

if not dfs:
    print("\nNenhum arquivo de dados foi carregado. Encerrando o script.")
    exit()

# --- CONFIGURACOES DE PLOTAGEM ---

colors = {'15%': 'blue', '20%': 'red', '30%': 'green', 'Convencional': 'black'}

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
        ncol = min(num_items, 3)
        if ncol == 0: ncol = 1
            
    ax.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, -0.22), 
              ncol=ncol, fancybox=True, shadow=False, borderaxespad=0., fontsize=fontsize)

figure_width = 10
figure_height = 10
tight_layout_rect = [0.12, 0.20, 0.95, 0.93]

# --- GERACAO DOS GRAFICOS (UM POR UM) ---
print("\nIniciando a geracao dos graficos um por um...")

# --- Gráficos Padrão (0-100%) ---

# Gráfico 1: Eficiencia Exergetica Total do Sistema
plt.figure(figsize=(figure_width, figure_height))
ax = plt.gca()
eta_col = 'eta_ex_total'
title_text = 'Eficiência Exergética Global do Sistema Propulsivo'
print(f"Gerando grafico: {title_text}")
for hybrid_degree, df in dfs.items():
    if eta_col in df.columns and 'time' in df.columns:
        ax.plot(df['time'] / 60, df[eta_col] * 100, color=colors[hybrid_degree], label=f'Eficiência Global - {hybrid_degree}')
ax.set_title(f'{title_text}', fontsize=axis_label_fontsize+2)
ax.set_xlabel('Tempo (min)', fontsize=axis_label_fontsize)
ax.set_ylabel('Eficiência Exergética (%)', fontsize=axis_label_fontsize)
ax.tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
ax.grid(True)
ax.set_ylim(0, 100)
place_legend_below(ax)
plt.tight_layout(rect=tight_layout_rect)
plt.savefig(f"{eta_col}_vs_time.png")
plt.close()
print(f"Grafico salvo como: {eta_col}_vs_time.png")

# Gráfico 2: Eficiencia Exergetica do Motor Termico
plt.figure(figsize=(figure_width, figure_height))
ax = plt.gca()
eta_col = 'eta_ex_engine'
title_text = 'Eficiência Exergética do Motor Térmico'
print(f"Gerando grafico: {title_text}")
for hybrid_degree, df in dfs.items():
    if eta_col in df.columns and 'time' in df.columns:
        ax.plot(df['time'] / 60, df[eta_col] * 100, color=colors[hybrid_degree], label=f'Efic. Mot. Térm. - {hybrid_degree}')
ax.set_title(f'{title_text}', fontsize=axis_label_fontsize+2)
ax.set_xlabel('Tempo (min)', fontsize=axis_label_fontsize)
ax.set_ylabel('Eficiência Exergética (%)', fontsize=axis_label_fontsize)
ax.tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
ax.grid(True)
ax.set_ylim(0, 100)
place_legend_below(ax)
plt.tight_layout(rect=tight_layout_rect)
plt.savefig(f"{eta_col}_vs_time.png")
plt.close()
print(f"Grafico salvo como: {eta_col}_vs_time.png")

# Gráfico 3: Eficiencia Exergetica da Caixa de Transmissao
plt.figure(figsize=(figure_width, figure_height))
ax = plt.gca()
eta_col = 'eta_ex_gearbox'
title_text = 'Eficiência Exergética da Caixa de Transmissão'
print(f"Gerando grafico: {title_text}")
for hybrid_degree, df in dfs.items():
    if eta_col in df.columns and 'time' in df.columns:
        ax.plot(df['time'] / 60, df[eta_col] * 100, color=colors[hybrid_degree], label=f'Eficiência da Transm. - {hybrid_degree}')
ax.set_title(f'{title_text}', fontsize=axis_label_fontsize+2)
ax.set_xlabel('Tempo (min)', fontsize=axis_label_fontsize)
ax.set_ylabel('Eficiência Exergética (%)', fontsize=axis_label_fontsize)
ax.tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
ax.grid(True)
ax.set_ylim(0, 100)
place_legend_below(ax)
plt.tight_layout(rect=tight_layout_rect)
plt.savefig(f"{eta_col}_vs_time.png")
plt.close()
print(f"Grafico salvo como: {eta_col}_vs_time.png")

# Gráfico 4: Eficiencia Exergetica da Helice (Sist. Termico)
plt.figure(figsize=(figure_width, figure_height))
ax = plt.gca()
eta_col = 'eta_ex_prop_SysTermico'
title_text = 'Eficiência Exergética da Hélice (Sistema Propulsivo Térmico)'
print(f"Gerando grafico: {title_text}")
for hybrid_degree, df in dfs.items():
    if eta_col in df.columns and 'time' in df.columns:
        ax.plot(df['time'] / 60, df[eta_col] * 100, color=colors[hybrid_degree], label=f'Eficiência da Hélice - {hybrid_degree}')
ax.set_title(f'{title_text}', fontsize=axis_label_fontsize+2)
ax.set_xlabel('Tempo (min)', fontsize=axis_label_fontsize)
ax.set_ylabel('Eficiência Exergética (%)', fontsize=axis_label_fontsize)
ax.tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
ax.grid(True)
ax.set_ylim(0, 100)
place_legend_below(ax)
plt.tight_layout(rect=tight_layout_rect)
plt.savefig(f"{eta_col}_vs_time.png")
plt.close()
print(f"Grafico salvo como: {eta_col}_vs_time.png")

# Gráfico 5: Eficiencia Exergetica da Bateria
plt.figure(figsize=(figure_width, figure_height))
ax = plt.gca()
eta_col = 'eta_ex_bat'
title_text = 'Eficiência Exergética das Baterias'
print(f"Gerando grafico: {title_text}")
for hybrid_degree, df in dfs.items():
    if hybrid_degree != 'Convencional' and eta_col in df.columns and 'time' in df.columns:
        ax.plot(df['time'] / 60, df[eta_col] * 100, color=colors[hybrid_degree], label=f'Eficiência das Baterias - {hybrid_degree}')
ax.set_title(f'{title_text}', fontsize=axis_label_fontsize+2)
ax.set_xlabel('Tempo (min)', fontsize=axis_label_fontsize)
ax.set_ylabel('Eficiência Exergética (%)', fontsize=axis_label_fontsize)
ax.tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
ax.grid(True)
ax.set_ylim(0, 100)
place_legend_below(ax)
plt.tight_layout(rect=tight_layout_rect)
plt.savefig(f"{eta_col}_vs_time.png")
plt.close()
print(f"Grafico salvo como: {eta_col}_vs_time.png")

# Gráfico 6: Eficiencia Exergetica do Inversor
plt.figure(figsize=(figure_width, figure_height))
ax = plt.gca()
eta_col = 'eta_ex_inverter'
title_text = 'Eficiência Exergética do Inversor DC/AC'
print(f"Gerando grafico: {title_text}")
for hybrid_degree, df in dfs.items():
    if hybrid_degree != 'Convencional' and eta_col in df.columns and 'time' in df.columns:
        ax.plot(df['time'] / 60, df[eta_col] * 100, color=colors[hybrid_degree], label=f'Eficiência do Inversor - {hybrid_degree}')
ax.set_title(f'{title_text}', fontsize=axis_label_fontsize+2)
ax.set_xlabel('Tempo (min)', fontsize=axis_label_fontsize)
ax.set_ylabel('Eficiência Exergética (%)', fontsize=axis_label_fontsize)
ax.tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
ax.grid(True)
ax.set_ylim(0, 100)
place_legend_below(ax)
plt.tight_layout(rect=tight_layout_rect)
plt.savefig(f"{eta_col}_vs_time.png")
plt.close()
print(f"Grafico salvo como: {eta_col}_vs_time.png")

# Gráfico 7: Eficiencia Exergetica do Motor Eletrico (MTRB)
plt.figure(figsize=(figure_width, figure_height))
ax = plt.gca()
eta_col = 'eta_ex_motor_MTRB'
title_text = 'Eficiência Exergética do Motor Elétrico (MTRB - Motor/Gerador)'
print(f"Gerando grafico: {title_text}")
for hybrid_degree, df in dfs.items():
    if hybrid_degree != 'Convencional' and eta_col in df.columns and 'time' in df.columns:
        ax.plot(df['time'] / 60, df[eta_col] * 100, color=colors[hybrid_degree], label=f'Efic. do MTRB - {hybrid_degree}')
ax.set_title(f'{title_text}', fontsize=axis_label_fontsize+2)
ax.set_xlabel('Tempo (min)', fontsize=axis_label_fontsize)
ax.set_ylabel('Eficiência Exergética (%)', fontsize=axis_label_fontsize)
ax.tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
ax.grid(True)
ax.set_ylim(0, 100)
place_legend_below(ax)
plt.tight_layout(rect=tight_layout_rect)
plt.savefig(f"{eta_col}_vs_time.png")
plt.close()
print(f"Grafico salvo como: {eta_col}_vs_time.png")

# Gráfico 8: Eficiencia Exergetica do Motor Eletrico (WTP)
plt.figure(figsize=(figure_width, figure_height))
ax = plt.gca()
eta_col = 'eta_ex_motor_WTP'
title_text = 'Eficiência Exergética do Motor Elétrico (Ponta de Asa)'
print(f"Gerando grafico: {title_text}")
for hybrid_degree, df in dfs.items():
    if hybrid_degree != 'Convencional' and eta_col in df.columns and 'time' in df.columns:
        ax.plot(df['time'] / 60, df[eta_col] * 100, color=colors[hybrid_degree], label=f'Efic. do Mot. Elét. WTP - {hybrid_degree}')
ax.set_title(f'{title_text}', fontsize=axis_label_fontsize+2)
ax.set_xlabel('Tempo (min)', fontsize=axis_label_fontsize)
ax.set_ylabel('Eficiência Exergética (%)', fontsize=axis_label_fontsize)
ax.tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
ax.grid(True)
ax.set_ylim(0, 100)
place_legend_below(ax)
plt.tight_layout(rect=tight_layout_rect)
plt.savefig(f"{eta_col}_vs_time.png")
plt.close()
print(f"Grafico salvo como: {eta_col}_vs_time.png")

# Gráfico 9: Eficiencia Exergetica da Helice (WTP)
plt.figure(figsize=(figure_width, figure_height))
ax = plt.gca()
eta_col = 'eta_ex_prop_WTP'
title_text = 'Eficiência Exergética da Hélice (Sistema Propulsivo Elétrico)'
print(f"Gerando grafico: {title_text}")
for hybrid_degree, df in dfs.items():
    if hybrid_degree != 'Convencional' and eta_col in df.columns and 'time' in df.columns:
        ax.plot(df['time'] / 60, df[eta_col] * 100, color=colors[hybrid_degree], label=f'Eficiência da Hélice - {hybrid_degree}')
ax.set_title(f'{title_text}', fontsize=axis_label_fontsize+2)
ax.set_xlabel('Tempo (min)', fontsize=axis_label_fontsize)
ax.set_ylabel('Eficiência Exergética (%)', fontsize=axis_label_fontsize)
ax.tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
ax.grid(True)
ax.set_ylim(0, 100)
place_legend_below(ax)
plt.tight_layout(rect=tight_layout_rect)
plt.savefig(f"{eta_col}_vs_time.png")
plt.close()
print(f"Grafico salvo como: {eta_col}_vs_time.png")

print("\nGeracao de graficos padrao concluida.")

# --- GERACAO DOS GRAFICOS COM ZOOM ---
print("\nIniciando a geracao de graficos com zoom...")

# Gráfico Zoom 1: Bateria
plt.figure(figsize=(figure_width, figure_height))
ax = plt.gca()
eta_col = 'eta_ex_bat'
title_text = 'Eficiência Exergética das Baterias'
print(f"Gerando grafico: {title_text}")
min_zoom_val, max_zoom_val = 100, 0
for hybrid_degree, df in dfs.items():
    if hybrid_degree != 'Convencional' and eta_col in df.columns:
        non_zero_data = df[df[eta_col] > 0][eta_col] * 100
        if not non_zero_data.empty:
            min_zoom_val = min(min_zoom_val, non_zero_data.min())
            max_zoom_val = max(max_zoom_val, non_zero_data.max())
if max_zoom_val > 0:
    for hybrid_degree, df in dfs.items():
        if hybrid_degree != 'Convencional' and eta_col in df.columns and 'time' in df.columns:
            ax.plot(df['time'] / 60, df[eta_col] * 100, color=colors[hybrid_degree], label=f'Eficiência das Baterias - {hybrid_degree}')
    ax.set_title(title_text, fontsize=axis_label_fontsize+2)
    ax.set_xlabel('Tempo (min)', fontsize=axis_label_fontsize)
    ax.set_ylabel('Eficiência Exergética (%)', fontsize=axis_label_fontsize)
    ax.tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
    ax.grid(True)
    y_padding = (max_zoom_val - min_zoom_val) * 0.1
    ax.set_ylim(max(0, min_zoom_val - y_padding), min(100, max_zoom_val + y_padding))
    place_legend_below(ax)
    plt.tight_layout(rect=tight_layout_rect)
    plt.savefig(f"{eta_col}_vs_time_zoom.png")
    print(f"Grafico salvo como: {eta_col}_vs_time_zoom.png")
plt.close()

# Gráfico Zoom 2: Motor Elétrico (MTRB)
plt.figure(figsize=(figure_width, figure_height))
ax = plt.gca()
eta_col = 'eta_ex_motor_MTRB'
title_text = 'Eficiência Exergética do Motor Elétrico (MTRB - Motor/Gerador)'
print(f"Gerando grafico: {title_text}")
min_zoom_val, max_zoom_val = 100, 0
for hybrid_degree, df in dfs.items():
    if hybrid_degree != 'Convencional' and eta_col in df.columns:
        non_zero_data = df[df[eta_col] > 0][eta_col] * 100
        if not non_zero_data.empty:
            min_zoom_val = min(min_zoom_val, non_zero_data.min())
            max_zoom_val = max(max_zoom_val, non_zero_data.max())
if max_zoom_val > 0:
    for hybrid_degree, df in dfs.items():
        if hybrid_degree != 'Convencional' and eta_col in df.columns and 'time' in df.columns:
            ax.plot(df['time'] / 60, df[eta_col] * 100, color=colors[hybrid_degree], label=f'Efic. do MTRB - {hybrid_degree}')
    ax.set_title(title_text, fontsize=axis_label_fontsize+2)
    ax.set_xlabel('Tempo (min)', fontsize=axis_label_fontsize)
    ax.set_ylabel('Eficiência Exergética (%)', fontsize=axis_label_fontsize)
    ax.tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
    ax.grid(True)
    y_padding = (max_zoom_val - min_zoom_val) * 0.1
    ax.set_ylim(max(0, min_zoom_val - y_padding), min(100, max_zoom_val + y_padding))
    place_legend_below(ax)
    plt.tight_layout(rect=tight_layout_rect)
    plt.savefig(f"{eta_col}_vs_time_zoom.png")
    print(f"Grafico salvo como: {eta_col}_vs_time_zoom.png")
plt.close()

# Gráfico Zoom 3: Motor Elétrico (WTP)
plt.figure(figsize=(figure_width, figure_height))
ax = plt.gca()
eta_col = 'eta_ex_motor_WTP'
title_text = 'Eficiência Exergética do Motor Elétrico (Ponta de Asa)'
print(f"Gerando grafico: {title_text}")
min_zoom_val, max_zoom_val = 100, 0
for hybrid_degree, df in dfs.items():
    if hybrid_degree != 'Convencional' and eta_col in df.columns:
        non_zero_data = df[df[eta_col] > 0][eta_col] * 100
        if not non_zero_data.empty:
            min_zoom_val = min(min_zoom_val, non_zero_data.min())
            max_zoom_val = max(max_zoom_val, non_zero_data.max())
if max_zoom_val > 0:
    for hybrid_degree, df in dfs.items():
        if hybrid_degree != 'Convencional' and eta_col in df.columns and 'time' in df.columns:
            ax.plot(df['time'] / 60, df[eta_col] * 100, color=colors[hybrid_degree], label=f'Efic. do Mot. Elét. WTP - {hybrid_degree}')
    ax.set_title(title_text, fontsize=axis_label_fontsize+2)
    ax.set_xlabel('Tempo (min)', fontsize=axis_label_fontsize)
    ax.set_ylabel('Eficiência Exergética (%)', fontsize=axis_label_fontsize)
    ax.tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
    ax.grid(True)
    y_padding = (max_zoom_val - min_zoom_val) * 0.1
    ax.set_ylim(max(0, min_zoom_val - y_padding), min(100, max_zoom_val + y_padding))
    place_legend_below(ax)
    plt.tight_layout(rect=tight_layout_rect)
    plt.savefig(f"{eta_col}_vs_time_zoom.png")
    print(f"Grafico salvo como: {eta_col}_vs_time_zoom.png")
plt.close()

print("\nGeracao de graficos concluida com sucesso.")
