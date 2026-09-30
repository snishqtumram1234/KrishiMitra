"""Offline tests on synthetic data: mapping, splits, and a tiny train -> evaluate -> export smoke run."""

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from PIL import Image

ML = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ML))

import download  # noqa: E402
import prepare_data  # noqa: E402
from classes import CLASSES, SOURCE_MAP, mignoni_source, source_caps  # noqa: E402


def make_img(path: Path, color: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (80, 60), (color, 255 - color, 128)).save(path)


@pytest.fixture
def raw_tree(tmp_path):
    raw = tmp_path / "raw"
    for i, src in enumerate(SOURCE_MAP):
        for j in range(14):
            make_img(raw / src / f"{j:05d}.jpg", (i * 25 + j) % 256)
    return raw


def test_mapping_covers_all_five_classes_and_no_extras():
    assert set(SOURCE_MAP.values()) == set(CLASSES)


def test_mignoni_healthy_is_not_used():
    assert mignoni_source("Images of Soybean Leaves/Healthy/img1.jpg") is None
    assert mignoni_source("x/Caterpillar/1.jpg") == "mignoni/caterpillar"
    assert mignoni_source("x/Diabrotica speciosa/1.jpg") == "mignoni/diabrotica"


def test_source_caps_split_budget_per_label():
    caps = source_caps(1500)
    assert caps["asdid/healthy"] == 1500 and caps["asdid/soybean_rust"] == 1500
    assert caps["asdid/frogeye"] == 500  # 3 leaf-spot sources
    assert caps["mignoni/caterpillar"] == 750  # 2 insect sources
    assert caps["asdid/downey_mildew"] == 500  # 3 unknown sources


def test_prepare_and_split_are_stratified_and_disjoint(raw_tree, tmp_path):
    rows = prepare_data.collect(raw_tree, tmp_path / "proc", images_per_class=30, seed=1)
    parts = prepare_data.split(rows, seed=1, val=0.15, test=0.15)
    paths = [set(r["path"] for r in p) for p in parts.values()]
    assert not (paths[0] & paths[1]) and not (paths[0] & paths[2]) and not (paths[1] & paths[2])
    assert sum(len(p) for p in parts.values()) == len(rows)
    for part in parts.values():
        assert {r["label"] for r in part} == set(CLASSES)


def test_unreadable_images_are_dropped(raw_tree, tmp_path):
    (raw_tree / "asdid/healthy/00000.jpg").write_bytes(b"not an image")
    rows = prepare_data.collect(raw_tree, tmp_path / "proc", images_per_class=30, seed=1)
    assert rows and all(Path(r["path"]).exists() for r in rows)


@pytest.mark.parametrize("bad", ["heldout", "indian_soybean", "Maharashtra"])
def test_heldout_data_is_refused(tmp_path, bad):
    with pytest.raises(SystemExit):
        prepare_data.check_not_forbidden(tmp_path / bad / "asdid" / "healthy")


def test_extract_subset_caps_and_classifies(tmp_path):
    zpath = tmp_path / "m.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        for i in range(10):
            for folder in ("Caterpillar", "Diabrotica speciosa", "Healthy"):
                z.writestr(f"Soy/{folder}/{i}.jpg", b"data")
        z.writestr("Soy/readme.txt", "hi")
    caps = {"mignoni/caterpillar": 4, "mignoni/diabrotica": 3}
    counts = download.extract_subset(zpath, tmp_path / "raw", mignoni_source, caps, seed=0)
    assert counts == caps
    assert len(list((tmp_path / "raw/mignoni/caterpillar").iterdir())) == 4
    assert not (tmp_path / "raw/mignoni/healthy").exists()


def test_tiny_train_evaluate_export_smoke(raw_tree, tmp_path):
    pytest.importorskip("torch")
    pytest.importorskip("onnxruntime")
    proc, splits, art = tmp_path / "proc", tmp_path / "splits", tmp_path / "art"
    run = lambda *args: subprocess.run([sys.executable, *args], cwd=ML, check=True, capture_output=True, text=True)  # noqa: E731

    run("prepare_data.py", "--raw", str(raw_tree), "--processed", str(proc), "--splits", str(splits),
        "--images-per-class", "30")
    run("train.py", "--splits", str(splits), "--out", str(art), "--epochs", "1", "--batch-size", "8",
        "--workers", "0", "--no-pretrained")
    run("evaluate.py", "--ckpt", str(art / "best.pt"), "--csv", str(splits / "test.csv"), "--out", str(art),
        "--workers", "0")
    out = run("export_onnx.py", "--ckpt", str(art / "best.pt"), "--out", str(art)).stdout

    assert "ONNX parity OK" in out
    m = json.loads((art / "metrics_test.json").read_text())
    assert set(m["per_class"]) == set(CLASSES)
    assert set(m["confidence_tiers"]) == {"low (<0.60)", "mid (0.60-0.85)", "high (>0.85)"}
    assert (art / "soybean_vision.onnx").exists() and (art / "confusion_matrix_test.csv").exists()
