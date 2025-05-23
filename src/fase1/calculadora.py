"""
Calculadora de métricas agrícolas e estatísticas
"""
import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import plotly.express as px
from typing import Dict, List, Tuple

class CalculadoraAgricola:
    def __init__(self):
        # Configurações de clima
        self.city = "Dourados"
        self.api_key = "c60a4792ccbe5983e113c048825b78fb"
        
        # Dados de insumos
        self.insumos_culturas = {
            'soja': {
                'Nitrogênio (N)': 17.5,
                'Fósforo (P)': 4.5,
                'Potássio (K)': 5
            },
            'milho': {
                'Nitrogênio (N)': 1.75,
                'Fósforo (P)': 2.5,
                'Potássio (K)': 4
            }
        }
        
        self.unidades_medidas = {
            'soja': {
                'Nitrogênio (N)': 'g',
                'Fósforo (P)': 'g',
                'Potássio (K)': 'g'
            },
            'milho': {
                'Nitrogênio (N)': 'g',
                'Fósforo (P)': 'g',
                'Potássio (K)': 'g'
            }
        }
        
        # Inicializar histórico
        if 'calculos_historico' not in st.session_state:
            st.session_state.calculos_historico = []
    
    def calcular_area_e_ruas(self, cultura: str, comprimento: float, largura: float) -> Tuple[float, int]:
        """Calcula a área e número de ruas"""
        area = largura * comprimento
        
        # Calcula o número de ruas com base na largura do terreno
        largura_ideal = 10
        if largura >= 2 * largura_ideal:
            ruas = int(largura // largura_ideal)
        else:
            ruas = 1
            
        return area, ruas
    
    def calcular_insumos(self, area: float, cultura: str, insumos_selecionados: List[str]) -> Dict[str, float]:
        """Calcula os insumos necessários"""
        insumos_detalhados = {}
        for insumo in insumos_selecionados:
            if insumo in self.insumos_culturas[cultura]:
                quantidade_por_m2 = self.insumos_culturas[cultura][insumo]
                insumos_detalhados[insumo] = area * quantidade_por_m2
        return insumos_detalhados
    
    def adicionar_insumo(self, cultura: str, nome: str, quantidade: float, unidade: str):
        """Adiciona novo insumo para uma cultura"""
        self.insumos_culturas[cultura][nome] = quantidade
        self.unidades_medidas[cultura][nome] = unidade
    
    def calcular_estatisticas(self, areas: List[float]) -> Dict[str, float]:
        """Calcula estatísticas básicas das áreas"""
        estatisticas = {
            'média': np.mean(areas),
            'mínimo': np.min(areas),
            'máximo': np.max(areas),
            'variância': np.var(areas),
            'desvio_padrão': np.std(areas),
            'quartis': np.percentile(areas, [25, 50, 75])
        }
        return estatisticas
    
    def obter_clima(self) -> Dict:
        """Obtém dados do clima atual"""
        url = f'https://api.openweathermap.org/data/2.5/weather?q={self.city}&appid={self.api_key}&lang=pt_br'
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            return {
                'clima': data['weather'][0]['description'],
                'temperatura': round(data['main']['temp'] - 273.15, 2)
            }
        return None
    
    def obter_previsao_chuva(self) -> pd.DataFrame:
        """Obtém previsão de chuva para os próximos 5 dias"""
        url = f"https://api.openweathermap.org/data/2.5/forecast?q={self.city}&appid={self.api_key}&units=metric"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            previsoes = []
            
            for item in data['list']:
                previsoes.append({
                    'data': datetime.fromtimestamp(item['dt']),
                    'prob_chuva': f"{round(item['pop'] * 100)}%"
                })
            
            return pd.DataFrame(previsoes)
        return None
    
    def display_calculadora(self):
        """Interface principal no Streamlit"""
        st.subheader("🌾 Calculadora Agrícola")
        
        # Tabs para diferentes funcionalidades
        tab1, tab2, tab3, tab4 = st.tabs([
            "Calcular Insumos",
            "Estatísticas",
            "Previsão do Tempo",
            "Gerenciar Insumos"
        ])
        
        # Tab 1: Cálculo de Insumos
        with tab1:
            st.write("### Cálculo de Insumos")
            
            # Seleção de cultura
            cultura = st.selectbox(
                "Selecione a cultura:",
                ['soja', 'milho'],
                format_func=lambda x: x.capitalize()
            )
            
            # Entrada de dimensões
            col1, col2 = st.columns(2)
            with col1:
                if cultura == 'soja':
                    lado = st.number_input("Lado do terreno quadrado (m)", min_value=0.0, value=100.0)
                    comprimento = largura = lado
                else:
                    comprimento = st.number_input("Comprimento do terreno (m)", min_value=0.0, value=100.0)
            
            with col2:
                if cultura == 'milho':
                    largura = st.number_input("Largura do terreno (m)", min_value=0.0, value=50.0)
            
            # Seleção de insumos
            insumos_disponiveis = list(self.insumos_culturas[cultura].keys())
            insumos_selecionados = st.multiselect(
                "Selecione os insumos desejados:",
                insumos_disponiveis,
                default=insumos_disponiveis
            )
            
            if st.button("Calcular"):
                # Cálculos
                area, ruas = self.calcular_area_e_ruas(cultura, comprimento, largura)
                insumos = self.calcular_insumos(area, cultura, insumos_selecionados)
                
                # Exibição dos resultados
                st.write("### Resultados")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Área Total", f"{area:.2f} m²")
                with col2:
                    st.metric("Número de Ruas", str(ruas))
                
                st.write("#### Insumos Necessários")
                for insumo, quantidade in insumos.items():
                    unidade = self.unidades_medidas[cultura][insumo]
                    st.metric(insumo, f"{quantidade:.2f} {unidade}")
                
                # Salvar no histórico
                calculo = {
                    'data': pd.Timestamp.now(),
                    'cultura': cultura.capitalize(),
                    'area': area,
                    'ruas': ruas,
                    'insumos': insumos
                }
                st.session_state.calculos_historico.append(calculo)
        
        # Tab 2: Estatísticas
        with tab2:
            st.write("### Análise de Áreas")
            
            # Input de áreas
            areas_input = st.text_input(
                "Digite as áreas em m² (separadas por vírgula)",
                value="1000, 1500, 2000, 3000"
            )
            
            try:
                areas = [float(x.strip()) for x in areas_input.split(',')]
                
                if st.button("Calcular Estatísticas"):
                    estatisticas = self.calcular_estatisticas(areas)
                    
                    # Exibir resultados
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Média", f"{estatisticas['média']:.2f} m²")
                        st.metric("Mínimo", f"{estatisticas['mínimo']:.2f} m²")
                        st.metric("Máximo", f"{estatisticas['máximo']:.2f} m²")
                    
                    with col2:
                        st.metric("Variância", f"{estatisticas['variância']:.2f}")
                        st.metric("Desvio Padrão", f"{estatisticas['desvio_padrão']:.2f}")
                    
                    st.write("#### Quartis")
                    st.write(f"- 25%: {estatisticas['quartis'][0]:.2f} m²")
                    st.write(f"- 50%: {estatisticas['quartis'][1]:.2f} m²")
                    st.write(f"- 75%: {estatisticas['quartis'][2]:.2f} m²")
                    
                    # Gráfico de distribuição
                    fig = px.box(areas, title="Distribuição das Áreas")
                    st.plotly_chart(fig)
            
            except ValueError:
                st.error("Por favor, insira números válidos separados por vírgula.")
        
        # Tab 3: Previsão do Tempo
        with tab3:
            st.write("### Previsão do Tempo")
            
            # Clima atual
            clima = self.obter_clima()
            if clima:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Temperatura", f"{clima['temperatura']}°C")
                with col2:
                    st.metric("Condição", clima['clima'].capitalize())
            
            # Previsão de chuva
            st.write("#### Probabilidade de Chuva")
            previsao = self.obter_previsao_chuva()
            
            if previsao is not None:
                # Converter probabilidades para números
                previsao['prob_numerica'] = previsao['prob_chuva'].str.rstrip('%').astype(float)
                
                # Gráfico de linha
                fig = px.line(
                    previsao,
                    x='data',
                    y='prob_numerica',
                    title=f'Probabilidade de Chuva em {self.city}',
                    labels={'data': 'Data e Hora', 'prob_numerica': 'Probabilidade (%)'}
                )
                st.plotly_chart(fig)
                
                # Tabela de previsão
                st.write("#### Detalhamento")
                previsao['data'] = previsao['data'].dt.strftime('%d/%m/%Y %H:%M')
                st.dataframe(previsao[['data', 'prob_chuva']])
        
        # Tab 4: Gerenciar Insumos
        with tab4:
            st.write("### Adicionar Novo Insumo")
            
            novo_cultura = st.selectbox(
                "Cultura:",
                ['soja', 'milho'],
                format_func=lambda x: x.capitalize(),
                key="novo_insumo_cultura"
            )
            
            col1, col2, col3 = st.columns(3)
            with col1:
                novo_nome = st.text_input("Nome do insumo")
            with col2:
                nova_quantidade = st.number_input("Quantidade por m²", min_value=0.0, value=1.0)
            with col3:
                nova_unidade = st.selectbox("Unidade", ['g', 'kg', 'L'])
            
            if st.button("Adicionar Insumo"):
                if novo_nome and nova_quantidade > 0:
                    self.adicionar_insumo(novo_cultura, novo_nome, nova_quantidade, nova_unidade)
                    st.success(f"Insumo {novo_nome} adicionado com sucesso!")
                else:
                    st.error("Por favor, preencha todos os campos corretamente.") 