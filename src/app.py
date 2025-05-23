"""
Aplicação principal do FarmTech Solutions

Para executar:
1. Certifique-se de que está no diretório raiz do projeto
2. Execute: python -m src.app
"""
from fase4.dashboard import Dashboard

if __name__ == "__main__":
    dashboard = Dashboard()
    dashboard.run()

