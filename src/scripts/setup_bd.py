import os
from dotenv import load_dotenv
import oracledb
import logging
import streamlit as st

# Configuração do logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('setup_bd.log')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

def verificar_e_criar_tabela(cursor, nome_tabela, sql_create, logger):
    """Verifica se a tabela existe e a cria se necessário"""
    try:
        cursor.execute("SELECT COUNT(*) FROM user_tables WHERE table_name = :nome_tabela", 
                      nome_tabela=nome_tabela.upper())
        existe = cursor.fetchone()[0] > 0
        
        if not existe:
            cursor.execute(sql_create)
            logger.info(f"Tabela '{nome_tabela}' criada com sucesso.")
        else:
            logger.info(f"Tabela '{nome_tabela}' já existe.")
    except oracledb.DatabaseError as e:
        logger.error(f"Erro ao criar tabela {nome_tabela}: {e}")
        raise

def criar_sequencias_e_triggers(conn):
    """Cria sequências e triggers para IDs automáticos nas tabelas que precisam de IDs gerados automaticamente."""
    cursor = conn.cursor()
    tabelas_com_trigger = {
        'PROPRIEDADE': 'id_propriedade',
        'CAMPO': 'id_campo',
        'SENSOR_UMIDADE': 'id_sensor_umidade',
        'LEITURA_SENSOR_UMIDADE': 'id_leitura_umidade',
        'LEITURA_SENSOR_TEMPERATURA': 'id_leitura_temperatura',
        'SENSOR_PH': 'id_sensor_ph',
        'LEITURA_SENSOR_PH': 'id_leitura_ph',
        'SENSOR_NUTRIENTES': 'id_sensor_nutrientes',
        'LEITURA_SENSOR_NUTRIENTES': 'id_leitura_nutrientes',
        'CLIMA': 'id_clima',
        'ALERTAS': 'id_alerta'
    }
    
    for tabela, id_coluna in tabelas_com_trigger.items():
        try:
            cursor.execute(f"""
                BEGIN
                    EXECUTE IMMEDIATE 'CREATE SEQUENCE {tabela}_SEQ START WITH 1 INCREMENT BY 1';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE != -955 THEN RAISE; END IF;
                END;
            """)
            logger.info(f"Sequência '{tabela}_SEQ' criada ou já existia.")
            
            cursor.execute(f"""
                CREATE OR REPLACE TRIGGER {tabela}_BI
                BEFORE INSERT ON {tabela}
                FOR EACH ROW
                WHEN (NEW.{id_coluna} IS NULL)
                BEGIN
                    SELECT {tabela}_SEQ.NEXTVAL INTO :NEW.{id_coluna} FROM dual;
                END;
            """)
            logger.info(f"Trigger '{tabela}_BI' criada para tabela '{tabela}'.")
        except oracledb.DatabaseError as e:
            logger.error(f"Erro ao criar sequência ou trigger para a tabela {tabela}: {e}")
            conn.rollback()
    cursor.close()

def criar_tabelas(conn, logger):
    """Cria todas as tabelas necessárias"""
    cursor = conn.cursor()
    
    tabelas = {
        'PRODUTOR': """
            CREATE TABLE PRODUTOR (
                id_produtor NUMBER PRIMARY KEY,
                nome_produtor VARCHAR2(100) NOT NULL,
                email_produtor VARCHAR2(100) UNIQUE NOT NULL,
                telefone_produtor VARCHAR2(20),
                data_cadastro DATE DEFAULT SYSDATE
            )
        """,
        'PROPRIEDADE': """
            CREATE TABLE PROPRIEDADE (
                id_propriedade NUMBER PRIMARY KEY,
                id_produtor NUMBER NOT NULL,
                nome_propriedade VARCHAR2(100) NOT NULL,
                endereco_propriedade VARCHAR2(200),
                area_total NUMBER(10,2),
                data_cadastro DATE DEFAULT SYSDATE,
                FOREIGN KEY (id_produtor) REFERENCES PRODUTOR(id_produtor)
            )
        """,
        'CAMPO': """
            CREATE TABLE CAMPO (
                id_campo NUMBER PRIMARY KEY,
                id_propriedade NUMBER NOT NULL,
                nome_campo VARCHAR2(100) NOT NULL,
                area_campo NUMBER(10,2),
                tipo_cultivo VARCHAR2(50),
                data_plantio DATE,
                FOREIGN KEY (id_propriedade) REFERENCES PROPRIEDADE(id_propriedade)
            )
        """,
        'SENSOR_UMIDADE': """
            CREATE TABLE SENSOR_UMIDADE (
                id_sensor_umidade NUMBER PRIMARY KEY,
                id_campo NUMBER NOT NULL,
                localizacao_sensor VARCHAR2(100),
                data_instalacao DATE DEFAULT SYSDATE,
                status_sensor VARCHAR2(20) DEFAULT 'ATIVO',
                FOREIGN KEY (id_campo) REFERENCES CAMPO(id_campo)
            )
        """,
        'LEITURA_SENSOR_UMIDADE': """
            CREATE TABLE LEITURA_SENSOR_UMIDADE (
                id_leitura_umidade NUMBER PRIMARY KEY,
                id_sensor_umidade NUMBER NOT NULL,
                data_leitura DATE NOT NULL,
                hora_leitura DATE NOT NULL,
                valor_umidade_leitura NUMBER(5,2) NOT NULL,
                FOREIGN KEY (id_sensor_umidade) REFERENCES SENSOR_UMIDADE(id_sensor_umidade)
            )
        """,
        'LEITURA_SENSOR_TEMPERATURA': """
            CREATE TABLE LEITURA_SENSOR_TEMPERATURA (
                id_leitura_temperatura NUMBER PRIMARY KEY,
                id_sensor_temperatura NUMBER NOT NULL,
                data_leitura DATE NOT NULL,
                hora_leitura DATE NOT NULL,
                valor_temperatura_leitura NUMBER(5,2) NOT NULL
            )
        """,
        'SENSOR_PH': """
            CREATE TABLE SENSOR_PH (
                id_sensor_ph NUMBER PRIMARY KEY,
                id_campo NUMBER NOT NULL,
                localizacao_sensor VARCHAR2(100),
                data_instalacao DATE DEFAULT SYSDATE,
                status_sensor VARCHAR2(20) DEFAULT 'ATIVO',
                FOREIGN KEY (id_campo) REFERENCES CAMPO(id_campo)
            )
        """,
        'LEITURA_SENSOR_PH': """
            CREATE TABLE LEITURA_SENSOR_PH (
                id_leitura_ph NUMBER PRIMARY KEY,
                id_sensor_ph NUMBER NOT NULL,
                data_leitura DATE NOT NULL,
                hora_leitura DATE NOT NULL,
                valor_ph_leitura NUMBER(4,2) NOT NULL,
                FOREIGN KEY (id_sensor_ph) REFERENCES SENSOR_PH(id_sensor_ph)
            )
        """,
        'SENSOR_NUTRIENTES': """
            CREATE TABLE SENSOR_NUTRIENTES (
                id_sensor_nutrientes NUMBER PRIMARY KEY,
                id_campo NUMBER NOT NULL,
                tipo_nutriente VARCHAR2(50) NOT NULL,
                localizacao_sensor VARCHAR2(100),
                data_instalacao DATE DEFAULT SYSDATE,
                status_sensor VARCHAR2(20) DEFAULT 'ATIVO',
                FOREIGN KEY (id_campo) REFERENCES CAMPO(id_campo)
            )
        """,
        'LEITURA_SENSOR_NUTRIENTES': """
            CREATE TABLE LEITURA_SENSOR_NUTRIENTES (
                id_leitura_nutrientes NUMBER PRIMARY KEY,
                id_sensor_nutrientes NUMBER NOT NULL,
                data_leitura DATE NOT NULL,
                hora_leitura DATE NOT NULL,
                valor_nutrientes_leitura NUMBER(8,2) NOT NULL,
                FOREIGN KEY (id_sensor_nutrientes) REFERENCES SENSOR_NUTRIENTES(id_sensor_nutrientes)
            )
        """,
        'CLIMA': """
            CREATE TABLE CLIMA (
                id_clima NUMBER PRIMARY KEY,
                id_propriedade NUMBER NOT NULL,
                data_clima DATE NOT NULL,
                temperatura_max NUMBER(5,2),
                temperatura_min NUMBER(5,2),
                umidade_ar NUMBER(5,2),
                precipitacao NUMBER(6,2),
                velocidade_vento NUMBER(5,2),
                FOREIGN KEY (id_propriedade) REFERENCES PROPRIEDADE(id_propriedade)
            )
        """,
        'NUTRIENTES': """
            CREATE TABLE NUTRIENTES (
                id_nutriente NUMBER PRIMARY KEY,
                nome_nutriente VARCHAR2(50) NOT NULL,
                unidade_medida VARCHAR2(20) NOT NULL,
                valor_ideal_min NUMBER(8,2),
                valor_ideal_max NUMBER(8,2)
            )
        """,
        'ALERTAS': """
            CREATE TABLE ALERTAS (
                id_alerta NUMBER PRIMARY KEY,
                tipo_alerta VARCHAR2(50) NOT NULL,
                nivel_alerta VARCHAR2(20) NOT NULL,
                mensagem_alerta CLOB NOT NULL,
                data_alerta DATE NOT NULL,
                hora_alerta DATE NOT NULL,
                sensor_origem VARCHAR2(50),
                valor_sensor NUMBER(10,2),
                email_enviado CHAR(1) DEFAULT 'N',
                data_criacao DATE DEFAULT SYSDATE
            )
        """
    }
    
    for nome_tabela, sql_create in tabelas.items():
        verificar_e_criar_tabela(cursor, nome_tabela, sql_create, logger)
    
    cursor.close()

def setup_banco_dados(conn):
    logger.info("Iniciando configuração do banco de dados")
    criar_tabelas(conn, logger)
    criar_sequencias_e_triggers(conn)
    logger.info("Configuração do banco de dados concluída")

if __name__ == "__main__":
    load_dotenv()
    
    try:
        conn = oracledb.connect(
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            dsn=os.getenv('DB_DSN')
        )
        setup_banco_dados(conn)
    except oracledb.DatabaseError as e:
        logger.error(f"Erro ao conectar ao banco de dados: {e}")
    finally:
        if 'conn' in locals():
            conn.close() 