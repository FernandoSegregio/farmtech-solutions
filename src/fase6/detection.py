"""
Sistema de Visão Computacional para análise de plantações
"""
import streamlit as st
import cv2
import numpy as np
from PIL import Image
import torch
import logging
from typing import Tuple, Optional, List, Dict
from pathlib import Path
import os
import traceback

class PlantAnalyzer:
    def __init__(self):
        self.model = None
        self.setup_logging()
        # Classes específicas para pragas agrícolas
        self.classes = {
            0: 'lagarta',
            1: 'pulgão', 
            2: 'percevejo',
            3: 'mosca_branca',
            4: 'trips',
            5: 'ácaro',
            6: 'cochonilha',
            7: 'cigarrinha',
            8: 'broca',
            9: 'vaquinha'
        }
        self.problem_colors = {
            'lagarta': (255, 0, 0),      # Vermelho
            'pulgão': (0, 255, 0),       # Verde
            'percevejo': (0, 0, 255),    # Azul
            'mosca_branca': (255, 165, 0), # Laranja
            'trips': (128, 0, 128),      # Roxo
            'ácaro': (255, 255, 0),      # Amarelo
            'cochonilha': (255, 192, 203), # Rosa
            'cigarrinha': (0, 255, 255),  # Ciano
            'broca': (139, 69, 19),      # Marrom
            'vaquinha': (0, 128, 0)      # Verde escuro
        }
        
    def setup_logging(self):
        """Configura o sistema de logs"""
        log_dir = Path(__file__).parent.parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            filename=str(log_dir / 'plant_analysis.log'),
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def load_model(self):
        """Carrega o modelo YOLOv5 pré-treinado para pragas"""
        try:
            logging.debug("Iniciando carregamento do modelo...")
            
            # Carrega modelo usando torch hub
            model_path = Path(__file__).parent.parent.parent / "models" / "yolov5_pests.pt"
            if not model_path.exists():
                logging.error(f"Modelo não encontrado em {model_path}")
                st.error("❌ Modelo não encontrado. Execute o script de configuração primeiro.")
                return False
            
            # Limpa o cache do torch hub
            torch.hub.set_dir(str(Path.home() / '.cache' / 'torch' / 'hub' / 'new'))
            
            # Carrega o modelo base
            self.model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True, force_reload=True, trust_repo=True)
            
            # Carrega os pesos e configurações salvos
            checkpoint = torch.load(model_path)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.model.names = checkpoint['names']
            self.model.conf = checkpoint['conf']
            self.model.iou = checkpoint['iou']
            self.model.max_det = checkpoint.get('max_det', 100)
            self.model.agnostic = checkpoint.get('agnostic', True)
            self.model.classes = checkpoint.get('classes', [0])  # Apenas lagartas por padrão
            
            # Configura o modelo para inferência
            self.model.eval()
            if torch.cuda.is_available():
                self.model.cuda()
                logging.info("Modelo movido para GPU")
            else:
                logging.info("Usando CPU para inferência")
            
            logging.info("✅ Modelo YOLOv5 para pragas carregado com sucesso")
            return True
                
        except Exception as e:
            logging.error(f"Erro ao carregar modelo: {str(e)}")
            logging.error(f"Traceback: {traceback.format_exc()}")
            st.error(f"❌ Erro ao carregar o modelo: {str(e)}")
            return False
    
    def enhance_image(self, img_array: np.ndarray) -> np.ndarray:
        """Melhora a imagem para facilitar a detecção de pragas"""
        try:
            # Lista para armazenar as diferentes versões da imagem
            enhanced_images = []
            
            # 1. Versão com realce de textura e segmentação
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            # Aplica threshold adaptativo para segmentar objetos
            thresh = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY_INV, 21, 2
            )
            
            # Operações morfológicas para limpar ruído
            kernel = np.ones((3,3), np.uint8)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
            
            # Converte threshold para RGB
            thresh_rgb = cv2.cvtColor(thresh, cv2.COLOR_GRAY2RGB)
            enhanced_images.append(thresh_rgb)
            
            # 2. Versão com destaque para segmentos escuros
            lab = cv2.cvtColor(img_array, cv2.COLOR_RGB2LAB)
            l, a, b = cv2.split(lab)
            
            # Aplica threshold no canal L para identificar regiões escuras
            _, dark_mask = cv2.threshold(l, 100, 255, cv2.THRESH_BINARY_INV)
            dark_mask = cv2.dilate(dark_mask, kernel, iterations=2)
            
            # Cria imagem realçando regiões escuras
            dark_enhanced = img_array.copy()
            dark_enhanced[dark_mask > 0] = dark_enhanced[dark_mask > 0] * 1.5
            enhanced_images.append(dark_enhanced)
            
            # 3. Versão com realce de bordas direcionais
            # Detecta bordas horizontais (característica de lagartas)
            sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            # Combina bordas com peso maior para horizontais
            edges = cv2.addWeighted(np.absolute(sobelx), 0.7, np.absolute(sobely), 0.3, 0)
            edges = np.uint8(edges)
            edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
            enhanced_images.append(edges)
            
            # 4. Versão com realce de contraste local
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            enhanced_gray = clahe.apply(gray)
            enhanced_gray = cv2.cvtColor(enhanced_gray, cv2.COLOR_GRAY2RGB)
            enhanced_images.append(enhanced_gray)
            
            # 5. Versão com segmentação de cor
            hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
            # Define faixas de cor típicas de lagartas
            lower_brown = np.array([10, 50, 50])
            upper_brown = np.array([30, 255, 255])
            mask_brown = cv2.inRange(hsv, lower_brown, upper_brown)
            
            lower_green = np.array([35, 50, 50])
            upper_green = np.array([85, 255, 255])
            mask_green = cv2.inRange(hsv, lower_green, upper_green)
            
            color_mask = cv2.bitwise_or(mask_brown, mask_green)
            color_mask = cv2.dilate(color_mask, kernel, iterations=2)
            color_mask = cv2.cvtColor(color_mask, cv2.COLOR_GRAY2RGB)
            enhanced_images.append(color_mask)
            
            # Combina todas as versões com pesos diferentes
            enhanced = enhanced_images[0]
            weights = [0.3, 0.2, 0.2, 0.15, 0.15]  # Ajusta pesos para cada versão
            for img, weight in zip(enhanced_images[1:], weights[1:]):
                enhanced = cv2.addWeighted(enhanced, 1 - weight, img, weight, 0)
            
            # Normalização final
            enhanced = cv2.normalize(enhanced, None, 0, 255, cv2.NORM_MINMAX)
            enhanced = enhanced.astype(np.uint8)
            
            return enhanced
            
        except Exception as e:
            logging.error(f"Erro no realce de imagem: {str(e)}")
            return img_array
    
    def analyze_image(self, image: Image.Image) -> Tuple[Optional[Image.Image], List[Dict]]:
        """Analisa uma imagem em busca de problemas na plantação"""
        try:
            # Verifica se o modelo está carregado
            if self.model is None:
                logging.info("Modelo não carregado. Tentando carregar...")
                if not self.load_model():
                    return None, []
            
            logging.info("Pré-processando imagem...")
            img_array = np.array(image)
            
            # Verifica se a imagem está no formato correto
            if len(img_array.shape) != 3:
                logging.error("Formato de imagem inválido: precisa ser RGB")
                st.error("❌ Formato de imagem inválido: precisa ser RGB")
                return None, []
                
            if img_array.shape[2] != 3:
                logging.error(f"Número incorreto de canais: {img_array.shape[2]}, esperado: 3")
                st.error("❌ Formato de imagem inválido: precisa ser RGB")
                return None, []
            
            # Garante que a imagem está em RGB
            if image.mode != 'RGB':
                image = image.convert('RGB')
                img_array = np.array(image)
            
            enhanced_img = self.enhance_image(img_array)
            
            logging.info("Executando detecção...")
            # Fazer múltiplas detecções com diferentes escalas
            detections = []
            scales = [0.5, 0.75, 1.0, 1.25, 1.5]  # Escalas ajustadas para objetos grandes
            sizes = [640, 832, 1024, 1280]  # Diferentes tamanhos de detecção
            
            for scale in scales:
                logging.debug(f"Testando escala {scale}x")
                if scale != 1.0:
                    h, w = enhanced_img.shape[:2]
                    scaled_img = cv2.resize(enhanced_img, (int(w*scale), int(h*scale)))
                else:
                    scaled_img = enhanced_img
                
                # Executa a detecção com diferentes tamanhos
                try:
                    with torch.no_grad():
                        for size in sizes:
                            results = self.model(scaled_img, size=size, augment=True)
                            
                            # Processa os resultados
                            for pred in results.pred:
                                for *xyxy, conf, cls in pred:
                                    # Ajusta as coordenadas de volta para a escala original
                                    x1, y1, x2, y2 = map(float, xyxy)
                                    if scale != 1.0:
                                        x1, x2 = x1/scale, x2/scale
                                        y1, y2 = y1/scale, y2/scale
                                    
                                    # Extrai a região detectada
                                    roi = img_array[int(y1):int(y2), int(x1):int(x2)]
                                    if roi.size == 0:
                                        continue
                                        
                                    # Calcula características da região
                                    roi_gray = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
                                    roi_hsv = cv2.cvtColor(roi, cv2.COLOR_RGB2HSV)
                                    
                                    # Calcula estatísticas da região
                                    mean_color = np.mean(roi, axis=(0,1))
                                    std_color = np.std(roi, axis=(0,1))
                                    contrast = np.std(roi_gray)
                                    
                                    # Calcula dimensões
                                    width = x2 - x1
                                    height = y2 - y1
                                    aspect_ratio = width / height if height > 0 else 0
                                    area = width * height
                                    img_area = img_array.shape[0] * img_array.shape[1]
                                    area_ratio = area / img_area
                                    
                                    # Filtros para reduzir falsos positivos
                                    is_valid = True
                                    
                                    # 1. Verifica se é um buraco na folha
                                    mean_brightness = np.mean(roi_gray)
                                    if mean_brightness < 30 and contrast < 15:  # Muito escuro e uniforme
                                        is_valid = False
                                        
                                    # 2. Verifica proporções típicas de lagartas
                                    # Mais permissivo com razão de aspecto
                                    if aspect_ratio < 1.2 or aspect_ratio > 8:
                                        is_valid = False
                                        
                                    # 3. Verifica variação de cor
                                    if np.all(std_color < 10):  # Muito uniforme
                                        is_valid = False
                                    
                                    # 4. Verifica textura (lagartas têm textura)
                                    edges = cv2.Canny(roi_gray, 100, 200)
                                    edge_density = np.count_nonzero(edges) / edges.size
                                    if edge_density < 0.01:  # Muito pouca textura
                                        is_valid = False
                                    
                                    # Ajusta confiança baseado nas características
                                    if is_valid:
                                        # Aumenta confiança para objetos com características de lagarta
                                        conf_mult = 1.0
                                        
                                        # Aspecto mais alongado (típico de lagartas)
                                        if 2 < aspect_ratio < 6:
                                            conf_mult *= 1.2
                                            
                                        # Contraste adequado
                                        if 20 < contrast < 120:
                                            conf_mult *= 1.2
                                            
                                        # Tamanho adequado
                                        if 0.005 < area_ratio < 0.3:
                                            conf_mult *= 1.2
                                            
                                        # Textura adequada
                                        if 0.02 < edge_density < 0.2:
                                            conf_mult *= 1.2
                                        
                                        # Cor típica de lagarta (tons de verde, marrom ou amarelo)
                                        mean_hue = np.mean(roi_hsv[:,:,0])
                                        if 20 < mean_hue < 100:  # Faixa de cores típicas
                                            conf_mult *= 1.2
                                        
                                        conf = float(conf * conf_mult)
                                        
                                        label = self.classes[int(cls)]
                                        detections.append({
                                            'box': (x1, y1, x2, y2),
                                            'label': label,
                                            'confidence': conf,
                                            'area_ratio': area_ratio,
                                            'aspect_ratio': aspect_ratio,
                                            'contrast': float(contrast),
                                            'edge_density': float(edge_density),
                                            'size': size,
                                            'scale': scale
                                        })
                                        logging.info(f"Detectado: {label} com confiança {conf:.2f}, "
                                                   f"área {area_ratio:.2%}, razão {aspect_ratio:.1f}, "
                                                   f"contraste {contrast:.1f}, textura {edge_density:.3f}")
                            
                except Exception as e:
                    logging.error(f"Erro na detecção na escala {scale}x: {str(e)}")
                    continue
            
            # Remove detecções duplicadas
            detections = self.remove_duplicates(detections, iou_threshold=0.7)
            
            # Filtra detecções por confiança mínima
            detections = [d for d in detections if d['confidence'] > 0.1]
            
            logging.info(f"Detectados {len(detections)} problemas")
            
            # Desenha as detecções na imagem
            marked_image = self.draw_detections(img_array, detections)
            result_image = Image.fromarray(marked_image)
            
            logging.info("Análise concluída com sucesso")
            return result_image, detections
            
        except Exception as e:
            logging.error(f"Erro na análise da imagem: {str(e)}")
            logging.error(f"Traceback: {traceback.format_exc()}")
            st.error(f"❌ Erro ao analisar imagem: {str(e)}")
            return None, []
    
    def remove_duplicates(self, detections: List[Dict], iou_threshold: float = 0.4) -> List[Dict]:
        """Remove detecções duplicadas baseado no IoU"""
        if not detections:
            return []
            
        # Ordena por confiança
        detections = sorted(detections, key=lambda x: x['confidence'], reverse=True)
        kept_detections = []
        
        for detection in detections:
            should_keep = True
            current_box = detection['box']
            current_label = detection['label']
            
            for kept in kept_detections:
                if kept['label'] != current_label:  # Ignora diferentes tipos de pragas
                    continue
                    
                kept_box = kept['box']
                iou = self.calculate_iou(current_box, kept_box)
                
                if iou > iou_threshold:
                    # Se a detecção atual tem confiança significativamente maior, substitui a anterior
                    if detection['confidence'] > kept['confidence'] * 1.2:  # 20% maior
                        kept_detections.remove(kept)
                    else:
                        should_keep = False
                    break
            
            if should_keep:
                kept_detections.append(detection)
        
        return kept_detections
    
    def calculate_iou(self, box1: Tuple[float, float, float, float], 
                     box2: Tuple[float, float, float, float]) -> float:
        """Calcula IoU entre duas boxes"""
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2
        
        # Calcula área de intersecção
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i < x1_i or y2_i < y1_i:
            return 0.0
            
        intersection = (x2_i - x1_i) * (y2_i - y1_i)
        
        # Calcula áreas
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        
        # Calcula IoU
        union = area1 + area2 - intersection
        return intersection / union if union > 0 else 0.0
    
    def draw_detections(self, image: np.ndarray, detections: List[Dict]) -> np.ndarray:
        """Desenha as detecções na imagem"""
        try:
            img = image.copy()
            for det in detections:
                # Extrai informações da detecção
                box = det['box']
                label = det['label']
                conf = det['confidence']
                aspect_ratio = det.get('aspect_ratio', 0)
                contrast = det.get('contrast', 0)
                area_ratio = det.get('area_ratio', 0)
                edge_density = det.get('edge_density', 0)
                
                # Converte coordenadas para inteiros
                x1, y1, x2, y2 = map(int, box)
                
                # Obtém a cor para este tipo de problema
                color = self.problem_colors.get(label, (255, 255, 255))
                
                # Ajusta a espessura da borda baseado na confiança
                thickness = max(1, int(conf * 5))
                
                # Desenha o retângulo
                cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)
                
                # Prepara o texto com informações detalhadas
                text_lines = [
                    f"{label} ({conf:.1%})",
                    f"AR: {aspect_ratio:.1f}",
                    f"Área: {area_ratio:.1%}",
                    f"Textura: {edge_density:.2f}"
                ]
                
                # Calcula o tamanho total do texto
                text_sizes = [cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0] 
                            for line in text_lines]
                max_width = max(size[0] for size in text_sizes)
                total_height = sum(size[1] for size in text_sizes) + 15  # 15px de padding
                
                # Cria overlay para o texto
                overlay = img.copy()
                cv2.rectangle(overlay, 
                            (x1, y1-total_height-10),
                            (x1+max_width+10, y1),
                            color, -1)
                cv2.addWeighted(overlay, 0.7, img, 0.3, 0, img)
                
                # Adiciona cada linha de texto
                y_offset = y1-total_height
                for line in text_lines:
                    y_offset += 20
                    cv2.putText(img, line,
                              (x1+5, y_offset),
                              cv2.FONT_HERSHEY_SIMPLEX,
                              0.5, (255,255,255), 2)
            
            return img
            
        except Exception as e:
            logging.error(f"Erro ao desenhar detecções: {str(e)}")
            logging.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    def display_analysis(self):
        """Interface para upload e análise de imagens"""
        st.subheader("🔍 Análise de Plantações")
        
        uploaded_file = st.file_uploader(
            "Escolha uma imagem da plantação", 
            type=['png', 'jpg', 'jpeg']
        )
        
        if uploaded_file is not None:
            try:
                logging.info(f"Arquivo carregado: {uploaded_file.name}")
                
                # Exibir imagem original
                image = Image.open(uploaded_file)
                st.image(image, caption="Imagem Original", use_column_width=True)
                
                # Analisar imagem
                if st.button("Analisar Imagem"):
                    with st.spinner("Preparando modelo..."):
                        if self.model is None:
                            if not self.load_model():
                                st.error("❌ Não foi possível carregar o modelo")
                                return
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    try:
                        # Atualiza status
                        status_text.text("🔄 Pré-processando imagem...")
                        progress_bar.progress(25)
                        
                        # Analisar imagem
                        with st.spinner("Analisando imagem..."):
                            result_image, detections = self.analyze_image(image)
                            if result_image:
                                # Mostra resultado
                                status_text.text("✅ Análise concluída!")
                                progress_bar.progress(100)
                                
                                st.image(result_image, caption="Resultado da Análise", 
                                       use_column_width=True)
                                
                                # Exibir métricas
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Problemas Detectados", len(detections))
                                with col2:
                                    conf_media = np.mean([d['confidence'] for d in detections]) if detections else 0
                                    st.metric("Confiança Média", f"{conf_media:.1%}")
                                with col3:
                                    st.metric("Escalas Analisadas", "0.5x, 0.75x, 1.0x, 1.25x, 1.5x")
                                
                                # Exibir detalhes dos problemas
                                if detections:
                                    st.write("### 📋 Detalhes dos Problemas")
                                    for i, det in enumerate(detections, 1):
                                        with st.expander(f"Problema {i}: {det['label'].title()} ({det['confidence']:.1%})"):
                                            st.write(f"**Tipo:** {det['label']}")
                                            st.write(f"**Confiança:** {det['confidence']:.1%}")
                                            st.write(f"**Localização:** x={det['box'][0]:.0f}, y={det['box'][1]:.0f}")
                                            st.write("**Recomendações:**")
                                            recs = self.get_recommendations([det['label']])
                                            for rec in recs:
                                                st.write(f"- {rec}")
                                else:
                                    st.info("✅ Nenhum problema detectado na imagem!")
                        
                        # Limpa elementos temporários
                        status_text.empty()
                        progress_bar.empty()
                        
                    except Exception as e:
                        status_text.text("❌ Erro durante a análise")
                        progress_bar.empty()
                        st.error(f"Erro ao analisar imagem: {str(e)}")
                        logging.error(f"Erro durante análise: {str(e)}")
                        logging.error(f"Traceback: {traceback.format_exc()}")
                
            except Exception as e:
                logging.error(f"Erro no processamento: {str(e)}")
                logging.error(f"Traceback: {traceback.format_exc()}")
                st.error(f"❌ Erro ao processar imagem: {str(e)}")
    
    def get_recommendations(self, problems: list) -> list:
        """Gera recomendações baseadas nos problemas detectados"""
        recommendations = []
        for problem in problems:
            if problem == "lagarta":
                recommendations.extend([
                    "Aplicar Bacillus thuringiensis (Bt)",
                    "Usar armadilhas com feromônios",
                    "Monitorar população de predadores naturais",
                    "Aplicar inseticidas biológicos à base de Bt"
                ])
            elif problem == "pulgão":
                recommendations.extend([
                    "Aplicar óleo de neem",
                    "Introduzir joaninhas como controle biológico", 
                    "Usar inseticidas seletivos se necessário",
                    "Monitorar formigas que protegem os pulgões"
                ])
            elif problem == "percevejo":
                recommendations.extend([
                    "Monitorar com armadilhas luminosas",
                    "Aplicar controle biológico com vespas",
                    "Manter a área livre de plantas hospedeiras",
                    "Usar feromônios para monitoramento"
                ])
            elif problem == "mosca_branca":
                recommendations.extend([
                    "Usar armadilhas adesivas amarelas",
                    "Aplicar óleo de neem",
                    "Controle biológico com fungos",
                    "Eliminar plantas hospedeiras"
                ])
            elif problem == "trips":
                recommendations.extend([
                    "Usar armadilhas adesivas azuis",
                    "Aplicar óleo mineral",
                    "Controle biológico com ácaros predadores",
                    "Manter irrigação adequada"
                ])
            elif problem == "ácaro":
                recommendations.extend([
                    "Aplicar enxofre",
                    "Usar ácaros predadores",
                    "Manter umidade adequada",
                    "Evitar excesso de nitrogênio"
                ])
            elif problem == "cochonilha":
                recommendations.extend([
                    "Poda de partes infestadas",
                    "Aplicar óleo mineral",
                    "Controle biológico com joaninhas",
                    "Monitorar formigas associadas"
                ])
            elif problem == "cigarrinha":
                recommendations.extend([
                    "Usar armadilhas adesivas amarelas",
                    "Aplicar fungos entomopatogênicos",
                    "Manter área livre de plantas daninhas",
                    "Rotação de culturas"
                ])
            elif problem == "broca":
                recommendations.extend([
                    "Usar armadilhas com feromônios",
                    "Controle biológico com vespas",
                    "Eliminar restos culturais",
                    "Manejo cultural adequado"
                ])
            elif problem == "vaquinha":
                recommendations.extend([
                    "Usar armadilhas luminosas",
                    "Aplicar Beauveria bassiana",
                    "Rotação de culturas",
                    "Eliminar plantas hospedeiras"
                ])
        return recommendations 