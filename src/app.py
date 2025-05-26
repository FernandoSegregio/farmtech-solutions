"""
Ponto de entrada principal da aplicação FarmTech Solutions

Para executar:
1. Certifique-se de que está no diretório raiz do projeto
2. Execute: streamlit run src/app.py
"""
import sys
import os

# Adiciona o diretório src ao path para resolver importações
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fase4.dashboard import Dashboard

if __name__ == "__main__":
    dashboard = Dashboard()
    dashboard.run()

