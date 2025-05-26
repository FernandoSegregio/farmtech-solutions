# run.py
import subprocess
import sys
import time
import os
import logging
import signal
from datetime import datetime

def setup_logging():
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    logging.basicConfig(
        filename=os.path.join(log_dir, f"app_{datetime.now().strftime('%Y%m%d')}.log"),
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def start_mqtt_client():
    # Configura o ambiente Python
    env = os.environ.copy()
    src_path = os.path.abspath("src")
    if 'PYTHONPATH' in env:
        env['PYTHONPATH'] = src_path + os.pathsep + env['PYTHONPATH']
    else:
        env['PYTHONPATH'] = src_path

    mqtt_process = subprocess.Popen([
        sys.executable,
        "-u",  # Força saída sem buffer
        "src/mqtt_client.py"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    
    logging.info("Cliente MQTT iniciado com PID: %d", mqtt_process.pid)
    return mqtt_process

def start_streamlit():
    # Configura o ambiente Python
    env = os.environ.copy()
    src_path = os.path.abspath("src")
    if 'PYTHONPATH' in env:
        env['PYTHONPATH'] = src_path + os.pathsep + env['PYTHONPATH']
    else:
        env['PYTHONPATH'] = src_path

    streamlit_process = subprocess.Popen([
        "streamlit",
        "run",
        "src/app.py"
    ], env=env)
    
    logging.info("Streamlit iniciado com PID: %d", streamlit_process.pid)
    return streamlit_process

def check_process(process, name):
    if process.poll() is not None:
        logging.error(f"{name} parou. Código de saída: {process.poll()}")
        return False
    return True

def run_apps():
    setup_logging()
    mqtt_process = None
    streamlit_process = None
    
    def cleanup(signum, frame):
        logging.info("Recebido sinal de término. Encerrando processos...")
        if mqtt_process:
            mqtt_process.terminate()
        if streamlit_process:
            streamlit_process.terminate()
        sys.exit(0)
    
    # Registra handler para SIGTERM e SIGINT
    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)
    
    try:
        logging.info("Iniciando aplicações...")
        print("🚀 Iniciando FarmTech Solutions...")
        
        # Inicia MQTT Client
        print("📡 Iniciando cliente MQTT...")
        mqtt_process = start_mqtt_client()
        time.sleep(3)  # Aguarda inicialização do MQTT
        
        # Verifica se MQTT iniciou corretamente
        if not check_process(mqtt_process, "Cliente MQTT"):
            out, err = mqtt_process.communicate()
            logging.error(f"Falha ao iniciar cliente MQTT. Saída: {out.decode() if out else ''}")
            logging.error(f"Erro: {err.decode() if err else ''}")
            print("❌ Falha ao iniciar cliente MQTT")
            return
        else:
            print("✅ Cliente MQTT iniciado com sucesso")
            
        # Inicia Streamlit
        print("🌐 Iniciando dashboard Streamlit...")
        streamlit_process = start_streamlit()
        time.sleep(2)
        
        if check_process(streamlit_process, "Streamlit"):
            print("✅ Dashboard iniciado com sucesso")
            print("🌱 FarmTech Solutions está rodando!")
            print("📊 Acesse o dashboard em: http://localhost:8501")
        
        # Loop principal de monitoramento
        while True:
            # Verifica MQTT
            if not check_process(mqtt_process, "Cliente MQTT"):
                out, err = mqtt_process.communicate()
                logging.error(f"Cliente MQTT parou. Saída: {out.decode() if out else ''}")
                logging.error(f"Erro: {err.decode() if err else ''}")
                
                print("🔄 Reiniciando cliente MQTT...")
                logging.info("Reiniciando cliente MQTT...")
                mqtt_process.terminate()
                mqtt_process = start_mqtt_client()
                time.sleep(3)
            
            # Verifica Streamlit
            if not check_process(streamlit_process, "Streamlit"):
                print("🔄 Reiniciando Streamlit...")
                logging.info("Reiniciando Streamlit...")
                streamlit_process.terminate()
                streamlit_process = start_streamlit()
                time.sleep(2)
            
            time.sleep(10)  # Verifica a cada 10 segundos
            
    except KeyboardInterrupt:
        print("\n🛑 Encerrando FarmTech Solutions...")
        logging.info("Interrupção do usuário detectada...")
    except Exception as e:
        print(f"❌ Erro: {e}")
        logging.error(f"Erro: {e}")
    finally:
        logging.info("Encerrando aplicações...")
        if mqtt_process:
            mqtt_process.terminate()
        if streamlit_process:
            streamlit_process.terminate()
        print("👋 FarmTech Solutions encerrado")

if __name__ == "__main__":
    # Garante que estamos no diretório raiz do projeto
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)
    
    run_apps()