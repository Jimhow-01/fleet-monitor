"""Testes da verificacao de espelho de backup (filecmp, stdlib pura)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backup"))

import verify_mirror  # noqa: E402


def test_get_all_files_walks_recursively(tmp_path):
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    sub = tmp_path / "sub" / "deep"
    sub.mkdir(parents=True)
    (sub / "b.txt").write_text("b", encoding="utf-8")
    found = verify_mirror.get_all_files(str(tmp_path))
    names = sorted(Path(p).name for p in found)
    assert names == ["a.txt", "b.txt"]


def test_compare_files_detects_content_difference(tmp_path):
    a, b = tmp_path / "a.bin", tmp_path / "b.bin"
    a.write_bytes(b"conteudo")
    b.write_bytes(b"conteud0")
    # shallow=False: compara bytes, nao so mtime/tamanho
    assert verify_mirror.compare_files(str(a), str(b)) is False
    b.write_bytes(b"conteudo")
    assert verify_mirror.compare_files(str(a), str(b)) is True


def test_compare_folders_reports_discrepancies_and_uniques(tmp_path):
    src, dst = tmp_path / "src", tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    (src / "same.txt").write_text("igual", encoding="utf-8")
    (dst / "same.txt").write_text("igual", encoding="utf-8")
    (src / "diff.txt").write_text("v1", encoding="utf-8")
    (dst / "diff.txt").write_text("v2", encoding="utf-8")
    (src / "only_src.txt").write_text("s", encoding="utf-8")
    (dst / "only_dst.txt").write_text("d", encoding="utf-8")

    discrepancies, unique_src, unique_dst = verify_mirror.compare_folders(str(src), str(dst))

    assert discrepancies == ["diff.txt"]
    assert unique_src == {"only_src.txt"}
    assert unique_dst == {"only_dst.txt"}


def test_identical_folders_have_no_differences(tmp_path):
    src, dst = tmp_path / "src", tmp_path / "dst"
    for d in (src, dst):
        (d / "x").mkdir(parents=True)
        (d / "x" / "f.txt").write_text("mesmo", encoding="utf-8")
        (d / "g.txt").write_text("mesmo", encoding="utf-8")
    discrepancies, unique_src, unique_dst = verify_mirror.compare_folders(str(src), str(dst))
    assert discrepancies == []
    assert unique_src == set()
    assert unique_dst == set()
