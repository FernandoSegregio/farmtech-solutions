import os
import paho.mqtt.client as mqtt
import ssl
import oracledb
import json
from dotenv import load_dotenv
from datetime import datetime
import streamlit as st
from fase5.alerts import AlertSystem
import time
import logging

# Configurações do HiveMQ Cloud
mqtt_server = "91c5f1ea0f494ccebe45208ea8ffceff.s1.eu.hivemq.cloud"
mqtt_port = 8883
mqtt_user = "FARM_TECH"
mqtt_password = "Pato1234"

# Tópicos MQTT
humidity_topic = "sensor/umidade"
temperature_topic = "sensor/temperatura"
pump_topic = "sensor/bomba"
ph_sensor = "sensor/ph"
k_button_topic = "sensor/potassio"
p_button_topic = "sensor/sodio"

# Carrega as variáveis de ambiente para o banco de dados
load_dotenv()
db_user = os.getenv('DB_USER') or st.secrets["database"]["user"]
db_password = os.getenv('DB_PASSWORD') or st.secrets["database"]["password"] 
db_dsn = os.getenv('DB_DSN') or st.secrets["database"]["dsn"]

# Configuração de logging
if not os.path.exists('logs'):
    os.makedirs('logs')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/mqtt.log'),
        logging.StreamHandler()  # Também mostra no console
    ]
)

def conectar_banco():
    try:
        conn = oracledb.connect(user=db_user, password=db_password, dsn=db_dsn)
        logging.info("Conectado ao banco de dados Oracle.")
        return conn
    except oracledb.DatabaseError as e:
        logging.error(f"Erro ao conectar ao banco de dados: {e}")
        return None

def verificar_ou_inserir_sensor_umidade(conn, id_sensor):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sensor_umidade WHERE id_sensor_umidade = :id_sensor", {'id_sensor': id_sensor})
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO sensor_umidade (id_sensor_umidade) VALUES (:id_sensor)", {'id_sensor': id_sensor})
        conn.commit()
        logging.info(f"Sensor de umidade {id_sensor} inserido com sucesso.")
    cursor.close()

def verificar_ou_inserir_sensor_ph(conn, id_sensor):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sensor_ph WHERE id_sensor_ph = :id_sensor", {'id_sensor': id_sensor})
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO sensor_ph (id_sensor_ph) VALUES (:id_sensor)", {'id_sensor': id_sensor})
        conn.commit()
        logging.info(f"Sensor de pH {id_sensor} inserido com sucesso.")
    cursor.close()

def inserir_leitura_umidade(conn, id_sensor, data_leitura, hora_leitura, valor_umidade):
    verificar_ou_inserir_sensor_umidade(conn, id_sensor)
    cursor = conn.cursor()
    try:
        # Tenta primeiro com formato HH:MM:SS, depois HH:MM
        try:
            data_hora_leitura = datetime.strptime(f"{data_leitura} {hora_leitura}", '%Y-%m-%d %H:%M:%S')
        except ValueError:
            data_hora_leitura = datetime.strptime(f"{data_leitura} {hora_leitura}:00", '%Y-%m-%d %H:%M:%S')
        
        umidade_formatada = round(float(valor_umidade), 2)

        cursor.execute("""
            INSERT INTO LEITURA_SENSOR_UMIDADE 
            (id_leitura_umidade, id_sensor_umidade, data_leitura, hora_leitura, valor_umidade_leitura)
            VALUES 
            (LEITURA_SENSOR_UMIDADE_SEQ.NEXTVAL, :id_sensor, :data_leitura, :hora_leitura, :valor_umidade)
        """, {
            'id_sensor': id_sensor,
            'data_leitura': data_hora_leitura.date(),
            'hora_leitura': data_hora_leitura,
            'valor_umidade': umidade_formatada
        })
        conn.commit()
        logging.info(f"✅ Leitura de umidade inserida: {umidade_formatada}%")
    except Exception as e:
        logging.error(f"Erro ao inserir dados de umidade: {e}")
        conn.rollback()
    finally:
        cursor.close()

def inserir_leitura_ph(conn, id_sensor, data_leitura, hora_leitura, ph_equivalente):
    verificar_ou_inserir_sensor_ph(conn, id_sensor)
    cursor = conn.cursor()
    try:
        # Tenta primeiro com formato HH:MM:SS, depois HH:MM
        try:
            data_hora_leitura = datetime.strptime(f"{data_leitura} {hora_leitura}", '%Y-%m-%d %H:%M:%S')
        except ValueError:
            data_hora_leitura = datetime.strptime(f"{data_leitura} {hora_leitura}:00", '%Y-%m-%d %H:%M:%S')
        
        ph_formatado = round(float(ph_equivalente), 2)

        cursor.execute("""
            INSERT INTO LEITURA_SENSOR_PH 
            (id_leitura_ph, id_sensor_ph, data_leitura, hora_leitura, valor_ph_leitura)
            VALUES 
            (LEITURA_SENSOR_PH_SEQ.NEXTVAL, :id_sensor, :data_leitura, :hora_leitura, :valor_ph)
        """, {
            'id_sensor': id_sensor,
            'data_leitura': data_hora_leitura.date(),
            'hora_leitura': data_hora_leitura,
            'valor_ph': ph_formatado
        })
        conn.commit()
        logging.info(f"✅ Leitura de pH inserida: {ph_formatado}")
    except Exception as e:
        logging.error(f"Erro ao inserir dados de pH: {e}")
        conn.rollback()
    finally:
        cursor.close()

def inserir_leitura_temperatura(conn, id_sensor, data_leitura, hora_leitura, temperatura):
    verificar_ou_inserir_sensor_umidade(conn, id_sensor)
    cursor = conn.cursor()
    try:
        data_leitura_formatada = datetime.strptime(data_leitura, '%Y-%m-%d').date()
        
        # Tenta primeiro com formato HH:MM:SS, depois HH:MM
        try:
            hora_leitura_formatada = datetime.strptime(hora_leitura, '%H:%M:%S')
        except ValueError:
            hora_leitura_formatada = datetime.strptime(f"{hora_leitura}:00", '%H:%M:%S')
        
        temperatura_formatada = round(float(temperatura), 2)

        cursor.execute("""
            INSERT INTO leitura_sensor_temperatura 
            (id_sensor_umidade, data_leitura, hora_leitura, valor_temperatura, limite_minimo_temperatura, limite_maximo_temperatura)
            VALUES (:id_sensor, :data_leitura, :hora_leitura, :valor_temperatura, :limite_minimo, :limite_maximo)
        """, {
            'id_sensor': id_sensor,
            'data_leitura': data_leitura_formatada,
            'hora_leitura': hora_leitura_formatada,
            'valor_temperatura': temperatura_formatada,
            'limite_minimo': 12.00,
            'limite_maximo': 36.00
        })
        conn.commit()
        logging.info(f"✅ Leitura de temperatura inserida: {temperatura_formatada}°C")
    except Exception as e:
        logging.error(f"Erro ao inserir dados de temperatura: {e}")
        conn.rollback()
    finally:
        cursor.close()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("🟢 CONECTADO AO BROKER MQTT COM SUCESSO!")
        logging.info("🟢 Conectado ao broker MQTT com sucesso!")
        
        # Inscreve em todos os tópicos
        topics = [
            (humidity_topic, 1),  # sensor/umidade - onde o ESP32 está enviando tudo
            (temperature_topic, 1),
            (ph_sensor, 1),
            (pump_topic, 1),
            (k_button_topic, 1),
            (p_button_topic, 1),
            ("sensor/status", 1),
            ("sensor/+", 1)  # Wildcard para capturar qualquer tópico sensor/*
        ]
        
        for topic, qos in topics:
            result = client.subscribe(topic, qos)
            print(f"📡 INSCRITO NO TÓPICO: {topic} (QoS: {qos})")
            logging.info(f"📡 Inscrito no tópico: {topic} (QoS: {qos}) - Resultado: {result}")
            
        print("🎯 AGUARDANDO MENSAGENS...")
            
    else:
        print(f"❌ FALHA NA CONEXÃO MQTT. CÓDIGO: {rc}")
        logging.error(f"❌ Falha na conexão MQTT. Código: {rc}")

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload_str = msg.payload.decode()
        
        # CONSOLE LOG DESTACADO
        print("=" * 60)
        print(f"🚨 MENSAGEM MQTT RECEBIDA!")
        print(f"📍 TÓPICO: {topic}")
        print(f"📦 PAYLOAD: {payload_str}")
        print("=" * 60)
        
        logging.info(f"📨 Mensagem recebida no tópico '{topic}': {payload_str}")
        
        # Trata mensagens da bomba que não são JSON
        if topic == pump_topic:
            print(f"💧 COMANDO DA BOMBA: {payload_str}")
            logging.info(f"💧 Comando da bomba: {payload_str}")
            return
        
        # Tenta fazer parse do JSON apenas para outros tópicos
        try:
            payload = json.loads(payload_str)
        except json.JSONDecodeError:
            print(f"⚠️ PAYLOAD NÃO É JSON VÁLIDO: {payload_str}")
            logging.warning(f"⚠️ Payload não é JSON válido: {payload_str}")
            return
        
        # Verifica se é uma mensagem de status
        if topic == "sensor/status":
            print(f"📊 STATUS DO DISPOSITIVO: {payload['status']}")
            logging.info(f"📊 Status do dispositivo: {payload['status']}")
            return
            
        conn = conectar_banco()
        if conn:
            try:
                # Processa baseado no ID do sensor, não no tópico
                id_sensor = payload.get("id_sensor")
                data_leitura = payload.get("data_leitura")
                hora_leitura = payload.get("hora_leitura")
                valor = payload.get("Valor")

                if all([id_sensor, data_leitura, hora_leitura, valor]):
                    # ID 1 = Umidade
                    if id_sensor == 1:
                        print(f"💧 PROCESSANDO UMIDADE: {valor}%")
                        inserir_leitura_umidade(conn, id_sensor, data_leitura, hora_leitura, valor)
                        
                        # Controle da bomba
                        umidade_float = float(valor)
                        if umidade_float > 50:
                            client.publish(pump_topic, "OFF", qos=1, retain=True)
                            print("💧 BOMBA DESLIGADA - Umidade alta")
                            logging.info("💧 Bomba DESLIGADA - Umidade alta")
                        else:
                            client.publish(pump_topic, "ON", qos=1, retain=True)
                            print("💧 BOMBA LIGADA - Umidade baixa")
                            logging.info("💧 Bomba LIGADA - Umidade baixa")
                    
                    # ID 2 = Temperatura
                    elif id_sensor == 2:
                        print(f"🌡️ PROCESSANDO TEMPERATURA: {valor}°C")
                        inserir_leitura_temperatura(conn, id_sensor, data_leitura, hora_leitura, valor)
                    
                    # ID 3 = pH
                    elif id_sensor == 3:
                        print(f"🧪 PROCESSANDO PH: {valor}")
                        inserir_leitura_ph(conn, id_sensor, data_leitura, hora_leitura, valor)
                    
                    else:
                        print(f"⚠️ ID SENSOR DESCONHECIDO: {id_sensor}")
                        logging.warning(f"⚠️ ID sensor desconhecido: {id_sensor}")

            finally:
                conn.close()
                
    except Exception as e:
        print(f"❌ ERRO AO PROCESSAR MENSAGEM: {e}")
        logging.error(f"❌ Erro ao processar mensagem MQTT: {e}")
        if 'conn' in locals():
            conn.close()

def on_disconnect(client, userdata, rc):
    if rc != 0:
        print(f"⚠️ DESCONECTADO INESPERADAMENTE! CÓDIGO: {rc}")
        logging.warning(f"⚠️ Desconectado inesperadamente do broker. Código: {rc}")
    else:
        print("🔴 DESCONECTADO DO BROKER MQTT")
        logging.info("🔴 Desconectado do broker MQTT")

def main():
    print("🚀 INICIANDO CLIENTE MQTT...")
    logging.info("🚀 Iniciando cliente MQTT...")
    
    # Configuração do cliente MQTT
    client = mqtt.Client(
        client_id=f"FarmTech_Client_{int(time.time())}",
        clean_session=True
    )
    
    client.username_pw_set(mqtt_user, mqtt_password)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    # Configuração TLS
    client.tls_set(cert_reqs=ssl.CERT_NONE, tls_version=ssl.PROTOCOL_TLSv1_2)
    client.tls_insecure_set(True)
    
    try:
        print(f"🔗 CONECTANDO AO BROKER {mqtt_server}:{mqtt_port}...")
        logging.info(f"🔗 Conectando ao broker {mqtt_server}:{mqtt_port}...")
        client.connect(mqtt_server, mqtt_port, keepalive=60)
        
        # Inicia o loop
        client.loop_forever()
        
    except KeyboardInterrupt:
        print("🛑 CLIENTE MQTT ENCERRADO PELO USUÁRIO")
        logging.info("🛑 Cliente MQTT encerrado pelo usuário")
        client.disconnect()
    except Exception as e:
        print(f"❌ ERRO NO CLIENTE MQTT: {e}")
        logging.error(f"❌ Erro no cliente MQTT: {e}")
        client.disconnect()

if __name__ == "__main__":
    main()
