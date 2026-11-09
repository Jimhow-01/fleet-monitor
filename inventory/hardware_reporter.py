import json
import os
import tkinter as tk
from datetime import datetime
from tkinter import messagebox

import psutil
import requests
import wmi


def show_success(nome_do_pc: str):
    root = tk.Tk()
    root.withdraw()  # não mostrar a janela principal
    messagebox.showinfo(
        "Sucesso",
        f"The hardware configuration was successfully submitted!\n\nRegistro: {nome_do_pc}"
    )
    root.destroy()


def show_error(msg: str):
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Erro ao enviar", msg)
    root.destroy()


def hardwarelist(usuario):
    def get_primary_mac():
        interfaces = psutil.net_if_addrs()

        # prioridade explícita (Linux/Windows)
        for iface in ["eth0", "enp", "eno", "ens", "Ethernet", "Wi-Fi"]:
            for name, addrs in interfaces.items():
                if iface.lower() in name.lower():
                    for addr in addrs:
                        if addr.family == psutil.AF_LINK:
                            return addr.address

        # fallback
        for addrs in interfaces.values():
            for addr in addrs:
                if addr.family == psutil.AF_LINK and addr.address != "00:00:00:00:00:00":
                    return addr.address

        return None

    def map_logical_drives_to_physical_disks():
        c = wmi.WMI()

        partition_to_disk = {}
        for disk in c.Win32_DiskDrive():
            for part in disk.associators("Win32_DiskDriveToDiskPartition"):
                partition_to_disk[part.DeviceID] = {
                    "disk_index": int(disk.Index),
                    "model": disk.Model,
                }

        logical_to_partition = {}
        for ld in c.Win32_LogicalDisk():
            for part in ld.associators("Win32_LogicalDiskToPartition"):
                logical_to_partition[ld.DeviceID] = part.DeviceID

        logical_to_disk = {}
        for logical, part_id in logical_to_partition.items():
            if part_id in partition_to_disk:
                logical_to_disk[logical] = partition_to_disk[part_id]

        return logical_to_disk

    def get_system_info():
        c = wmi.WMI()
        logical_map = map_logical_drives_to_physical_disks()

        processor_name = ""
        for processor in c.Win32_Processor():
            processor_name = processor.Name

        motherboard_model = ""
        for motherboard in c.Win32_BaseBoard():
            motherboard_model = motherboard.Product

        memory_info = []
        for memory in c.Win32_PhysicalMemory():
            # serial/partnumber costumam ser os melhores IDs
            serial = (getattr(memory, "SerialNumber", "") or "").strip()
            part = (getattr(memory, "PartNumber", "") or "").strip()
            memory_info.append({
                "Capacidade (GB)": int(memory.Capacity) / (1024**3),
                "Velocidade (MHz)": memory.Speed,
                "SerialNumber": serial or None,
                "Modelo": part or None
            })

        gpu_model = ""
        for gpu in c.Win32_VideoController():
            gpu_model = gpu.Name

        disk_info = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                drive = partition.device.rstrip("\\")
                disk_meta = logical_map.get(drive, {})

                disk_info.append({
                    "Disco": partition.device,
                    "Tipo": partition.fstype,
                    "Tamanho Total (GB)": usage.total / (1024**3),
                    "Espaço Livre (GB)": usage.free / (1024**3),
                    "DiskIndex": disk_meta.get("disk_index"),
                    "Modelo": disk_meta.get("model"),
                })
            except Exception as e:
                print(f"Erro para pegar o disco {partition.device}: {e}")

        return {
            "Processador": processor_name,
            "Placa-Mãe": motherboard_model,
            "Memória RAM": memory_info,
            "Placa de Vídeo": gpu_model,
            "Discos Rígidos": disk_info
        }

    def salvar_no_firebase(usuario, system_info, nome_do_pc):
        link = os.environ["FIREBASE_DATABASE_URL"] + "/"

        dados = {
            "Usuario": usuario,
            "Processador": system_info["Processador"],
            "Placa-Mãe": system_info["Placa-Mãe"],
            "Placa de Vídeo": system_info["Placa de Vídeo"],
            "Discos Rígidos": system_info["Discos Rígidos"],
            "Memória RAM": system_info["Memória RAM"],  # mantém como lista (node)
            "Data da Última Verificação": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        }

        try:
            requisicao = requests.put(
                f"{link}/{nome_do_pc}.json",
                data=json.dumps(dados),
                timeout=15
            )

            if requisicao.ok:
                show_success(nome_do_pc)
            else:
                show_error(f"HTTP {requisicao.status_code}\n\n{requisicao.text}")

        except requests.RequestException as e:
            show_error(str(e))

    mac = get_primary_mac() or "sem-mac"

    def HardwareInfoRoutine(usuario):
        nome_do_pc = "PC - " + f"{mac}"
        system_info = get_system_info()
        salvar_no_firebase(usuario, system_info, nome_do_pc)

    HardwareInfoRoutine(usuario)



def get_chrome_users():
    # NOTE: le "Local State" do Chrome e extrai nomes de perfil e e-mails das contas
    # logadas na estacao, e isso vai junto para o Firebase. Se voce nao quer coletar
    # dado de navegador, remova a chamada no final do arquivo.
    users = []

    base_path = os.path.join(
        os.environ.get("LOCALAPPDATA", ""),
        "Google", "Chrome", "User Data"
    )

    local_state_path = os.path.join(base_path, "Local State")

    if not os.path.exists(local_state_path):
        return users

    try:
        with open(local_state_path, encoding="utf-8") as f:
            local_state = json.load(f)

        profiles = local_state.get("profile", {}).get("info_cache", {})

        for profile_dir, info in profiles.items():
            users.append({
                "profile_dir": profile_dir,
                "profile_name": info.get("name"),
                "email": info.get("user_name"),  # pode ser None
                "is_guest": info.get("is_guest", False),
            })

    except Exception as e:
        print("Erro lendo Chrome Local State:", e)

    return users

a = get_chrome_users()
hardwarelist(a)
