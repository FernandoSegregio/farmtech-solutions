"""
Serviço de previsão do tempo para a Fase 4
"""
import requests
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
from dotenv import load_dotenv
import logging
from typing import Tuple, Optional, Dict, Any

class WeatherService:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('OPENWEATHER_API_KEY', 'c60a4792ccbe5983e113c048825b78fb')
        self.city = os.getenv('CITY', 'Juiz de Fora')
        
        logging.basicConfig(
            filename='weather.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def get_coordinates(self) -> Tuple[Optional[float], Optional[float]]:
        """Obtém as coordenadas geográficas da cidade"""
        try:
            url = "http://api.openweathermap.org/data/2.5/weather"
            params = {
                "q": self.city,
                "appid": self.api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            lat = data['coord']['lat']
            lon = data['coord']['lon']
            
            logging.info(f"Coordenadas obtidas: lat={lat}, lon={lon}")
            return lat, lon
            
        except Exception as e:
            logging.error(f"Erro ao obter coordenadas: {e}")
            st.error(f"Erro ao obter coordenadas: {e}")
            return None, None
    
    def consultar_previsao(self):
        """Consulta a previsão do tempo"""
        try:
            url = f"https://api.openweathermap.org/data/2.5/forecast"
            params = {
                "q": self.city,
                "appid": self.api_key,
                "units": "metric"
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            self._exibir_previsao(data)
            
        except Exception as e:
            logging.error(f"Erro ao consultar previsão: {e}")
            st.error(f"Erro ao consultar previsão do tempo: {e}")
    
    def _exibir_previsao(self, data: Dict[str, Any]):
        """Exibe a previsão do tempo"""
        previsao = data['list']
        
        # Criar DataFrame
        df = pd.DataFrame([
            {
                'data': datetime.fromtimestamp(item['dt']),
                'temperatura': item['main']['temp'],
                'umidade': item['main']['humidity'],
                'probabilidade_chuva': item.get('pop', 0) * 100
            } for item in previsao[:7 * 8]  # 7 dias, 8 medições por dia
        ])
        
        # Métricas
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Temperatura Média",
                f"{df['temperatura'].mean():.1f}°C"
            )
        with col2:
            st.metric(
                "Umidade Média",
                f"{df['umidade'].mean():.1f}%"
            )
        with col3:
            st.metric(
                "Chance de Chuva Média",
                f"{df['probabilidade_chuva'].mean():.1f}%"
            )
        
        # Gráfico de temperatura
        fig_temp = px.line(
            df,
            x='data',
            y='temperatura',
            title='Previsão de Temperatura'
        )
        st.plotly_chart(fig_temp)
        
        # Gráfico de probabilidade de chuva
        fig_chuva = px.bar(
            df,
            x='data',
            y='probabilidade_chuva',
            title='Probabilidade de Chuva'
        )
        st.plotly_chart(fig_chuva)
        
        # Alertas
        chuva_alta = df[df['probabilidade_chuva'] > 70]
        if not chuva_alta.empty:
            st.warning(f"⚠️ Alta probabilidade de chuva em {len(chuva_alta)} períodos") 