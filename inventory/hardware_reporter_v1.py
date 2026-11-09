import json
import os
from datetime import datetime

import psutil
import requests
import wmi

# Inicializa a variável global usuario
usuario = os.getlogin()
nome_do_pc = "PC - " + usuario

def HardwareInfoRoutine():
    # Definir a função salvar_no_firebase globalmente
    def salvar_no_firebase(usuario, system_info, nome_do_pc):
        link = os.environ["FIREBASE_DATABASE_URL"] + "/"
        
        
        dados = {
            'Usuario': usuario,
            'Processador': system_info["Processador"],
            'Placa-Mãe': system_info["Placa-Mãe"],
            'Placa de Vídeo': system_info["Placa de Vídeo"],
            'Discos Rígidos': system_info["Discos Rígidos"],
            'Data da Última Verificação': str(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        }

        # Converta a lista de informações da memória RAM e discos rígidos em JSON para incluí-la nos dados
        dados["Memória RAM"] = json.dumps(system_info["Memória RAM"])

        requisicao = requests.put(f'{link}/{nome_do_pc}.json', data=json.dumps(dados))
        print(requisicao)
        print(requisicao.text)

    def get_system_info():
        # Conecta-se ao serviço WMI (Windows Management Instrumentation)
        c = wmi.WMI()

        # Informações do Processador
        processor_name = ""
        for processor in c.Win32_Processor():
            processor_name = processor.Name

        # Informações da Placa-Mãe
        motherboard_model = ""
        for motherboard in c.Win32_BaseBoard():
            motherboard_model = motherboard.Product

        # Informações sobre a Memória RAM
        memory_info = []  # Crie uma lista para armazenar informações da memória RAM
        for memory in c.Win32_PhysicalMemory():
            memory_info.append({
                "Capacidade (GB)": int(memory.Capacity) / (1024**3),
                "Velocidade (MHz)": memory.Speed
            })

        # Informações da Placa de Vídeo
        gpu_model = ""
        for gpu in c.Win32_VideoController():
            gpu_model = gpu.Name

        # Informações sobre os discos rígidos
        disk_info = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info.append({
                    "Disco": partition.device,
                    "Tipo": partition.fstype,
                    "Tamanho Total (GB)": usage.total / (1024**3),
                    "Espaço Livre (GB)": usage.free / (1024**3)})
            except Exception as e:
                print("erro para pegar o disco")

        return {
            "Processador": processor_name,
            "Placa-Mãe": motherboard_model,
            "Memória RAM": memory_info,
            "Placa de Vídeo": gpu_model,
            "Discos Rígidos": disk_info
        }

    # Chamar a função main() apenas se este script estiver sendo executado diretamente (não importado)
    if __name__ == "__main__":
        get_system_info()
        salvar_no_firebase(usuario, get_system_info(), nome_do_pc)

HardwareInfoRoutine()