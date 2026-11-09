import json
import os
import time
from datetime import datetime
from pathlib import Path

import psutil
import requests
import schedule
from sklearn.linear_model import LinearRegression
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def verifica_hdd():
    # Função para enviar notificação no Slack
    def enviar_notificacao_slack(mensagem):
        client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
        try:
            response = client.chat_postMessage(
                channel=os.environ["SLACK_CHANNEL_ID"],
                text=mensagem
            )
        except SlackApiError as e:
            print(f"Erro ao enviar mensagem no Slack: {e.response['error']}")

    # Caminho para o arquivo JSON
    json_path = Path(__file__).parent / "disk_space.json"

    # Verifica se o arquivo JSON existe, caso contrário cria com as informações do espaço máximo de cada disco
    if not os.path.isfile(json_path):
        disk_space = {"TotalSpace": {}}
        for disk in psutil.disk_partitions():
            disk_name = disk.device[:2]
            total_space = psutil.disk_usage(disk_name).total
            disk_space["TotalSpace"][disk_name] = total_space
        with open(json_path, "w") as json_file:
            json.dump(disk_space, json_file)
    else:
        with open(json_path) as json_file:
            disk_space = json.load(json_file)

    # Verifica se a chave "TimeLine" existe no dicionário disk_space
    if "TimeLine" not in disk_space:
        disk_space["TimeLine"] = {}

    # Adiciona uma nova entrada com a data atual e o espaço ocupado de cada disco, se necessário
    last_date = list(disk_space.get("TimeLine", {}).keys())[-1] if disk_space.get("TimeLine") else None
    today_date = datetime.now().strftime("%d-%m-%Y")  # Corrigido aqui
    if last_date != today_date:
        disk_space["TimeLine"][today_date] = {}
        for disk in psutil.disk_partitions():
            disk_name = disk.device[:2]
            used_space = psutil.disk_usage(disk_name).used
            disk_space["TimeLine"][today_date][disk_name] = used_space
        with open(json_path, "w") as json_file:
            json.dump(disk_space, json_file)

    # Função para calcular a porcentagem de espaço ocupado do HD
    def calcular_porcentagem_hd(total_hd_bytes, limite_percentual):
        valor_bytes = total_hd_bytes * limite_percentual
        return valor_bytes

    # Carrega os dados do JSON
    with open(json_path) as f:
        data = json.load(f)

    results = []
    limite_percentual = 0.85  # Limite de 85% de uso do HD

    for letter in data['TotalSpace'].keys():
        
        drive_percentages = []

        for date_str, drive_sizes in data['TimeLine'].items():
            date = datetime.strptime(date_str, '%d-%m-%Y')
            if letter in drive_sizes:
                drive_percentages.append(drive_sizes[letter] / data['TotalSpace'][letter])
                
        if len(drive_percentages) > 2:
            drive_model = LinearRegression().fit([[i] for i in range(len(drive_percentages))], drive_percentages)
            # Calcula quando o HD vai atingir 85% de capacidade
            drive_time = (calcular_porcentagem_hd(1, limite_percentual) - drive_model.intercept_) / drive_model.coef_[0]
            results.append({'letter': letter, 'drive_time': drive_time})

    # Verifica se algum HD precisa de upgrade e envia mensagem no Slack
    for r in results:
        if r["drive_time"] < 45:
            mensagem = f'ALERTA: HD {r["letter"]} atingirá 85% de capacidade em {r["drive_time"]:.2f} dias. URGENTE!'
            enviar_notificacao_slack(mensagem)
        elif r["drive_time"] < 60:
            mensagem = f'HD {r["letter"]} atingirá 85% de capacidade em {r["drive_time"]:.2f} dias. Planeje um upgrade.'
            enviar_notificacao_slack(mensagem)

    print(f"Total de {len(results)} discos monitorados. Notificações enviadas se necessário.")

CLICKUP_API_TOKEN = os.environ["CLICKUP_API_TOKEN"]
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CHANNEL = os.environ["SLACK_CHANNEL_ID"]
CLICKUP_LIST_ID = os.environ.get("CLICKUP_LIST_ID", "")
MESSAGE_STORAGE_FILE = 'message_timestamps.json'

slack_client = WebClient(token=SLACK_BOT_TOKEN)

def load_message_storage():
    try:
        with open(MESSAGE_STORAGE_FILE) as f:
            content = f.read()
            if content.strip() == "":
                return {}
            return json.loads(content)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        print("Erro ao decodificar o arquivo JSON. O arquivo pode estar corrompido.")
        return {}

def save_message_storage(data):
    with open(MESSAGE_STORAGE_FILE, 'w') as f:
        json.dump(data, f)

def send_slack_message(task_messages):
    try:
        message = "Personal and hardware configuration:\n" + "\n".join(task_messages)
        
        response = slack_client.chat_postMessage(
            channel=SLACK_CHANNEL,
            text=message
        )

        timestamp = response['ts']
        message_storage = load_message_storage()
        
        for task_message in task_messages:
            task_name = task_message.split('"')[1]
            due_date_str = task_message.split('em ')[1].split('.')[0] 
            
            message_storage[timestamp] = {
                'sent_time': datetime.now().isoformat(),
                'due_date': due_date_str,
                'task_name': task_name
            }
        
        save_message_storage(message_storage)
        print(f"Mensagem enviada com sucesso: {timestamp}")
    except SlackApiError as e:
        print(f"Erro ao enviar mensagem para o Slack: {e.response['error']}")
        print(f"Detalhes da resposta: {e.response}")
    except Exception as e:
        print(f"Erro inesperado: {e}")

def delete_old_messages():
    message_storage = load_message_storage()
    now = datetime.now()

    latest_timestamp = max(message_storage.keys(), key=lambda ts: datetime.fromisoformat(message_storage[ts]['sent_time']), default=None)

    for timestamp, message_info in list(message_storage.items()):
        try:
            sent_time = datetime.fromisoformat(message_info.get('sent_time', ''))
            
            due_date_str = message_info.get('due_date')
            if due_date_str:
                due_date = datetime.strptime(due_date_str, '%d-%m-%Y')
                if now > due_date:
                    slack_client.chat_delete(
                        channel=SLACK_CHANNEL,
                        ts=timestamp
                    )
                    print(f"Mensagem excluída após o vencimento da tarefa: {timestamp}")
                    del message_storage[timestamp]
            else:
                print(f"'due_date' não encontrado nas informações da mensagem para o timestamp: {timestamp}")

            if timestamp != latest_timestamp:
                slack_client.chat_delete(
                    channel=SLACK_CHANNEL,
                    ts=timestamp
                )
                print(f"Mensagem antiga excluída com sucesso: {timestamp}")
                del message_storage[timestamp]

        except SlackApiError as e:
            print(f"Erro ao excluir mensagem do Slack: {e.response['error']}")
        except Exception as e:
            print(f"Erro inesperado ao excluir mensagem: {e}")

    save_message_storage(message_storage)

def get_due_tasks():
    url = f'https://api.clickup.com/api/v2/list/{CLICKUP_LIST_ID}/task'
    headers = {
        'Authorization': CLICKUP_API_TOKEN
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        tasks = response.json().get('tasks', [])
        print(f"Tasks: {tasks}")
        return tasks
    else:
        print(f"Erro na requisição: {response.status_code}")
        print(response.text)
        return []

def check_due_dates():
    tasks = get_due_tasks()
    today = datetime.now().date()
    print(f"A data de hoje é: {today.strftime('%d-%m-%Y')}")
    
    task_messages = [] 

    for task in tasks:
        due_timestamp = int(task['due_date']) / 1000
        due_date_dt = datetime.fromtimestamp(due_timestamp).date()
        due_date = due_date_dt.strftime('%d-%m-%Y')
        days_remaining = (due_date_dt - today).days
        print(f"Tarefa: {task['name']}, Due Date: {due_date}, Dias restantes: {days_remaining}")

        if days_remaining == 2 or days_remaining == 1:
            task_messages.append(f'- A tarefa "{task["name"]}" está agendada para vencer em {due_date}. Faltam {days_remaining} dias.')
        elif days_remaining == 0:
            task_messages.append(f'- A tarefa "{task["name"]}" vence hoje ({due_date}).')

    if task_messages:  
        send_slack_message(task_messages)

def job():
    print("Iniciando verificacao do disco da esta...")
    verifica_hdd()
    time.sleep(2)
    print("Iniciando verificação de tarefas...")
    check_due_dates()
    delete_old_messages()

schedule.every().day.at("14:03").do(job)

print("Agendamento concluído. Verificando tarefas diariamente às 14h01h.")

while True:
    schedule.run_pending()
    time.sleep(60)  