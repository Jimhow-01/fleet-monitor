import json
import os
import shutil
import time
import tkinter as tk
from pathlib import Path

import psutil
import requests
import wmi

AGENT_BINARY = "fleet_agent.exe"


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

    # Monitorar o tempo todo e executar a tarefa no horário definido
    while True:
        horario = time.localtime()
        print(horario)
        hora_atual = time.localtime().tm_hour
        minuto_atual = time.localtime().tm_min
        if hora_atual == 18 and minuto_atual == 38:  # Horário definido (17:42)
            verificar_e_enviar()

        time.sleep(60)  # Verificar a cada minuto

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

    requisicao = requests.put(f'{link}/{numero_do_pc2}.json', data=json.dumps(dados))
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

    # Crie rótulos e entradas para nome de usuário e nome do PC com espaçamento lateral
    label_usuario = tk.Label(root, text="Nome de Usuário:")
    label_usuario.pack()
    entry_usuario = tk.Entry(root)
    entry_usuario.pack(pady=5)  # Adiciona espaço vertical entre o rótulo e a entrada

    label_pc = tk.Label(root, text="Nome do PC:")
    label_pc.pack()
    entry_pc = tk.Entry(root)
    entry_pc.pack(pady=5)  # Adiciona espaço vertical entre o rótulo e a entrada

    def salvar_informacoes():
        usuario_real = entry_usuario.get()
        numero_do_pc = entry_pc.get()

        # Salvar informações em arquivo TXT
        salvar_em_arquivo(usuario_real, numero_do_pc)

        # Chamar a função salvar_no_firebase globalmente
        salvar_no_firebase(usuario_real, get_system_info(), f'Gabinete {numero_do_pc}')

        # Exibir uma mensagem quando as informações forem salvas
        mensagem_salvo = tk.Label(root, text="Informações salvas com sucesso!")
        mensagem_salvo.pack()

    def salvar_em_arquivo(usuario_real, numero_do_pc3):
        diretorio_documentos = Path.home() / 'shared-state' / "Documents"
        arquivo_usuario = os.path.join(diretorio_documentos, "user.txt")
        arquivo_pc = os.path.join(diretorio_documentos, "numero do pc.txt")

        with open(arquivo_usuario, "w") as f_usuario:
            f_usuario.write(f"{usuario_real}\n")

        with open(arquivo_pc, "w") as f_pc:
            f_pc.write(f"{numero_do_pc3}\n")
            
    # Crie um botão para salvar as informações
    botao_salvar = tk.Button(root, text="Salvar Informações", command=salvar_informacoes)
    botao_salvar.pack(pady=10)  # Adiciona espaço vertical abaixo do botão

    root.mainloop()

# Definir a função verificar_e_enviar globalmente
def verificar_e_enviar():
    diretorio_documentos = Path.home() / 'shared-state' / "Documents"
    arquivo_usuario = os.path.join(diretorio_documentos, "user.txt")
    arquivo_pc = os.path.join(diretorio_documentos, "numero do pc.txt")

    if os.path.exists(arquivo_usuario) and os.path.exists(arquivo_pc):
        with open(arquivo_usuario) as f_usuario, open(arquivo_pc) as f_pc:
            usuario_real = f_usuario.readline().strip()
            numero_do_pc3 = f_pc.readline().strip()
            numero_do_pc2 = 'Gabinete ' + numero_do_pc3

            system_info = get_system_info()
            salvar_no_firebase(usuario_real, system_info, numero_do_pc2)

            print("Informações enviadas para o Firebase:")
            print(f"Usuário: {usuario_real}")
            print(f"Número do PC: {numero_do_pc2}")
    else:
        exibir_interface_grafica()
        
        # Caminho do arquivo a ser copiado
        caminho_origem = os.environ.get("AGENT_BINARY_PATH", str(Path.home() / "Downloads" / AGENT_BINARY))

        # NOTE: persistencia - copia o agente para a pasta Startup do Windows
        # (auto-inicio). Nao ha instalador formal nem desinstalacao.
        # Caminho de destino na pasta de inicialização do sistema
        caminho_destino = str(Path(os.environ.get("APPDATA", ".")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / AGENT_BINARY)

        # Copia o arquivo para o diretório de inicialização
        shutil.copy2(caminho_origem, caminho_destino)

# Chamar a função main() apenas se este script estiver sendo executado diretamente (não importado)
if __name__ == "__main__":
    main()