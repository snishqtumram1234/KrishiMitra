"""Export the checkpoint to ONNX and verify it against PyTorch.

The exported graph takes float32 RGB in [0,1], shape (N,3,224,224), does the ImageNet
normalisation itself and returns softmax probabilities in CLASSES order. So the backend only
needs to resize to 224x224 and scale to [0,1].

  python export_onnx.py --ckpt artifacts/best.pt --out artifacts
  python export_onnx.py --copy-to ../backend/models
"""

import argparse
import json
import shutil
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch
from torch import nn

from train import MEAN, SIZE, STD, build_model


class Exported(nn.Module):
    def __init__(self, model: nn.Module):
        super().__init__()
        self.model = model
        self.register_buffer("mean", torch.tensor(MEAN).view(1, 3, 1, 1))
        self.register_buffer("std", torch.tensor(STD).view(1, 3, 1, 1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return torch.softmax(self.model((x - self.mean) / self.std), dim=1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", type=Path, default=Path("artifacts/best.pt"))
    ap.add_argument("--out", type=Path, default=Path("artifacts"))
    ap.add_argument("--copy-to", type=Path, help="e.g. ../backend/models")
    a = ap.parse_args()

    ck = torch.load(a.ckpt, map_location="cpu")
    model = build_model(ck["arch"], len(ck["classes"]), pretrained=False)
    model.load_state_dict(ck["state_dict"])
    wrapped = Exported(model).eval()

    a.out.mkdir(parents=True, exist_ok=True)
    onnx_path = a.out / "soybean_vision.onnx"
    dummy = torch.rand(1, 3, SIZE, SIZE)
    torch.onnx.export(wrapped, dummy, str(onnx_path), input_names=["image"], output_names=["probs"],
                      dynamic_axes={"image": {0: "batch"}, "probs": {0: "batch"}}, opset_version=17,
                      dynamo=False)

    # parity check
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    x = torch.rand(4, 3, SIZE, SIZE)
    with torch.no_grad():
        ref = wrapped(x).numpy()
    got = sess.run(None, {"image": x.numpy()})[0]
    diff = float(np.abs(ref - got).max())
    assert diff < 1e-3, f"ONNX/PyTorch mismatch: {diff}"
    print(f"ONNX parity OK (max diff {diff:.2e}), size {onnx_path.stat().st_size / 1e6:.1f} MB")

    meta = {"classes": ck["classes"], "arch": ck["arch"], "input": f"float32 RGB [0,1] NCHW {SIZE}x{SIZE}",
            "output": "softmax probabilities in `classes` order"}
    (a.out / "soybean_vision.json").write_text(json.dumps(meta, indent=2))

    if a.copy_to:
        a.copy_to.mkdir(parents=True, exist_ok=True)
        for name in ("soybean_vision.onnx", "soybean_vision.json"):
            shutil.copy(a.out / name, a.copy_to / name)
        print(f"Copied to {a.copy_to}")


if __name__ == "__main__":
    main()
