Códigos Python (v. 3.6.0):
- analise_energetica.py: script em Python que contém cálculos referentes à análise energética, como balanços de energia e eficiências de componentes ou globais.
- analise_exergetica.py: script em Python que contém cálculos referentes à análise exergética, como balanços de exergia, fluxos de exergia destruída e eficiências exergéticas de componentes ou globais.
- plota_graficos.py: script em Python que gera os gráficos da análise exergética a partir das planilhas CSV de resultados.

OBS: É necessário que o arquivo A2highT.cti, assim como as planilhas CSV de entrada (descritas a seguir), estejam no mesmo diretório dos códigos .py para o funcionamento dos códigos.

Arquivos de entrada CSV:
- resultados_suave_15.csv: planilha de resultados obtidos pela simulação SUAVE-FutPrInt50, para a missão definida de 400 km e 5300 kg de MTOW, para 15% de hibridização.
- resultados_suave_20.csv: planilha de resultados obtidos pela simulação SUAVE-FutPrInt50, para a missão definida de 400 km e 5300 kg de MTOW, para 20% de hibridização.
- resultados_suave_30.csv: planilha de resultados obtidos pela simulação SUAVE-FutPrInt50, para a missão definida de 400 km e 5300 kg de MTOW, para 30% de hibridização.
- resultados_suave_convencional.csv: planilha de resultados obtidos pela simulação SUAVE-FutPrInt50, para a missão definida de 400 km e 5300 kg de MTOW, para a aeronave convencional (apenas motores térmicos).

Arquivos de saída/resultados CSV:
- resultados_energia_15.csv: planilha de resultados do código analise_energetica.py, para a aeronave com 15% de hibridização.
- resultados_energia_20.csv: planilha de resultados do código analise_energetica.py, para a aeronave com 20% de hibridização.
- resultados_energia_30.csv: planilha de resultados do código analise_energetica.py, para a aeronave com 30% de hibridização.
- resultados_energia_convencional.csv: planilha de resultados do código analise_energetica.py, para a aeronave convencional.

- resultados_exergia_15.csv: planilha de resultados do código analise_exergetica.py, para a aeronave com 15% de hibridização.
- resultados_energia_20.csv: planilha de resultados do código analise_exergetica.py, para a aeronave com 20% de hibridização.
- resultados_energia_30.csv: planilha de resultados do código analise_exergetica.py, para a aeronave com 30% de hibridização.
- resultados_energia_Convencional.csv: planilha de resultados do código analise_exergetica.py, para a aeronave convencional.
