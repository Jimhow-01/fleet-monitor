import datetime
import json
import os
from pathlib import Path

import psutil

# Define o caminho para o arquivo JSON
json_path = Path(__file__).parent / "disk_space.json"

# Verifica se o arquivo JSON já existe, caso contrário cria com as informações do espaço máximo de cada disco
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

# Verifica se a chave "TimeLine" existe no dicionário disk_space, caso contrário cria a chave
if "TimeLine" not in disk_space:
    disk_space["TimeLine"] = {}

# Adiciona uma nova entrada com a data atual e o espaço ocupado de cada disco se a última entrada não for da data atual
last_date = list(disk_space.get("TimeLine", {}).keys())[-1] if disk_space.get("TimeLine") else None
today_date = datetime.datetime.now().strftime("%d-%m-%Y")
if last_date != today_date:
    disk_space["TimeLine"][today_date] = {}
    for disk in psutil.disk_partitions():
        disk_name = disk.device[:2]
        used_space = psutil.disk_usage(disk_name).used
        disk_space["TimeLine"][today_date][disk_name] = used_space
    with open(json_path, "w") as json_file:
        json.dump(disk_space, json_file)
