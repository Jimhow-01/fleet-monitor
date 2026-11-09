import json
import sys
from pathlib import Path

from sklearn.linear_model import LinearRegression

URGENT_DAYS = 30
WATCH_DAYS = 60
HEADROOM_GB = 250


def calcular_porcentagem_usada(total_hd_bytes, valor_gb):
    """Fração do disco OCUPADA por `valor_gb`.

    Args:
        total_hd_bytes (int): capacidade total da unidade, em bytes.
        valor_gb (float): volume a converter.

    Returns:
        float: fração ocupada (1.0 == unidade cheia).
    """
    valor_bytes = valor_gb * (1024 ** 3)
    return valor_bytes / total_hd_bytes


def calcular_porcentagem_hd(total_hd_bytes, valor_gb):
    """Fração do disco LIVRE depois de ocupar `valor_gb`.

    Mantém o nome e o sinal originais para não quebrar quem já chama a função.
    """
    return 1 - calcular_porcentagem_usada(total_hd_bytes, valor_gb)


def collect_drive_percentages(data, letter):
    """Série de frações ocupadas de uma unidade, na ordem das leituras.

    Args:
        data (dict): JSON gerado por `hdd_scanner.py` (`TotalSpace` e `TimeLine`).
        letter (str): letra da unidade, ex. ``"C:"``.

    Returns:
        list[float]: uma fração por leitura em que a unidade aparece.
    """
    total = data["TotalSpace"][letter]
    return [sizes[letter] / total for sizes in data["TimeLine"].values() if letter in sizes]


def forecast_days_until_full(series, total_hd_bytes):
    """Extrapola por regressão linear quando restarão `HEADROOM_GB` livres.

    NOTE: a regressão é sobre a fração ocupada contra o índice da leitura, então
    assume crescimento linear e leituras com intervalo constante (uma por dia).
    O alvo são HEADROOM_GB livres, não 100% cheio — a ideia é avisar antes de
    encostar, não no momento de esgotar. É indicativo, não serve para decisão
    de compra sem olhar a série.

    Args:
        series (list[float]): frações ocupadas em ordem cronológica.
        total_hd_bytes (int): capacidade da unidade.

    Returns:
        float | None: dias até o alvo; None se a série tem pontos demais para
        regressão ou se a tendência não é de crescimento (coeficiente <= 0).
    """
    if len(series) <= 2:
        return None

    model = LinearRegression().fit([[i] for i in range(len(series))], series)
    slope = model.coef_[0]
    if slope <= 0:
        return None

    target = calcular_porcentagem_usada(total_hd_bytes, HEADROOM_GB)
    return (target - model.intercept_) / slope


def classify(days):
    """Rótulo de prioridade para um prazo em dias."""
    if days < URGENT_DAYS:
        return "URGENTE"
    if days < WATCH_DAYS:
        return "atencao"
    return "folga"


def build_report(data):
    """Relatório de previsão para todas as unidades do JSON.

    Returns:
        list[dict]: ``{'letter', 'readings', 'days', 'priority'}`` por unidade
        com previsão viável.
    """
    report = []
    for letter, total in data["TotalSpace"].items():
        series = collect_drive_percentages(data, letter)
        days = forecast_days_until_full(series, total)
        if days is None:
            continue
        report.append({
            "letter": letter,
            "readings": len(series),
            "days": days,
            "priority": classify(days),
        })
    return report


def render_report(report, total_readings):
    """Formata o relatório em texto."""
    lines = [f"\nTotal de {total_readings} dias de dados guardados\n"]
    for r in report:
        if r["priority"] == "URGENTE":
            lines.append(f'HD {r["letter"]} precisa de upgrade URGENTE em: {r["days"]:.2f} dias')
        elif r["priority"] == "atencao":
            lines.append(f'HD {r["letter"]} precisa receber upgrade em: {r["days"]:.2f} dias')
        else:
            lines.append(f'HD {r["letter"]} com folga vai precisar de um upgrade em: {r["days"]:.2f} dias')
    return "\n".join(lines)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    source = Path(argv[0]) if argv else Path(__file__).with_name("disk_space.json")
    if not source.exists():
        print(f"Arquivo de leituras não encontrado: {source}")
        print("Rode primeiro disk/hdd_scanner.py para gerar as leituras.")
        return 1

    with open(source, encoding="utf-8") as f:
        data = json.load(f)

    report = build_report(data)
    total_readings = max((len(v) for v in data["TimeLine"].values()), default=0)
    print(render_report(report, total_readings))
    return 0


if __name__ == "__main__":
    sys.exit(main())
