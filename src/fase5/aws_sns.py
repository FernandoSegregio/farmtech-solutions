"""
Gerenciador de AWS SNS para o sistema de alertas
"""
import boto3
import logging
from typing import List, Dict, Optional
import os
from pathlib import Path
import json
from dotenv import load_dotenv
from botocore.exceptions import ClientError

# Configura logging mais detalhado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

class SNSManager:
    def __init__(self):
        # Verifica se as variáveis de ambiente necessárias estão definidas
        required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SNS_TOPIC_ARN', 'AWS_DEFAULT_REGION']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ValueError(
                f"Variáveis de ambiente necessárias não encontradas: {', '.join(missing_vars)}\n"
                "Por favor, crie um arquivo .env com as variáveis necessárias."
            )
        
        try:
            self.sns = boto3.client(
                'sns',
                region_name=os.getenv('AWS_DEFAULT_REGION'),
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
            )
            self.topic_arn = os.getenv('AWS_SNS_TOPIC_ARN')
            
            # Verifica se o tópico existe
            try:
                self.sns.get_topic_attributes(TopicArn=self.topic_arn)
                logging.info(f"Conectado ao tópico SNS: {self.topic_arn}")
            except ClientError as e:
                if e.response['Error']['Code'] == 'NotFound':
                    raise ValueError(f"Tópico SNS não encontrado: {self.topic_arn}")
                elif e.response['Error']['Code'] == 'InvalidParameter':
                    raise ValueError(f"ARN do tópico SNS inválido: {self.topic_arn}")
                else:
                    raise
            
            self.load_config()
            
        except Exception as e:
            logging.error(f"Erro ao inicializar SNS: {str(e)}")
            raise
    
    def load_config(self):
        """Carrega ou cria a configuração do SNS"""
        config_dir = Path(__file__).parent.parent.parent / "config"
        config_dir.mkdir(exist_ok=True)
        self.config_file = config_dir / "sns_config.json"
        
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {
                'topic_arn': self.topic_arn,
                'subscriptions': {}
            }
            self.save_config()
    
    def save_config(self):
        """Salva a configuração do SNS"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def get_subscriptions(self) -> List[Dict]:
        """Obtém todas as inscrições do tópico SNS"""
        try:
            subscriptions = []
            paginator = self.sns.get_paginator('list_subscriptions_by_topic')
            
            for page in paginator.paginate(TopicArn=self.topic_arn):
                for sub in page['Subscriptions']:
                    if sub['Protocol'] == 'email':
                        subscriptions.append({
                            'email': sub['Endpoint'],
                            'arn': sub['SubscriptionArn'],
                            'status': 'Confirmado' if sub['SubscriptionArn'] != 'PendingConfirmation' else 'Aguardando confirmação'
                        })
            
            logging.info(f"Inscrições encontradas: {len(subscriptions)}")
            for sub in subscriptions:
                logging.info(f"Inscrição: {sub['email']} - Status: {sub['status']}")
            
            # Atualiza o cache local
            self.config['subscriptions'] = {
                sub['email']: {
                    'arn': sub['arn'],
                    'status': sub['status']
                }
                for sub in subscriptions
            }
            self.save_config()
            
            return subscriptions
            
        except Exception as e:
            logging.error(f"Erro ao obter inscrições SNS: {str(e)}")
            return []
    
    def subscribe_email(self, email: str) -> bool:
        """Inscreve um email no tópico SNS"""
        try:
            logging.info(f"Tentando inscrever email: {email}")
            
            # Verifica se o email já está inscrito
            subscriptions = self.get_subscriptions()
            for sub in subscriptions:
                if sub['email'] == email:
                    logging.warning(f"Email {email} já está inscrito com status: {sub['status']}")
                    return False
            
            response = self.sns.subscribe(
                TopicArn=self.topic_arn,
                Protocol='email',
                Endpoint=email,
                ReturnSubscriptionArn=True
            )
            
            logging.info(f"Resposta da inscrição: {response}")
            
            # Atualiza o cache local
            self.config['subscriptions'][email] = {
                'arn': response['SubscriptionArn'],
                'status': 'Aguardando confirmação'
            }
            self.save_config()
            
            logging.info(f"Email {email} inscrito com sucesso. Aguardando confirmação.")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logging.error(f"Erro AWS ao inscrever email: {error_code} - {error_message}")
            return False
        except Exception as e:
            logging.error(f"Erro ao inscrever email no SNS: {str(e)}")
            return False
    
    def unsubscribe_email(self, email: str) -> bool:
        """Remove a inscrição de um email do tópico SNS"""
        try:
            if email in self.config['subscriptions']:
                subscription_arn = self.config['subscriptions'][email]['arn']
                
                if subscription_arn != 'PendingConfirmation':
                    self.sns.unsubscribe(
                        SubscriptionArn=subscription_arn
                    )
                    logging.info(f"Email {email} removido com sucesso")
                else:
                    logging.info(f"Email {email} removido (estava pendente)")
                
                # Remove do cache local
                del self.config['subscriptions'][email]
                self.save_config()
                
                return True
                
        except Exception as e:
            logging.error(f"Erro ao remover inscrição SNS: {str(e)}")
        
        return False
    
    def is_email_subscribed(self, email: str) -> bool:
        """Verifica se um email já está inscrito"""
        return email in self.config['subscriptions']
    
    def get_subscription_status(self, email: str) -> Optional[str]:
        """Obtém o status de inscrição de um email"""
        if email in self.config['subscriptions']:
            return self.config['subscriptions'][email]['status']
        return None
    
    def publish_test_message(self) -> bool:
        """Publica uma mensagem de teste no tópico"""
        try:
            logging.info("Enviando mensagem de teste...")
            response = self.sns.publish(
                TopicArn=self.topic_arn,
                Subject='Teste de Alerta FarmTech',
                Message='Este é um teste do sistema de alertas do FarmTech Solutions.'
            )
            logging.info(f"Mensagem de teste enviada: {response['MessageId']}")
            return True
        except Exception as e:
            logging.error(f"Erro ao publicar mensagem de teste: {str(e)}")
            return False
    
    def publish_message(self, subject: str, message: str) -> bool:
        """Publica uma mensagem personalizada no tópico"""
        try:
            logging.info(f"Enviando mensagem: {message}")
            response = self.sns.publish(
                TopicArn=self.topic_arn,
                Subject=subject,
                Message=message
            )
            logging.info(f"Mensagem enviada: {response['MessageId']}")
            return True
        except Exception as e:
            logging.error(f"Erro ao publicar mensagem: {str(e)}")
            return False 