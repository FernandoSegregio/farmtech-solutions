"""
Script para configurar o modelo YOLOv5 para detecção de pragas
"""
import torch
import os
from pathlib import Path
import yaml
import logging
import requests
from tqdm import tqdm
import shutil

def setup_logging():
    """Configura o sistema de logs"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def download_file(url: str, dest_path: str):
    """Download de arquivo com barra de progresso"""
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    with open(dest_path, 'wb') as file, tqdm(
        desc=dest_path,
        total=total_size,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as pbar:
        for data in response.iter_content(chunk_size=1024):
            size = file.write(data)
            pbar.update(size)

def setup_model():
    """Configura o modelo YOLOv5 para detecção de pragas"""
    try:
        setup_logging()
        logging.info("Iniciando configuração do modelo...")
        
        # Limpa o cache do torch hub
        cache_dir = Path.home() / '.cache' / 'torch' / 'hub'
        if cache_dir.exists():
            logging.info("Limpando cache do torch hub...")
            shutil.rmtree(str(cache_dir))
        
        # Cria diretório models se não existir
        models_dir = Path(__file__).parent.parent / "models"
        models_dir.mkdir(exist_ok=True)
        
        # Baixa modelo pré-treinado YOLOv5s
        model_path = models_dir / "yolov5_pests.pt"
        
        logging.info("Carregando modelo YOLOv5s pré-treinado...")
        model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True, force_reload=True, trust_repo=True)
        
        # Configura as classes
        model.names = {
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
        
        # Configura parâmetros
        model.conf = 0.01  # confidence threshold muito baixo para capturar todas as possíveis detecções
        model.iou = 0.7   # IoU alto para evitar duplicatas
        model.max_det = 100  # máximo de detecções por imagem
        model.agnostic = True  # NMS class-agnostic
        model.classes = [0]  # Apenas detecta lagartas (classe 0)
        
        # Ajusta parâmetros do modelo para melhor detecção de lagartas grandes
        try:
            # Tenta ajustar os parâmetros do modelo de diferentes formas
            if hasattr(model, 'model') and hasattr(model.model, 'model'):
                # Versão antiga do YOLOv5
                detection_layer = model.model.model[-1]
                if hasattr(detection_layer, 'anchors'):
                    detection_layer.anchors = torch.tensor([
                        [10, 13], [16, 30], [33, 23],  # P3/8
                        [30, 61], [62, 45], [59, 119],  # P4/16
                        [116, 90], [156, 198], [373, 326]  # P5/32
                    ])
                    detection_layer.stride = torch.tensor([8., 16., 32.])
            elif hasattr(model, 'model'):
                # Nova versão do YOLOv5
                for m in model.model.modules():
                    if hasattr(m, 'anchors'):
                        m.anchors = torch.tensor([
                            [10, 13], [16, 30], [33, 23],
                            [30, 61], [62, 45], [59, 119],
                            [116, 90], [156, 198], [373, 326]
                        ], device=m.anchors.device)
                        if hasattr(m, 'stride'):
                            m.stride = torch.tensor([8., 16., 32.], device=m.stride.device)
            
            logging.info("✅ Parâmetros do modelo ajustados com sucesso")
        except Exception as e:
            logging.warning(f"⚠️ Não foi possível ajustar alguns parâmetros do modelo: {str(e)}")
            logging.warning("O modelo ainda funcionará, mas pode ter performance reduzida para lagartas grandes")
        
        # Salva modelo configurado
        logging.info("Salvando modelo configurado...")
        torch.save({
            'model_state_dict': model.state_dict(),
            'names': model.names,
            'conf': model.conf,
            'iou': model.iou,
            'max_det': model.max_det,
            'agnostic': model.agnostic,
            'classes': model.classes
        }, model_path)
        
        logging.info("✅ Modelo configurado com sucesso!")
        
    except Exception as e:
        logging.error(f"❌ Erro na configuração do modelo: {str(e)}")
        logging.error("Stacktrace:", exc_info=True)
        raise

if __name__ == "__main__":
    setup_model() 