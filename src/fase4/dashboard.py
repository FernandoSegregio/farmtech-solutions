"""
Dashboard principal integrando todas as fases do FarmTech Solutions
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import logging
from typing import Tuple
import os
from pathlib import Path

from scripts.connect_db import conectar_banco, fechar_conexao
from scripts.setup_db import setup_banco_dados
from scripts.consulta_banco import carregar_dados_umidade, carregar_dados_temperatura, carregar_dados_ph
from fase4.mqtt_handler import MQTTHandler
from fase4.weather_service import WeatherService
from fase5.alerts import AlertSystem
from fase6.detection import PlantAnalyzer
from fase1.calculadora import CalculadoraAgricola
from log.logger_config import configurar_logging

class Dashboard:
    def __init__(self):
        self.logger = configurar_logging()
        self.mqtt_handler = MQTTHandler()
        self.weather_service = WeatherService()
        self.alert_system = AlertSystem()
        self.plant_analyzer = PlantAnalyzer()
        self.calculadora = CalculadoraAgricola()
        self.setup_page()
        
    def setup_page(self):
        """Configuração inicial da página"""
        st.set_page_config(
            page_title="🚜 FarmTech - Sistema Integrado de Gestão Agrícola", 
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Estilos customizados
        st.markdown("""
            <style>
            .stButton>button {
                background-color: #39ff14;
                color: #000080;
                font-size: 16px;
                border: none;
                border-radius: 5px;
                margin-bottom: 6px;
                cursor: pointer;
                width: 286px;
            }
            .stButton>button:hover {
                background-color: #2ecc71;
                color: #000080 !important;
            }
            .stButton>button:focus {
                background-color: #000080;
                color: #39ff14 !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
    def exibir_dados_sensor_umidade(self, conn):
        """Exibe os dados do sensor de umidade"""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id_leitura_umidade, id_sensor_umidade, 
                   TO_CHAR(data_leitura, 'YYYY-MM-DD') as data_leitura,
                   TO_CHAR(hora_leitura, 'HH24:MI:SS') as hora_leitura, 
                   valor_umidade_leitura 
            FROM LEITURA_SENSOR_UMIDADE 
            ORDER BY data_leitura DESC, hora_leitura DESC
        """)
        resultados = cursor.fetchall()
        
        if resultados:
            df = pd.DataFrame(resultados, columns=[
                'ID Leitura', 'ID Sensor', 'Data', 'Hora', 'Umidade (%)'
            ])
            
            # Formatação e métricas
            self._exibir_metricas_umidade(df)
            self._exibir_grafico_umidade(df)
            self._exibir_tabela_umidade(df)
        else:
            st.info("Nenhum dado encontrado para o sensor de umidade.")
        
        cursor.close()
    
    def _exibir_metricas_umidade(self, df):
        """Exibe métricas do sensor de umidade"""
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Média de Umidade", 
                f"{df['Umidade (%)'].mean():.2f}%",
                delta_color="inverse"
            )
        with col2:
            ultimo_valor = df['Umidade (%)'].iloc[0]
            status = "🔴" if (ultimo_valor < 45 or ultimo_valor > 55) else "🟢"
            st.metric(
                "Última Leitura",
                f"{ultimo_valor:.2f}% {status}"
            )
        with col3:
            valores_fora = len(df[(df['Umidade (%)'] < 45) | (df['Umidade (%)'] > 55)])
            st.metric("Leituras Fora do Limite", valores_fora)
    
    def _exibir_grafico_umidade(self, df):
        """Exibe gráfico de umidade"""
        try:
            # Combina data e hora em uma única coluna datetime
            df['Data_Hora'] = pd.to_datetime(df['Data'] + ' ' + df['Hora'])
            
            # Ordena o DataFrame pela data/hora
            df = df.sort_values('Data_Hora')
            
            fig = px.line(df, x='Data_Hora', y='Umidade (%)', 
                         title='Monitoramento de Umidade',
                         markers=True)
            fig.add_hline(y=55, line_dash="dash", line_color="red", 
                         annotation_text="Limite Máximo (55%)")
            fig.add_hline(y=45, line_dash="dash", line_color="red", 
                         annotation_text="Limite Mínimo (45%)")
            
            # Configura o layout para melhor visualização
            fig.update_layout(
                xaxis_title="Data e Hora",
                yaxis_title="Umidade (%)",
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Erro ao gerar gráfico: {str(e)}")
            print(f"Erro ao gerar gráfico: {str(e)}")
            print("DataFrame:", df.head())
    
    def _exibir_tabela_umidade(self, df):
        """Exibe tabela de dados de umidade"""
        st.write("### Histórico de Leituras")
        styled_df = df.style.format({'Umidade (%)': '{:.2f}'})
        st.dataframe(styled_df, width=1000)
    
    def exibir_dados_sensor_temperatura(self, conn):
        """Exibe os dados do sensor de temperatura"""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id_leitura_temperatura, id_sensor_umidade, 
                   TO_CHAR(data_leitura, 'YYYY-MM-DD') as data_leitura,
                   TO_CHAR(hora_leitura, 'HH24:MI:SS') as hora_leitura, 
                   valor_temperatura 
            FROM LEITURA_SENSOR_TEMPERATURA 
            ORDER BY data_leitura DESC, hora_leitura DESC
        """)
        resultados = cursor.fetchall()
        
        if resultados:
            df = pd.DataFrame(resultados, columns=[
                'ID Leitura', 'ID Sensor', 'Data', 'Hora', 'Temperatura (°C)'
            ])
            
            # Formatação e métricas
            self._exibir_metricas_temperatura(df)
            self._exibir_grafico_temperatura(df)
            self._exibir_tabela_temperatura(df)
        else:
            st.info("Nenhum dado encontrado para o sensor de temperatura.")
        
        cursor.close()
    
    def _exibir_metricas_temperatura(self, df):
        """Exibe métricas do sensor de temperatura"""
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Temperatura Média", 
                f"{df['Temperatura (°C)'].mean():.2f}°C",
                delta_color="inverse"
            )
        with col2:
            ultimo_valor = df['Temperatura (°C)'].iloc[0]
            status = "🔴" if (ultimo_valor < 12 or ultimo_valor > 36) else "🟢"
            st.metric(
                "Última Leitura",
                f"{ultimo_valor:.2f}°C {status}"
            )
        with col3:
            valores_fora = len(df[(df['Temperatura (°C)'] < 12) | (df['Temperatura (°C)'] > 36)])
            st.metric("Leituras Fora do Limite", valores_fora)
    
    def _exibir_grafico_temperatura(self, df):
        """Exibe gráfico de temperatura"""
        try:
            # Combina data e hora em uma única coluna datetime
            df['Data_Hora'] = pd.to_datetime(df['Data'] + ' ' + df['Hora'])
            
            # Ordena o DataFrame pela data/hora
            df = df.sort_values('Data_Hora')
            
            fig = px.line(df, x='Data_Hora', y='Temperatura (°C)', 
                         title='Monitoramento de Temperatura',
                         markers=True)
            fig.add_hline(y=36, line_dash="dash", line_color="red", 
                         annotation_text="Limite Máximo (36°C)")
            fig.add_hline(y=12, line_dash="dash", line_color="blue", 
                         annotation_text="Limite Mínimo (12°C)")
            
            # Configura o layout para melhor visualização
            fig.update_layout(
                xaxis_title="Data e Hora",
                yaxis_title="Temperatura (°C)",
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Erro ao gerar gráfico: {str(e)}")
            print(f"Erro ao gerar gráfico: {str(e)}")
            print("DataFrame:", df.head())
    
    def _exibir_tabela_temperatura(self, df):
        """Exibe tabela de dados de temperatura"""
        st.write("### Histórico de Leituras")
        styled_df = df.style.format({'Temperatura (°C)': '{:.2f}'})
        st.dataframe(styled_df, width=1000)
    
    def exibir_dados_sensor_ph(self, conn):
        """Exibe os dados do sensor de pH"""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id_leitura_ph, id_sensor_ph, 
                   TO_CHAR(data_leitura, 'YYYY-MM-DD') as data_leitura,
                   TO_CHAR(hora_leitura, 'HH24:MI:SS') as hora_leitura, 
                   valor_ph_leitura 
            FROM LEITURA_SENSOR_PH 
            ORDER BY data_leitura DESC, hora_leitura DESC
        """)
        resultados = cursor.fetchall()
        
        if resultados:
            df = pd.DataFrame(resultados, columns=[
                'ID Leitura', 'ID Sensor', 'Data', 'Hora', 'pH'
            ])
            
            # Formatação e métricas
            self._exibir_metricas_ph(df)
            self._exibir_grafico_ph(df)
            self._exibir_tabela_ph(df)
        else:
            st.info("Nenhum dado encontrado para o sensor de pH.")
        
        cursor.close()
    
    def _exibir_metricas_ph(self, df):
        """Exibe métricas do sensor de pH"""
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "pH Médio", 
                f"{df['pH'].mean():.2f}",
                delta_color="inverse"
            )
        with col2:
            ultimo_valor = df['pH'].iloc[0]
            # pH ideal para agricultura: 6.0 - 7.5
            status = "🔴" if (ultimo_valor < 6.0 or ultimo_valor > 7.5) else "🟢"
            st.metric(
                "Última Leitura",
                f"{ultimo_valor:.2f} {status}"
            )
        with col3:
            valores_fora = len(df[(df['pH'] < 6.0) | (df['pH'] > 7.5)])
            st.metric("Leituras Fora do Limite", valores_fora)
    
    def _exibir_grafico_ph(self, df):
        """Exibe gráfico de pH"""
        try:
            # Combina data e hora em uma única coluna datetime
            df['Data_Hora'] = pd.to_datetime(df['Data'] + ' ' + df['Hora'])
            
            # Ordena o DataFrame pela data/hora
            df = df.sort_values('Data_Hora')
            
            fig = px.line(df, x='Data_Hora', y='pH', 
                         title='Monitoramento de pH do Solo',
                         markers=True)
            fig.add_hline(y=7.5, line_dash="dash", line_color="red", 
                         annotation_text="Limite Máximo (7.5)")
            fig.add_hline(y=6.0, line_dash="dash", line_color="blue", 
                         annotation_text="Limite Mínimo (6.0)")
            
            # Configura o layout para melhor visualização
            fig.update_layout(
                xaxis_title="Data e Hora",
                yaxis_title="pH",
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Erro ao gerar gráfico: {str(e)}")
            print(f"Erro ao gerar gráfico: {str(e)}")
            print("DataFrame:", df.head())
    
    def _exibir_tabela_ph(self, df):
        """Exibe tabela de dados de pH"""
        st.write("### Histórico de Leituras")
        styled_df = df.style.format({'pH': '{:.2f}'})
        st.dataframe(styled_df, width=1000)
    
    def run(self):
        """Executa o dashboard"""
        conn = conectar_banco()
        if not conn:
            st.error("Erro ao conectar ao banco de dados.")
            return
            
        try:
            menu_options = {
                "Fase 1 - Cálculos": [
                    "Calculadora Agrícola",
                    "Histórico de Cálculos"
                ],
                "Fase 2, 3 e 4 - Automação": [
                    "Exibir Dados do Sensor de Umidade",
                    "Exibir Dados do Sensor de Temperatura",
                    "Exibir Dados do Sensor de pH",
                    "Ligar Bomba de Água",
                    "Desligar Bomba de Água",
                    "Consultar Previsão do Tempo",
                    "Configuração Inicial do Banco"
                ],
                "Fase 5 - Alertas": [
                    "Sistema de Alertas",
                    "Histórico de Alertas"
                ],
                "Fase 6 - Análise Visual": [
                    "Análise de Plantações",
                    "Histórico de Análises"
                ]
            }
            
            # Logo e título no menu lateral
            current_dir = Path(__file__).parent.parent.parent
            logo_path = current_dir / "assets" / "farm-tech-logo.png"
            
            st.sidebar.image(str(logo_path), width=300)
            st.sidebar.title("🌱 FarmTech Solutions")
            
            for category, options in menu_options.items():
                st.sidebar.subheader(category)
                for option in options:
                    if st.sidebar.button(option):
                        st.session_state.selected_button = option
            
            # Execução da opção selecionada
            selected = st.session_state.get("selected_button", "Exibir Dados do Sensor de Umidade")
            
            # Fase 1 - Cálculos
            if selected == "Calculadora Agrícola":
                st.title("Calculadora Agrícola")
                self.calculadora.display_calculadora()
            
            elif selected == "Histórico de Cálculos":
                st.title("Histórico de Cálculos")
                if 'calculos_historico' in st.session_state and st.session_state.calculos_historico:
                    for idx, calculo in enumerate(st.session_state.calculos_historico):
                        with st.expander(f"Cálculo {idx + 1} - {calculo['cultura']} - {calculo['data'].strftime('%d/%m/%Y %H:%M')}"):
                            st.write(f"**Área:** {calculo['area']:.2f} m²")
                            st.write(f"**Ruas:** {calculo['ruas']}")
                            st.write("**Insumos:**")
                            for insumo, quantidade in calculo['insumos'].items():
                                st.write(f"- {insumo}: {quantidade:.2f}")
                else:
                    st.info("Nenhum cálculo realizado ainda.")
            
            # Fase 4 - Automação
            elif selected == "Exibir Dados do Sensor de Umidade":
                st.title("Dados do Sensor de Umidade")
                self.exibir_dados_sensor_umidade(conn)
                
                # Integração com alertas
                dados = carregar_dados_umidade(conn, self.logger)
                if dados is not None and not dados.empty:
                    ultima_umidade = dados['Umidade (%)'].iloc[-1]
                    self.alert_system.check_humidity_alert(ultima_umidade, self.logger)
            
            elif selected == "Exibir Dados do Sensor de Temperatura":
                st.title("Dados do Sensor de Temperatura")
                self.exibir_dados_sensor_temperatura(conn)
                
                # Integração com alertas
                dados = carregar_dados_temperatura(conn, self.logger)
                if dados is not None and not dados.empty:
                    ultima_temperatura = dados['Temperatura (°C)'].iloc[-1]
                    # Aqui você pode adicionar alertas de temperatura se necessário
                    # self.alert_system.check_temperature_alert(ultima_temperatura, self.logger)
            
            elif selected == "Exibir Dados do Sensor de pH":
                st.title("Dados do Sensor de pH")
                self.exibir_dados_sensor_ph(conn)
                
                # Integração com alertas
                dados = carregar_dados_ph(conn, self.logger)
                if dados is not None and not dados.empty:
                    ultimo_ph = dados['pH'].iloc[-1]
                    # Aqui você pode adicionar alertas de pH se necessário
                    # self.alert_system.check_ph_alert(ultimo_ph, self.logger)
            
            elif selected == "Ligar Bomba de Água":
                st.title("Controle da Bomba de Água")
                self.mqtt_handler.ligar_bomba_agua()
            
            elif selected == "Desligar Bomba de Água":
                st.title("Controle da Bomba de Água")
                self.mqtt_handler.desligar_bomba_agua()
            
            elif selected == "Consultar Previsão do Tempo":
                st.title("Previsão do Tempo")
                previsao = self.weather_service.consultar_previsao()
                if previsao and 'rain_probability' in previsao:
                    self.alert_system.check_weather_alert(previsao['rain_probability'], self.logger)
            
            elif selected == "Configuração Inicial do Banco":
                st.title("Configuração do Banco de Dados")
                setup_banco_dados(conn)
                st.success("Banco de dados configurado com sucesso.")
            
            # Fase 5 - Alertas
            elif selected == "Sistema de Alertas":
                st.title("🚨 Sistema de Alertas")
                self.alert_system.display_alerts()
            
            elif selected == "Histórico de Alertas":
                self.alert_system.display_alerts_history()
            
            # Fase 6 - Análise Visual
            elif selected == "Análise de Plantações":
                st.title("Análise de Plantações")
                self.plant_analyzer.display_analysis()
            
            elif selected == "Histórico de Análises":
                st.title("Histórico de Análises")
                st.info("Em desenvolvimento")
                
        finally:
            fechar_conexao(conn)
            self.mqtt_handler.stop()

if __name__ == "__main__":
    dashboard = Dashboard()
    dashboard.run() 