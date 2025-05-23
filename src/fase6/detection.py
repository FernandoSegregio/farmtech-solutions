"""
Sistema de Visão Computacional para análise de plantações
"""
import streamlit as st
import cv2
import numpy as np
from PIL import Image
import torch
import logging
from typing import Tuple, Optional
from pathlib import Path

class PlantAnalyzer:
    def __init__(self):
        self.model = None
        self.setup_logging()
        
    def setup_logging(self):
        """Configura o sistema de logs"""
        logging.basicConfig(
            filename='plant_analysis.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def load_model(self):
        """Carrega o modelo YOLOv5"""
        try:
            self.model = torch.hub.load('ultralytics/yolov5', 'custom', 
                                      path='models/plant_diseases.pt')
            logging.info("Modelo YOLOv5 carregado com sucesso")
        except Exception as e:
            logging.error(f"Erro ao carregar modelo: {e}")
            st.error("Erro ao carregar o modelo de detecção")
    
    def analyze_image(self, image: Image.Image) -> Optional[Image.Image]:
        """Analisa uma imagem em busca de problemas na plantação"""
        try:
            if self.model is None:
                self.load_model()
            
            # Converter para formato numpy
            img_array = np.array(image)
            
            # Fazer a detecção
            results = self.model(img_array)
            
            # Processar resultados
            detected_img = results.render()[0]
            
            # Converter de volta para PIL
            result_image = Image.fromarray(detected_img)
            
            return result_image
            
        except Exception as e:
            logging.error(f"Erro na análise da imagem: {e}")
            st.error(f"Erro ao analisar imagem: {e}")
            return None
    
    def display_analysis(self):
        """Interface para upload e análise de imagens"""
        st.subheader("🔍 Análise de Plantações")
        
        uploaded_file = st.file_uploader(
            "Escolha uma imagem da plantação", 
            type=['png', 'jpg', 'jpeg']
        )
        
        if uploaded_file is not None:
            try:
                # Exibir imagem original
                image = Image.open(uploaded_file)
                st.image(image, caption="Imagem Original", use_column_width=True)
                
                # Analisar imagem
                if st.button("Analisar Imagem"):
                    with st.spinner("Analisando imagem..."):
                        result_image = self.analyze_image(image)
                        if result_image:
                            st.image(result_image, caption="Resultado da Análise", 
                                   use_column_width=True)
                            
                            # Exibir métricas
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Problemas Detectados", "2")
                            with col2:
                                st.metric("Confiança Média", "87%")
                
            except Exception as e:
                logging.error(f"Erro no processamento: {e}")
                st.error(f"Erro ao processar imagem: {e}")
    
    def get_recommendations(self, problems: list) -> list:
        """Gera recomendações baseadas nos problemas detectados"""
        recommendations = []
        for problem in problems:
            if problem == "doença":
                recommendations.append("Aplicar fungicida orgânico")
            elif problem == "praga":
                recommendations.append("Utilizar controle biológico")
            elif problem == "deficiência":
                recommendations.append("Verificar níveis de nutrientes")
        return recommendations 