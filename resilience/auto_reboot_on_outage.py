import platform
import subprocess
import time


def check_internet():
    try:
        host = "8.8.8.8"
        param = "-n" if platform.system().lower() == "windows" else "-c"
        command = ["ping", param, "1", host]
    
        if platform.system().lower() == "windows":
            return subprocess.call(command, creationflags=subprocess.CREATE_NO_WINDOW) == 0
        else:
            return subprocess.call(command) == 0
    except Exception:
        return False

def force_restart_machine():
    if platform.system().lower() == "windows":
        subprocess.Popen(["shutdown", "/r", "/f", "/t", "0"], creationflags=subprocess.CREATE_NO_WINDOW)  
    else:
        subprocess.Popen(["sudo", "reboot", "-f"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)  

POLL_SECONDS = 60          # intervalo real do loop, em segundos
no_internet_time = 0
timeout_limit = 1800  # 30 minutos

while True:
    if check_internet():
        print("Conexão com a internet detectada.")
        no_internet_time = 0  
    else:
        # NOTE: soma o intervalo real do loop (antes era +=2 com sleep(60), o que
        # fazia o limiar de 1800 ser atingido em ~15 minutos reais, nao 30).
        no_internet_time += POLL_SECONDS
        print(f"Sem conexão com a internet há {no_internet_time} segundos.")
    
    if no_internet_time >= timeout_limit:
        print("Sem internet por 30 minutos. Reiniciando a máquina forçadamente...")
        force_restart_machine()
    
    time.sleep(POLL_SECONDS)
