"""Testes da previsao de esgotamento de disco.

O modulo importa scikit-learn. Em algumas maquinas Windows o pacote instala mas
nao carrega (falta a DLL de compilador `vcomp140.dll`), e o erro ai e
FileNotFoundError, nao ModuleNotFoundError - por isso o skip usa try/except
amplo em vez de importorskip.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "disk"))

try:
    import disk_forecast  # noqa: E402
except Exception as exc:  # sklearn indisponivel neste ambiente
    disk_forecast = None
    pytest.skip(
        f"disk_forecast requer scikit-learn funcional ({type(exc).__name__})",
        allow_module_level=True,
    )

GB = 1024 ** 3


class TestPorcentagem:
    def test_full_disk_is_one(self):
        assert disk_forecast.calcular_porcentagem_usada(100 * GB, 100) == pytest.approx(1.0)

    def test_half_used_is_half(self):
        assert disk_forecast.calcular_porcentagem_usada(100 * GB, 50) == pytest.approx(0.5)

    def test_free_fraction_is_complement(self):
        """calcular_porcentagem_hd mantem o sinal original (fracao LIVRE)."""
        used = disk_forecast.calcular_porcentagem_usada(200 * GB, 60)
        free = disk_forecast.calcular_porcentagem_hd(200 * GB, 60)
        assert used + free == pytest.approx(1.0)


class TestForecast:
    def test_returns_none_for_too_few_readings(self):
        assert disk_forecast.forecast_days_until_full([0.1, 0.2], 100 * GB) is None

    def test_returns_none_when_disk_is_not_growing(self):
        """Serie plana ou decrescente nao tem prazo de esgotamento."""
        assert disk_forecast.forecast_days_until_full([0.5, 0.5, 0.5, 0.5], 100 * GB) is None
        assert disk_forecast.forecast_days_until_full([0.7, 0.6, 0.5, 0.4], 100 * GB) is None

    def test_linear_growth_hits_the_headroom_target(self):
        """Cresce 1% por dia; alvo = 250 GB livres num disco de 500 GB (50% ocupado).

        Regressao exata dos 5 pontos: coef_ = 0.01, intercept_ = 0.10
        (a serie passa por 0.10 em x=0), entao (0.50 - 0.10) / 0.01 = 40 dias.
        """
        series = [0.10, 0.11, 0.12, 0.13, 0.14]
        days = disk_forecast.forecast_days_until_full(series, 500 * GB)
        assert days == pytest.approx(40.0, abs=0.5)

    def test_faster_growth_gives_shorter_deadline(self):
        slow = disk_forecast.forecast_days_until_full([0.10, 0.11, 0.12, 0.13], 500 * GB)
        fast = disk_forecast.forecast_days_until_full([0.10, 0.20, 0.30, 0.40], 500 * GB)
        assert fast < slow


class TestClassify:
    def test_thresholds(self):
        assert disk_forecast.classify(10) == "URGENTE"
        assert disk_forecast.classify(29) == "URGENTE"
        assert disk_forecast.classify(30) == "atencao"
        assert disk_forecast.classify(59) == "atencao"
        assert disk_forecast.classify(60) == "folga"
        assert disk_forecast.classify(400) == "folga"


class TestBuildReport:
    def sample(self):
        return {
            "TotalSpace": {"C:": 500 * GB, "D:": 1000 * GB},
            "TimeLine": {
                "01-01-2026": {"C:": 0.10 * 500 * GB, "D:": 0.10 * 1000 * GB},
                "02-01-2026": {"C:": 0.15 * 500 * GB, "D:": 0.11 * 1000 * GB},
                "03-01-2026": {"C:": 0.20 * 500 * GB, "D:": 0.12 * 1000 * GB},
                "04-01-2026": {"C:": 0.25 * 500 * GB, "D:": 0.13 * 1000 * GB},
            },
        }

    def test_reports_every_drive(self):
        report = disk_forecast.build_report(self.sample())
        assert {r["letter"] for r in report} == {"C:", "D:"}

    def test_report_entries_are_classified(self):
        for r in disk_forecast.build_report(self.sample()):
            assert r["priority"] in {"URGENTE", "atencao", "folga"}
            assert r["readings"] == 4

    def test_drive_absent_from_timeline_is_skipped(self):
        data = self.sample()
        data["TotalSpace"]["E:"] = 250 * GB  # sem leituras
        report = disk_forecast.build_report(data)
        assert "E:" not in {r["letter"] for r in report}

    def test_render_report_is_human_readable(self):
        text = disk_forecast.render_report(disk_forecast.build_report(self.sample()), 4)
        assert "4 dias de dados" in text
        assert "HD C:" in text and "HD D:" in text

    def test_main_reports_missing_input_file(self, tmp_path, capsys):
        rc = disk_forecast.main([str(tmp_path / "nao-existe.json")])
        assert rc == 1
        assert "não encontrado" in capsys.readouterr().out
