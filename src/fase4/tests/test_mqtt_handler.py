"""
Testes para o manipulador MQTT
"""
import unittest
from unittest.mock import Mock, patch
from ..mqtt_handler import MQTTHandler

class TestMQTTHandler(unittest.TestCase):
    def setUp(self):
        self.mqtt_handler = MQTTHandler()
    
    @patch('paho.mqtt.client.Client')
    def test_ligar_bomba_agua(self, mock_client):
        self.mqtt_handler.client = mock_client
        self.mqtt_handler.ligar_bomba_agua()
        mock_client.publish.assert_called_once_with(self.mqtt_handler.pump_topic, "ON")
    
    @patch('paho.mqtt.client.Client')
    def test_desligar_bomba_agua(self, mock_client):
        self.mqtt_handler.client = mock_client
        self.mqtt_handler.desligar_bomba_agua()
        mock_client.publish.assert_called_once_with(self.mqtt_handler.pump_topic, "OFF") 