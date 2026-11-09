import json
import os
import random
import time
import tkinter as tk

import psutil
import requests
import schedule
import wmi

# Inicializa a variável global usuario
usuario = None

def main():
    # Utiliza a variável global usuario
    global usuario
    
    # Obtemos o nome do usuário logado no sistema
    usuario = os.getlogin()
    
    # E mostramos o resultado
    print("O usuário logado no momento é:", usuario)

    # Chama verificar_e_enviar imediatamente após obter o nome do usuário
    verificar_e_enviar()

    # Executar o agendamento em um loop
    while True:
        schedule.run_pending()
        time.sleep(1)

# Definir a função salvar_no_firebase globalmente
def salvar_no_firebase(usuario_real, system_info, numero_do_pc2):
    link = os.environ["FIREBASE_DATABASE_URL"] + "/"

    dados = {
        'Usuario': usuario_real,
        'Processador': system_info["Processador"],
        'Placa-Mãe': system_info["Placa-Mãe"],
        'Placa de Vídeo': system_info["Placa de Vídeo"],
        'Discos Rígidos': system_info["Discos Rígidos"]
    }

    # Converta a lista de informações da memória RAM e discos rígidos em JSON para incluí-la nos dados
    dados["Memória RAM"] = json.dumps(system_info["Memória RAM"])

    tentativas = 3  # Número de tentativas
    for _ in range(tentativas):
        try:
            requisicao = requests.put(f'{link}/{numero_do_pc2}.json', data=json.dumps(dados))
            requisicao.raise_for_status()  # Lança uma exceção para códigos de resposta HTTP diferentes de 2xx
            print(requisicao)
            print(requisicao.text)
            return True  # Se a tentativa for bem-sucedida, retorna True
        except requests.exceptions.RequestException as e:
            print(f"Erro ao enviar para o Firebase: {e}")
            time.sleep(5)  # Espera por 5 segundos antes de tentar novamente

    return False  # Retorna False se todas as tentativas falharem
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
        usage = psutil.disk_usage(partition.mountpoint)
        disk_info.append({
            "Disco": partition.device,
            "Tipo": partition.fstype,
            "Tamanho Total (GB)": usage.total / (1024**3),
            "Espaço Livre (GB)": usage.free / (1024**3)
        })

    return {
        "Processador": processor_name,
        "Placa-Mãe": motherboard_model,
        "Memória RAM": memory_info,
        "Placa de Vídeo": gpu_model,
        "Discos Rígidos": disk_info
    }

def exibir_interface_grafica():
    # Crie uma janela tkinter
    root = tk.Tk()
    root.title("Informações do PC")

    # Crie rótulos e entradas para nome de usuário e gabinete com espaçamento lateral
    label_usuario = tk.Label(root, text="Nome de Usuário:")
    label_usuario.pack()
    entry_usuario = tk.Entry(root)
    entry_usuario.pack(pady=5)  # Adiciona espaço vertical entre o rótulo e a entrada

    # Adiciona um ID aleatório de 8 dígitos em números ao gabinete
    numero_do_pc = 'PC id = ' + ''.join(str(random.randint(0, 9)) for _ in range(8))
    label_pc = tk.Label(root, text=f"Gabinete: {numero_do_pc}")
    label_pc.pack()

    def salvar_informacoes():
        usuario_real = entry_usuario.get()

        # Chamar a função salvar_no_firebase globalmente
        success = salvar_no_firebase(usuario_real, get_system_info(), numero_do_pc)

        if success:
            # Exibir uma mensagem quando as informações forem salvas
            mensagem_salvo = tk.Label(root, text="Informações salvas com sucesso! Pode fechar o script\n(Information saved successfully! You can close the script.)")
            mensagem_salvo.pack()

        else:
            # Exibir uma mensagem de falha no envio
            mensagem_erro = tk.Label(root, text="Erro ao enviar informações. Tente novamente.")
            mensagem_erro.pack()

    # Crie um botão para salvar as informações
    botao_salvar = tk.Button(root, text="Salvar Informações", command=salvar_informacoes)
    botao_salvar.pack(pady=10)  # Adiciona espaço vertical abaixo do botão

    root.mainloop()

# Definir a função verificar_e_enviar globalmente
def verificar_e_enviar():
    exibir_interface_grafica()

# Chamar a função main() apenas se este script estiver sendo executado diretamente (não importado)
if __name__ == "__main__":
    main()