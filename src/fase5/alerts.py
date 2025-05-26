"""
Sistema de Alertas para monitoramento de condições críticas
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import logging
from typing import List, Dict
from pathlib import Path
import json
import re
from fase5.aws_sns import SNSManager

class AlertSystem:
    def __init__(self):
        self.alerts = []
        self.sns_manager = SNSManager()
        self.setup_logging()
        # Controle de spam de emails
        self.last_email_sent = {}  # Armazena timestamp do último email por tipo
        self.email_cooldown = 300  # 5 minutos entre emails do mesmo tipo
        self.last_alert_state = {}  # Armazena último estado para detectar mudanças
    
    def setup_logging(self):
        """Configura o sistema de logs"""
        log_dir = Path(__file__).parent.parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            filename=str(log_dir / 'alerts.log'),
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def is_valid_email(self, email: str) -> bool:
        """Valida o formato do email"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def add_recipient(self, email: str) -> bool:
        """Adiciona um novo destinatário"""
        if not self.is_valid_email(email):
            st.error("❌ Formato de email inválido!")
            return False
        
        # Tenta inscrever o email no SNS
        if self.sns_manager.subscribe_email(email):
            st.success(f"✅ Email {email} inscrito! Por favor, verifique sua caixa de entrada para confirmar a inscrição.")
            return True
        else:
            st.error("❌ Erro ao inscrever email. Verifique os logs para mais detalhes.")
            return False
    
    def remove_recipient(self, email: str):
        """Remove um destinatário"""
        if self.sns_manager.unsubscribe_email(email):
            st.success(f"✅ Email {email} removido com sucesso!")
        else:
            st.error("❌ Erro ao remover email. Verifique os logs para mais detalhes.")
    
    def test_sns_alert(self):
        """Testa o envio de alerta via SNS"""
        if self.sns_manager.publish_test_message():
            st.success("✅ Alerta de teste enviado com sucesso!")
        else:
            st.error("❌ Erro ao enviar alerta de teste!")
    
    def check_humidity_alert(self, humidity: float, logger=None) -> bool:
        """Verifica se a umidade está em níveis críticos"""
        alert_type = "humidity"
        current_state = None
        
        if humidity < 45:
            current_state = "low"
            message = f"Umidade muito baixa: {humidity:.1f}%"
        elif humidity > 55:
            current_state = "high"
            message = f"Umidade muito alta: {humidity:.1f}%"
        else:
            current_state = "normal"
            # Se voltou ao normal, limpa o estado anterior
            if alert_type in self.last_alert_state:
                del self.last_alert_state[alert_type]
            return False
        
        # Verifica se houve mudança de estado ou se passou tempo suficiente
        should_send_email = self._should_send_email(alert_type, current_state)
        
        if current_state != "normal":
            self.create_alert("CRÍTICO", message, logger, send_email=should_send_email)
            return True
        
        return False
    
    def check_weather_alert(self, rain_probability: float, logger=None) -> bool:
        """Verifica se há alerta de chuva"""
        if rain_probability > 70:
            self.create_alert("ATENÇÃO", f"Alta probabilidade de chuva: {rain_probability:.1f}%", logger)
            return True
        return False
    
    def _should_send_email(self, alert_type: str, current_state: str) -> bool:
        """Verifica se deve enviar email baseado no estado anterior e tempo"""
        now = datetime.now()
        
        # Verifica se houve mudança de estado
        if alert_type in self.last_alert_state:
            if self.last_alert_state[alert_type] == current_state:
                # Mesmo estado - verifica cooldown
                if alert_type in self.last_email_sent:
                    time_since_last = (now - self.last_email_sent[alert_type]).total_seconds()
                    if time_since_last < self.email_cooldown:
                        return False  # Ainda no cooldown
                else:
                    return True  # Primeiro email deste estado
            else:
                # Mudança de estado - sempre envia
                self.last_alert_state[alert_type] = current_state
                return True
        else:
            # Primeiro alerta deste tipo
            self.last_alert_state[alert_type] = current_state
            return True
        
        return True
    
    def create_alert(self, level: str, message: str, logger=None, send_email: bool = True, sensor_origem=None, valor_sensor=None):
        """Cria um novo alerta"""
        alert = {
            'timestamp': datetime.now(),
            'level': level,
            'message': message
        }
        self.alerts.append(alert)
        
        # Salva no banco de dados
        self._save_alert_to_database(level, message, sensor_origem, valor_sensor, send_email)
        
        # Se for um alerta crítico E deve enviar email, envia por SNS
        if level == "CRÍTICO" and send_email:
            # Formata a mensagem com mais detalhes
            subject = f"{message.split(':')[0]} - FarmTech"
            
            # Extrai informações da mensagem
            if "umidade" in message.lower():
                umidade = re.search(r'(\d+\.?\d*)%', message).group(1) if re.search(r'(\d+\.?\d*)%', message) else "N/A"
                detailed_message = f"""🚨 Alerta de Umidade Crítica

📊 Detalhes do Alerta:
- Tipo: {'Umidade Baixa' if 'baixa' in message else 'Umidade Alta'}
- Valor: {umidade}%
- Timestamp: {alert['timestamp'].strftime('%d/%m/%Y %H:%M:%S')}

⚠️ Ação necessária: Verificar sistema de irrigação.

Este é um alerta automático do sistema FarmTech Solutions."""
            else:
                detailed_message = f"""🚨 Alerta do Sistema FarmTech

📊 Detalhes:
- Mensagem: {message}
- Timestamp: {alert['timestamp'].strftime('%d/%m/%Y %H:%M:%S')}

Este é um alerta automático do sistema FarmTech Solutions."""
            
            self.sns_manager.publish_message(subject, detailed_message)
            
            # Atualiza timestamp do último email enviado
            alert_type = "humidity" if "umidade" in message.lower() else "general"
            self.last_email_sent[alert_type] = alert['timestamp']
            
            log_message = f"📧 Email enviado - Alerta criado: {level} - {message}"
        else:
            log_message = f"Alerta criado (sem email): {level} - {message}"
        
        if logger:
            logger.info(log_message)
        logging.info(log_message)
    
    def _save_alert_to_database(self, level: str, message: str, sensor_origem=None, valor_sensor=None, email_enviado=False):
        """Salva o alerta no banco de dados (funcionalidade desabilitada temporariamente)"""
        # Funcionalidade temporariamente desabilitada
        # Os alertas são mantidos apenas em memória por enquanto
        logging.info(f"Alerta registrado em memória: {level} - {message}")
    
    def display_alerts(self):
        """Exibe os alertas no dashboard"""
        st.title("Sistema de Alertas")
        
        # Configurações de Email
        with st.expander("⚙️ Configurações de Email", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                cooldown_minutes = st.slider(
                    "Intervalo entre emails (minutos):",
                    min_value=1,
                    max_value=60,
                    value=int(self.email_cooldown / 60),
                    help="Tempo mínimo entre emails do mesmo tipo de alerta"
                )
                if st.button("Aplicar Configuração"):
                    self.email_cooldown = cooldown_minutes * 60
                    st.success(f"Intervalo configurado para {cooldown_minutes} minutos")
            
            with col2:
                st.write("**Status dos Alertas:**")
                if self.last_alert_state:
                    for alert_type, state in self.last_alert_state.items():
                        st.write(f"• {alert_type.title()}: {state}")
                else:
                    st.write("Nenhum alerta ativo")
        
        # Botão de teste SNS
        if st.button("Testar Alerta SNS", type="primary", use_container_width=True):
            self.test_sns_alert()
        
        # Gerenciador de Destinatários
        st.subheader("📧 Gerenciador de Destinatários")
        
        # Adicionar novo destinatário
        with st.form("novo_destinatario"):
            email = st.text_input("Adicionar novo destinatário de email:")
            submitted = st.form_submit_button("Adicionar Destinatário", use_container_width=True)
            
            if submitted and email:
                self.add_recipient(email)
        
        # Lista de destinatários
        st.subheader("Destinatários Cadastrados")
        subscriptions = self.sns_manager.get_subscriptions()
        
        if not subscriptions:
            st.info("Nenhum destinatário cadastrado.")
        else:
            for sub in subscriptions:
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.write(f"📧 {sub['email']}")
                with col2:
                    status_icon = "🟡" if sub['status'] == 'Aguardando confirmação' else "✅"
                    st.write(f"{status_icon} {sub['status']}")
                with col3:
                    if st.button("🗑️ Remover", key=f"remove_{sub['email']}"):
                        self.remove_recipient(sub['email'])
                        st.rerun()
        
        # Histórico de Alertas
        if self.alerts:
            st.divider()
            df = pd.DataFrame(self.alerts)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp', ascending=False)
            
            # Contagem de alertas por nível
            alert_counts = df['level'].value_counts()
            
            # Métricas em cards
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "🔴 Alertas Críticos", 
                    alert_counts.get("CRÍTICO", 0),
                    delta=None,
                    delta_color="inverse"
                )
            with col2:
                st.metric(
                    "🟡 Alertas de Atenção", 
                    alert_counts.get("ATENÇÃO", 0),
                    delta=None,
                    delta_color="inverse"
                )
            with col3:
                st.metric(
                    "📊 Total de Alertas",
                    len(df),
                    delta=None,
                    delta_color="inverse"
                )
            
            # Tabela de alertas
            st.write("### 📝 Histórico de Alertas")
            
            def color_level(val):
                if val == "CRÍTICO":
                    return 'color: red; font-weight: bold'
                elif val == "ATENÇÃO":
                    return 'color: orange; font-weight: bold'
                return ''
            
            # Adiciona ícones aos níveis
            df['level'] = df['level'].apply(lambda x: f"{'🔴' if x == 'CRÍTICO' else '🟡'} {x}")
            
            styled_df = df.style\
                .format({'timestamp': lambda x: x.strftime('%d/%m/%Y %H:%M:%S')})\
                .applymap(color_level, subset=['level'])
            
            st.dataframe(
                styled_df,
                width=1000,
                column_config={
                    "timestamp": "Data/Hora",
                    "level": "Nível",
                    "message": "Mensagem"
                }
            )
        else:
            st.info("Nenhum alerta registrado.")
    
    def clear_alerts(self, logger=None):
        """Limpa todos os alertas"""
        self.alerts = []
        log_message = "Todos os alertas foram limpos"
        if logger:
            logger.info(log_message)
        logging.info(log_message)
    

    
    def display_alerts_history(self):
        """Exibe página de histórico de alertas em desenvolvimento"""
        st.title("📊 Histórico de Alertas")
        
        # Container principal
        with st.container():
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col2:
                st.markdown("""
                <div style="text-align: center; padding: 50px;">
                    <h2>🚧 Em Desenvolvimento</h2>
                    <p style="font-size: 18px; color: #666;">
                        Esta funcionalidade está sendo desenvolvida e estará disponível em breve.
                    </p>
                    <p style="font-size: 16px; color: #888;">
                        Por enquanto, você pode visualizar os alertas em tempo real na página principal do sistema de alertas.
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                # Botão para voltar aos alertas
                if st.button("🔙 Voltar aos Alertas", type="primary", use_container_width=True):
                    st.switch_page("pages/alerts.py")
    
    def get_alerts_summary(self):
        """Retorna resumo dos alertas em memória"""
        if self.alerts:
            criticos = len([a for a in self.alerts if a['level'] == 'CRÍTICO'])
            ultimo = max([a['timestamp'] for a in self.alerts]) if self.alerts else None
            return {
                'total': len(self.alerts),
                'criticos': criticos,
                'ultimo': ultimo
            }
        return {'total': 0, 'criticos': 0, 'ultimo': None} 