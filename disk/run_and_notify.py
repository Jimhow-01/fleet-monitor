import os
import subprocess
import time
from pathlib import Path

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def enviar_mensagem_slack(mensagem, canal, slack_token):
    client = WebClient(token=slack_token)
    
    try:
        response = client.chat_postMessage(
            channel=canal,
            text=mensagem
        )
        print(f"Mensagem enviada para o Slack no canal {canal}")
    except SlackApiError as e:
        print(f"Erro ao enviar mensagem: {e.response['error']}")

def executar_bats():
    scanner = Path(__file__).parent / "run_hdd_scanner.bat"
    status = Path(__file__).parent / "run_forecast.bat"
    
    slack_token = os.environ["SLACK_BOT_TOKEN"] 
    canal_slack = os.environ["SLACK_CHANNEL_ID"]  

    print(f"Executando {scanner}...")
    processo_1 = subprocess.run(scanner, shell=True, capture_output=True, text=True)
    print("HDs escaneados.\n", processo_1.stdout)
    
    time.sleep(2)
    
    print(f"Executando {status}...")
    processo_2 = subprocess.run(status, shell=True, capture_output=True, text=True)
    retorno_status = processo_2.stdout
    print("Retorno do segundo bat:\n", retorno_status)

    mensagem_slack = f"Retorno do Status do HDD Scanner:\n{retorno_status}"
    enviar_mensagem_slack(mensagem_slack, canal_slack, slack_token)

executar_bats()