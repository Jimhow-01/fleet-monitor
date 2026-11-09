import json
import os
import shutil
import time
import tkinter as tk
from datetime import datetime
from threading import Thread
from tkinter import filedialog, messagebox

import schedule

CONFIG_FILE = "backup_config.json"

class BackupApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Backup Automático")
        self.source_folder1 = tk.StringVar()
        self.source_folder2 = tk.StringVar()
        self.backup_base_folder = tk.StringVar()
        self.backup_time = tk.StringVar(value="02:00")

        self.create_widgets()
        self.load_configuration()
        self.start_scheduler()

    def create_widgets(self):
        tk.Label(self.root, text="Pasta de Origem 1:").grid(row=0, column=0, sticky=tk.W)
        tk.Entry(self.root, textvariable=self.source_folder1).grid(row=0, column=1)
        tk.Button(self.root, text="Selecionar", command=self.select_source_folder1).grid(row=0, column=2)

        tk.Label(self.root, text="Pasta de Origem 2:").grid(row=1, column=0, sticky=tk.W)
        tk.Entry(self.root, textvariable=self.source_folder2).grid(row=1, column=1)
        tk.Button(self.root, text="Selecionar", command=self.select_source_folder2).grid(row=1, column=2)

        tk.Label(self.root, text="Pasta de Destino:").grid(row=2, column=0, sticky=tk.W)
        tk.Entry(self.root, textvariable=self.backup_base_folder).grid(row=2, column=1)
        tk.Button(self.root, text="Selecionar", command=self.select_backup_base_folder).grid(row=2, column=2)

        tk.Label(self.root, text="Horário do Backup (HH:MM):").grid(row=3, column=0, sticky=tk.W)
        tk.Entry(self.root, textvariable=self.backup_time).grid(row=3, column=1)

        tk.Button(self.root, text="Salvar Configuração", command=self.save_configuration).grid(row=4, column=0, columnspan=3)

    def select_source_folder1(self):
        folder = filedialog.askdirectory()
        if folder:
            self.source_folder1.set(folder)

    def select_source_folder2(self):
        folder = filedialog.askdirectory()
        if folder:
            self.source_folder2.set(folder)

    def select_backup_base_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.backup_base_folder.set(folder)

    def save_configuration(self):
        backup_time = self.backup_time.get()
        if not (self.source_folder1.get() and self.source_folder2.get() and self.backup_base_folder.get()):
            messagebox.showerror("Erro", "Todas as pastas devem ser selecionadas.")
            return
        if not self.validate_time_format(backup_time):
            messagebox.showerror("Erro", "Formato de horário inválido. Use HH:MM.")
            return

        config = {
            "source_folder1": self.source_folder1.get(),
            "source_folder2": self.source_folder2.get(),
            "backup_base_folder": self.backup_base_folder.get(),
            "backup_time": backup_time
        }
        with open(CONFIG_FILE, "w") as config_file:
            json.dump(config, config_file)

        schedule.clear()  # Limpa tarefas agendadas anteriores
        schedule.every().day.at(backup_time).do(self.daily_backup)

        messagebox.showinfo("Configuração Salva", "Configuração salva com sucesso!")

    def load_configuration(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE) as config_file:
                config = json.load(config_file)
                self.source_folder1.set(config.get("source_folder1", ""))
                self.source_folder2.set(config.get("source_folder2", ""))
                self.backup_base_folder.set(config.get("backup_base_folder", ""))
                self.backup_time.set(config.get("backup_time", "02:00"))

                schedule.clear()  # Limpa tarefas agendadas anteriores
                schedule.every().day.at(self.backup_time.get()).do(self.daily_backup)

    def validate_time_format(self, time_str):
        try:
            time.strptime(time_str, "%H:%M")
            return True
        except ValueError:
            return False

    def copy_files(self, source_folder, dest_folder):
        try:
            if not os.path.exists(dest_folder):
                os.makedirs(dest_folder)
            for item in os.listdir(source_folder):
                s = os.path.join(source_folder, item)
                d = os.path.join(dest_folder, item)
                if os.path.isdir(s):
                    self.copy_files(s, d)
                else:
                    # Normalizar os caminhos
                    s_normalized = os.path.normpath(s)
                    d_normalized = os.path.normpath(d)
                    if s_normalized != d_normalized:
                        shutil.copy2(s, d)  # Sobrescreve o arquivo no destino
        except Exception as e:
            print(f"Erro ao copiar arquivos: {e}")

    def backup_folder(self, source_folder, backup_base_folder):
        if source_folder == backup_base_folder or backup_base_folder.startswith(source_folder):
            print(f'Erro: A pasta de destino ({backup_base_folder}) não pode ser a mesma que a pasta de origem ({source_folder}) ou estar dentro dela.')
            return
        
        folder_name = os.path.basename(source_folder)
        backup_folder = os.path.join(backup_base_folder, folder_name)

        try:
            self.copy_files(source_folder, backup_folder)
            print(f'Backup de {source_folder} concluído com sucesso em {backup_folder}')
        except Exception as e:
            print(f'Erro ao fazer backup de {source_folder}: {e}')

    def daily_backup(self):
        print(f'Iniciando backup diário às {datetime.now()}')
        self.backup_folder(self.source_folder1.get(), self.backup_base_folder.get())
        self.backup_folder(self.source_folder2.get(), self.backup_base_folder.get())
        print(f'Backup diário concluído às {datetime.now()}')

    def start_scheduler(self):
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(1)

        scheduler_thread = Thread(target=run_scheduler)
        scheduler_thread.daemon = True
        scheduler_thread.start()

if __name__ == "__main__":
    root = tk.Tk()
    app = BackupApp(root)
    root.mainloop()
