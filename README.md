# fleet-monitor

> Inventário de hardware por WMI, previsão de esgotamento de disco com regressão linear e alertas em Slack/ClickUp para um parque de máquinas Windows.

![CI](https://img.shields.io/github/actions/workflow/status/Jimhow-01/fleet-monitor/ci.yml?branch=main&label=CI&logo=githubactions&logoColor=white) ![Tests](https://img.shields.io/badge/tests-17%20passing-brightgreen?logo=pytest&logoColor=white) ![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json) ![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white) ![Platform](https://img.shields.io/badge/platform-Windows-lightgrey) ![Status](https://img.shields.io/badge/status-portfolio%20showcase-lightgrey)

![Python](https://img.shields.io/badge/Python-377641?logo=python&logoColor=white) ![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E) ![WMI](https://img.shields.io/badge/WMI-0078D4) ![Slack](https://img.shields.io/badge/Slack-4A154B?logo=slack&logoColor=white) ![ClickUp](https://img.shields.io/badge/ClickUp-7B68EE) ![Firebase](https://img.shields.io/badge/Firebase-FFA100?logo=firebase&logoColor=white)

## O problema

Estúdio tem muitos PCs e ninguém sabe o estado deles até alguém reclamar. Estes agentes respondem três perguntas sem ninguém perguntar: **o que existe**, **quanto espaço resta** e **quando vai acabar**.

## Arquitetura

```
fleet-monitor/
├── inventory/    agentes de inventario (WMI + psutil -> Realtime Database)
├── disk/         scanner diario + previsao por regressao linear
├── alerts/       job agendado: disco + vencimento de tarefas -> Slack/ClickUp
├── backup/       backup agendado com GUI e verificacao de espelho
├── resilience/   reboot automatico apos queda prolongada de internet
└── scripts/      wrappers .bat para o Task Scheduler
```

## Destaques técnicos

### 🔍 Inventário por WMI — `inventory/hardware_reporter.py`

Coleta `Win32_Processor`, `Win32_BaseBoard`, `Win32_PhysicalMemory` (capacidade, velocidade e serial dos pentes), `Win32_VideoController` e `Win32_DiskDrive`. Faz o **mapeamento lógico→físico** navegando os associators do WMI (`Win32_DiskDriveToDiskPartition` e `Win32_LogicalDiskToPartition`) para reportar modelo e índice de cada unidade — não só a letra do drive.

### 🎯 Identidade estável de máquina

Em vez de confiar no nome do PC (que colide), usa o **MAC da interface primária**, com prioridade explícita `eth0 / enp / eno / ens / Ethernet / Wi-Fi` e fallback.

### 📉 Previsão de capacidade — `disk/disk_forecast.py`

Série temporal diária do espaço usado + `LinearRegression` do scikit-learn sobre a fração ocupada, extrapolando em quantos dias o disco chega ao ponto em que restam **250 GB livres** (`calcular_porcentagem_hd(total, 250)`), com alerta escalonado:

| Dias estimados | Ação |
|---|---|
| < 30 | 🚨 URGENTE |
| < 60 | ⚠️ planejar upgrade |
| ≥ 60 | com folga |

Só faz previsão quando há mais de 2 observações (`len(drive_percentages) > 2`) — evita extrapolar a partir de dois pontos.

### 🔁 Resiliência de coleta

`fleet_agent_regional.py` faz 3 tentativas com `raise_for_status()` por envio, com `time.sleep(5)` fixo entre elas (não é backoff exponencial) e `requests.put` **sem timeout** — falha de rede pode travar o loop. `hardware_reporter.py` usa `requests.put` com `timeout=15` e trata falha por `response.ok`, mostrando o erro na GUI.

### 🛡️ Auto-recuperação — `resilience/auto_reboot_on_outage.py`

Ping a cada 60s; 30 minutos contínuos sem internet → reboot forçado. Para estações em área de produção com rede instável, que precisam voltar sozinhas sem técnico. (NOTE: a versão original somava `+= 2` por iteração mas dormia 60s, o que fazia o limiar de 1800 ser atingido em ~15 minutos reais em vez de 30. Corrigido aqui para somar o intervalo real do loop.)

## 📌 Sobre as variantes em `inventory/`

Há versões sucessivas do mesmo agente (`fleet_agent`, `fleet_agent_v2`, `fleet_agent_regional`, `hardware_reporter_v1`). Mantive as variantes de propósito: elas mostram a evolução do código. Mas a evolução é menos linear do que parece — **o mapeamento lógico→físico de disco (`Win32_DiskDriveToDiskPartition`/`Win32_LogicalDiskToPartition`) e a identificação por MAC existem só em `hardware_reporter.py`**; as variantes antigas não têm nenhum dos dois. O que `fleet_agent_regional.py` acrescenta é apenas o laço de 3 tentativas. **A versão canônica é `inventory/hardware_reporter.py`.**

## Testes e lint

```bash
pip install -r requirements.txt -r requirements-dev.txt
ruff check .          # lint
pytest                # 17 testes
```

O CI roda lint, `compileall` e pytest em `windows-latest` (Python 3.11 e 3.12) a cada
push — Windows porque este código usa `pywin32`, `wmi` e `winreg`, que não existem em Linux.

A configuração do ruff está em `pyproject.toml` e declara, com o motivo de cada uma, as
regras que **não** estou corrigindo agora. Prefiro isso a escolher um subconjunto de regras
que passa por acaso.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # Windows (cp .env.example .env em Linux/macOS)
```

### Como rodar

```bash
# inventario de hardware via WMI (variante canonica)
python inventory/hardware_reporter.py

# agente residente (coleta e envia ao servidor)
python inventory/fleet_agent.py
python inventory/fleet_agent_regional.py

# coleta de espaco em disco - gera disk/disk_space.json
python disk/hdd_scanner.py

# previsao de esgotamento a partir do JSON gerado acima
python disk/disk_forecast.py

# alertas de task no Slack
python alerts/task_alerts.py

# verificacao de espelho de backup
python backup/verify_mirror.py <origem> <destino>

# monitor de queda de rede com reboot automatico
python resilience/auto_reboot_on_outage.py
```

Há também `scripts/run_hdd_scanner.bat` e `scripts/run_forecast.bat` para agendar
no Agendador de Tarefas do Windows.

Ordem que importa: `hdd_scanner.py` gera as leituras que `disk_forecast.py` consome.

### Variáveis de ambiente

| Variável | Descrição |
|---|---|
| `FIREBASE_DATABASE_URL` | ver `.env.example` |
| `SLACK_BOT_TOKEN` | ver `.env.example` |
| `SLACK_CHANNEL_ID` | ver `.env.example` |
| `CLICKUP_API_TOKEN` | ver `.env.example` |
| `CLICKUP_LIST_ID` | ver `.env.example` |
| `AGENT_BINARY_PATH` | ver `.env.example` |

---

## ⚠️ Fragilidades conhecidas (declaradas, não escondidas)

1. **Persistência não declarada no original.** `fleet_agent.py` e `fleet_agent_v2.py` copiam o próprio `.exe` de `~/Downloads` para a pasta **Startup** do Windows (auto-início). Não há instalador formal nem desinstalação. Em portfólio isso precisa estar escrito, não descoberto por quem lê o código.
2. **Coleta de dado de navegador.** `hardware_reporter.py` (a variante canônica) lê o `Local State` do Chrome e extrai **nomes de perfil e e-mails das contas logadas na estação**, e isso vai junto para o Firebase. É coleta de dado pessoal de terceiro — o módulo está marcado com `NOTE` no fonte e a chamada pode ser removida sem afetar o inventário de hardware.
3. **Bug de contagem no auto-reboot** (corrigido aqui): contador somava 2s por iteração com `sleep(60)`, então o limiar de 30 minutos era atingido em ~15 minutos reais.
4. **`requests.put` sem timeout** em `fleet_agent_regional.py`, e retry com `sleep(5)` fixo, não backoff.
5. **`hdd_scanner.py` e `disk_forecast.py` assumem disco único** e extrapolam a regressão linear para 250 GB livres — a previsão é indicativa, não confiável para decisão de compra.

---

## ⚠️ Sobre o que isto é — e sobre titularidade

São **scripts internos de TI** escritos durante meu trabalho em um estúdio de jogos, **sanitizados** para publicação: tokens, senhas, hosts internos, IPs, nomes de projeto e dados de terceiros foram substituídos por variáveis de ambiente ou placeholders. O estúdio não é nomeado aqui de propósito.

Duas coisas que quero deixar claras em vez de deixar você descobrir:

- **Não estou reivindicando direitos sobre este código.** Parte dele foi produzida como funcionário, e direitos sobre trabalho de empregador pertencem ao empregador. Publico como demonstração de como eu resolvi os problemas — para leitura e estudo, não como software livre. Não há licença concedida (ver `LICENSE`).
- **Não são produtos prontos para produção.** São demonstrações de abordagem técnica, com limitações declaradas nas seções acima. Copie `.env.example` para `.env` e preencha antes de rodar qualquer coisa — e rode só contra infraestrutura sua.
