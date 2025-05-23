"""
Manipulador MQTT para a Fase 4
"""
import paho.mqtt.client as mqtt
import ssl
import streamlit as st
from dotenv import load_dotenv
import os
import logging

class MQTTHandler:
    def __init__(self):
        load_dotenv()
        
        # Configurações MQTT
        self.mqtt_server = os.getenv('MQTT_SERVER', "91c5f1ea0f494ccebe45208ea8ffceff.s1.eu.hivemq.cloud")
        self.mqtt_port = int(os.getenv('MQTT_PORT', 8883))
        self.mqtt_user = os.getenv('MQTT_USER', "FARM_TECH")
        self.mqtt_password = os.getenv('MQTT_PASSWORD', "Pato1234")
        self.humidity_topic = os.getenv('MQTT_HUMIDITY_TOPIC', "sensor/umidade")
        self.pump_topic = os.getenv('MQTT_PUMP_TOPIC', "sensor/bomba")
        
        # Configuração de logging
        logging.basicConfig(
            filename='mqtt.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Inicialização do cliente MQTT
        self.client = mqtt.Client()
        self.setup_client()
        
    def setup_client(self):
        """Configura o cliente MQTT"""
        try:
            self.client.username_pw_set(self.mqtt_user, self.mqtt_password)
            self.client.tls_set(cert_reqs=ssl.CERT_NONE)
            self.client.connect(self.mqtt_server, self.mqtt_port, 60)
            self.client.loop_start()
            logging.info("Cliente MQTT conectado com sucesso")
        except Exception as e:
            logging.error(f"Erro ao conectar cliente MQTT: {e}")
            st.error(f"Erro ao conectar ao broker MQTT: {e}")
    
    def ligar_bomba_agua(self):
        """Liga a bomba de água"""
        try:
            self.client.publish(self.pump_topic, "ON")
            st.success("Comando enviado para ligar a bomba de água.")
            logging.info("Bomba de água ligada")
        except Exception as e:
            logging.error(f"Erro ao ligar bomba: {e}")
            st.error(f"Erro ao enviar comando para bomba: {e}")
    
    def desligar_bomba_agua(self):
        """Desliga a bomba de água"""
        try:
            self.client.publish(self.pump_topic, "OFF")
            st.success("Comando enviado para desligar a bomba de água.")
            logging.info("Bomba de água desligada")
        except Exception as e:
            logging.error(f"Erro ao desligar bomba: {e}")
            st.error(f"Erro ao enviar comando para bomba: {e}")
    
    def stop(self):
        """Para o cliente MQTT"""
        try:
            self.client.loop_stop()
            self.client.disconnect()
            logging.info("Cliente MQTT desconectado")
        except Exception as e:
            logging.error(f"Erro ao desconectar cliente MQTT: {e}") 