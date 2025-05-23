"""
Dashboard principal integrando todas as fases do FarmTech Solutions
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import logging
from typing import Tuple

from scripts.connect_db import conectar_banco, fechar_conexao
from scripts.setup_db import setup_banco_dados
from scripts.consulta_banco import carregar_dados_umidade
from fase4.mqtt_handler import MQTTHandler
from fase4.weather_service import WeatherService
from fase5.alerts import AlertSystem
from fase6.detection import PlantAnalyzer
from fase1.calculadora import CalculadoraAgricola

class Dashboard:
    def __init__(self):
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
            layout="wide"
        )
        self.setup_styles()
        
    def setup_styles(self):
        """Configuração dos estilos CSS"""
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
                   data_leitura, hora_leitura, valor_umidade_leitura 
            FROM LEITURA_SENSOR_UMIDADE 
            ORDER BY hora_leitura DESC
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
        fig = px.line(df, x='Hora', y='Umidade (%)', 
                     title='Monitoramento de Umidade')
        fig.add_hline(y=55, line_dash="dash", line_color="red")
        fig.add_hline(y=45, line_dash="dash", line_color="red")
        st.plotly_chart(fig)
    
    def _exibir_tabela_umidade(self, df):
        """Exibe tabela de dados de umidade"""
        st.write("### Histórico de Leituras")
        styled_df = df.style.format({'Umidade (%)': '{:.2f}'})
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
                "Fase 4 - Automação": [
                    "Exibir Dados do Sensor de Umidade",
                    "Ligar Bomba de Água",
                    "Desligar Bomba de Água",
                    "Consultar Previsão do Tempo",
                    "Configuração Inicial do Banco"
                ],
                "Fase 5 - Alertas": [
                    "Sistema de Alertas",
                    "Histórico de Alertas",
                    "Limpar Alertas"
                ],
                "Fase 6 - Análise Visual": [
                    "Análise de Plantações",
                    "Histórico de Análises"
                ]
            }
            
            # Menu lateral com categorias
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
                dados = carregar_dados_umidade(conn)
                if dados and len(dados) > 0:
                    ultima_umidade = dados[-1]['valor_umidade_leitura']
                    self.alert_system.check_humidity_alert(ultima_umidade)
            
            elif selected == "Ligar Bomba de Água":
                st.title("Controle da Bomba de Água")
                self.mqtt_handler.ligar_bomba_agua()
            
            elif selected == "Desligar Bomba de Água":
                st.title("Controle da Bomba de Água")
                self.mqtt_handler.desligar_bomba_agua()
            
            elif selected == "Consultar Previsão do Tempo":
                st.title("Previsão do Tempo")
                self.weather_service.consultar_previsao()
            
            elif selected == "Configuração Inicial do Banco":
                st.title("Configuração do Banco de Dados")
                setup_banco_dados(conn)
                st.success("Banco de dados configurado com sucesso.")
            
            # Fase 5 - Alertas
            elif selected == "Sistema de Alertas":
                st.title("Sistema de Alertas")
                self.alert_system.display_alerts()
            
            elif selected == "Histórico de Alertas":
                st.title("Histórico de Alertas")
                self.alert_system.display_alerts()
            
            elif selected == "Limpar Alertas":
                st.title("Limpar Alertas")
                if st.button("Confirmar Limpeza"):
                    self.alert_system.clear_alerts()
                    st.success("Alertas limpos com sucesso!")
            
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