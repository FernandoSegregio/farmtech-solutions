import os
from sqlalchemy import create_engine
import pandas as pd
import streamlit as st
import logging

class Config:
    user = os.getenv('DB_USER') or st.secrets["database"]["user"]
    password = os.getenv('DB_PASSWORD') or st.secrets["database"]["password"] 
    dsn = os.getenv('DB_DSN') or st.secrets["database"]["dsn"]

def carregar_dados_umidade(conn, logging):
    """
    Carrega dados de leitura e umidade do banco de dados, formata a hora e exibe em formato de tabela.
    Adiciona uma coluna indicando o estado da bomba com base na umidade.

    Args:
    conn: Conexão com o banco de dados.
    logging: Instância de logging para registrar atividades.

    Returns:
    pandas.DataFrame: DataFrame contendo os dados de leitura e umidade com o estado da bomba.
    """
    try:
        # Conexão usando SQLAlchemy com o Oracle
        engine = create_engine(f'oracle+oracledb://{Config.user}:{Config.password}@{Config.dsn}')
        
        # Query para carregar apenas dados de leitura e umidade (últimos 50 registros)
        query = """
        SELECT * FROM (
            SELECT 
                TO_CHAR(data_leitura, 'YYYY-MM-DD') as data_leitura,
                TO_CHAR(hora_leitura, 'HH24:MI:SS') as hora_leitura,
                valor_umidade_leitura
            FROM 
                LEITURA_SENSOR_UMIDADE
            ORDER BY 
                data_leitura DESC, hora_leitura DESC
        ) WHERE ROWNUM <= 50
        """
        
        # Executa a query e carrega os dados em um DataFrame
        df = pd.read_sql(query, engine)
        logging.info(f"Carregados {len(df)} registros de umidade do banco.")
        
        # Renomeia as colunas para o formato esperado pelo dashboard
        df.columns = ['Data', 'Hora', 'Umidade (%)']
        
        # Adicionar coluna com o estado da bomba
        df['estado_bomba'] = df['Umidade (%)'].apply(lambda x: "bomba ligada" if x < 50 else "bomba desligada")
        
        return df

    except Exception as e:
        logging.error(f"Erro ao carregar dados de umidade do banco: {e}")
        print("Erro ao carregar dados de umidade do banco.")
        return None

def carregar_dados_temperatura(conn, logging):
    """
    Carrega dados de leitura de temperatura do banco de dados, formata a hora e exibe em formato de tabela.

    Args:
    conn: Conexão com o banco de dados.
    logging: Instância de logging para registrar atividades.

    Returns:
    pandas.DataFrame: DataFrame contendo os dados de leitura de temperatura.
    """
    try:
        # Conexão usando SQLAlchemy com o Oracle
        engine = create_engine(f'oracle+oracledb://{Config.user}:{Config.password}@{Config.dsn}')
        
        # Query para carregar apenas dados de leitura de temperatura (últimos 50 registros)
        query = """
        SELECT * FROM (
            SELECT 
                TO_CHAR(data_leitura, 'YYYY-MM-DD') as data_leitura,
                TO_CHAR(hora_leitura, 'HH24:MI:SS') as hora_leitura,
                valor_temperatura
            FROM 
                LEITURA_SENSOR_TEMPERATURA
            ORDER BY 
                data_leitura DESC, hora_leitura DESC
        ) WHERE ROWNUM <= 50
        """
        
        # Executa a query e carrega os dados em um DataFrame
        df = pd.read_sql(query, engine)
        logging.info(f"Carregados {len(df)} registros de temperatura do banco.")
        
        # Renomeia as colunas para o formato esperado pelo dashboard
        df.columns = ['Data', 'Hora', 'Temperatura (°C)']
        
        return df

    except Exception as e:
        logging.error(f"Erro ao carregar dados de temperatura do banco: {e}")
        print("Erro ao carregar dados de temperatura do banco.")
        return None

def carregar_dados_ph(conn, logging):
    """
    Carrega dados de leitura de pH do banco de dados, formata a hora e exibe em formato de tabela.

    Args:
    conn: Conexão com o banco de dados.
    logging: Instância de logging para registrar atividades.

    Returns:
    pandas.DataFrame: DataFrame contendo os dados de leitura de pH.
    """
    try:
        # Conexão usando SQLAlchemy com o Oracle
        engine = create_engine(f'oracle+oracledb://{Config.user}:{Config.password}@{Config.dsn}')
        
        # Query para carregar apenas dados de leitura de pH (últimos 50 registros)
        query = """
        SELECT * FROM (
            SELECT 
                TO_CHAR(data_leitura, 'YYYY-MM-DD') as data_leitura,
                TO_CHAR(hora_leitura, 'HH24:MI:SS') as hora_leitura,
                valor_ph_leitura
            FROM 
                LEITURA_SENSOR_PH
            ORDER BY 
                data_leitura DESC, hora_leitura DESC
        ) WHERE ROWNUM <= 50
        """
        
        # Executa a query e carrega os dados em um DataFrame
        df = pd.read_sql(query, engine)
        logging.info(f"Carregados {len(df)} registros de pH do banco.")
        
        # Renomeia as colunas para o formato esperado pelo dashboard
        df.columns = ['Data', 'Hora', 'pH']
        
        return df

    except Exception as e:
        logging.error(f"Erro ao carregar dados de pH do banco: {e}")
        print("Erro ao carregar dados de pH do banco.")
        return None
