"""
Sistema de Alertas para monitoramento de condições críticas
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import logging
from typing import List, Dict

class AlertSystem:
    def __init__(self):
        self.alerts = []
        self.setup_logging()
    
    def setup_logging(self):
        """Configura o sistema de logs"""
        logging.basicConfig(
            filename='alerts.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def check_humidity_alert(self, humidity: float) -> bool:
        """Verifica se a umidade está em níveis críticos"""
        if humidity < 45:
            self.create_alert("CRÍTICO", f"Umidade muito baixa: {humidity}%")
            return True
        elif humidity > 55:
            self.create_alert("CRÍTICO", f"Umidade muito alta: {humidity}%")
            return True
        return False
    
    def check_weather_alert(self, rain_probability: float) -> bool:
        """Verifica se há alerta de chuva"""
        if rain_probability > 70:
            self.create_alert("ATENÇÃO", f"Alta probabilidade de chuva: {rain_probability}%")
            return True
        return False
    
    def create_alert(self, level: str, message: str):
        """Cria um novo alerta"""
        alert = {
            'timestamp': datetime.now(),
            'level': level,
            'message': message
        }
        self.alerts.append(alert)
        logging.info(f"Alerta criado: {level} - {message}")
    
    def display_alerts(self):
        """Exibe os alertas no dashboard"""
        if not self.alerts:
            st.info("Nenhum alerta registrado.")
            return
        
        df = pd.DataFrame(self.alerts)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp', ascending=False)
        
        st.subheader("🚨 Alertas do Sistema")
        
        # Contagem de alertas por nível
        alert_counts = df['level'].value_counts()
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Alertas Críticos", alert_counts.get("CRÍTICO", 0))
        with col2:
            st.metric("Alertas de Atenção", alert_counts.get("ATENÇÃO", 0))
        
        # Tabela de alertas
        st.write("### Histórico de Alertas")
        
        def color_level(val):
            if val == "CRÍTICO":
                return 'color: red; font-weight: bold'
            elif val == "ATENÇÃO":
                return 'color: orange; font-weight: bold'
            return ''
        
        styled_df = df.style\
            .format({'timestamp': lambda x: x.strftime('%d/%m/%Y %H:%M:%S')})\
            .applymap(color_level, subset=['level'])
        
        st.dataframe(styled_df, width=1000)
    
    def clear_alerts(self):
        """Limpa todos os alertas"""
        self.alerts = []
        logging.info("Todos os alertas foram limpos") 