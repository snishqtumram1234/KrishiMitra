# ml/ - soybean vision model track

Trains the specialist vision model the orchestrator calls. It is a component, not the product.

## Data
| Dataset | Use | Source |
|---|---|---|
| ASDID (Auburn Soybean Disease Image Dataset) | train | [Dryad](https://doi.org/10.5061/dryad.41ns1rnj3), ~43 GB, needs a free API token |
| Mignoni soybean insect images | train (insect classes only) | [Mendeley Data](https://data.mendeley.com/datasets/bycbh73438/1), no login |
| Indian/Maharashtra soybean dataset | **held-out evaluation only, never train** | not downloaded here |

Class mapping (see [classes.py](classes.py)):

| Category | Sources |
|---|---|
| healthy | ASDID healthy |
| rust_like | ASDID soybean_rust |
| leaf_spot_like | ASDID frogeye, target_spot, cercospora_leaf_blight |
| insect_damage | Mignoni Caterpillar, Diabrotica speciosa |
| unknown | ASDID bacterial_blight, downey_mildew, potassium_deficiency (real problems outside our categories, so the model can say "not one of mine") |

Mignoni's "Healthy" folder is not used. `prepare_data.py` refuses any path containing `heldout`, `indian` or `maharashtra`.

Each category gets an equal image budget (`--images-per-class`, default 1500), split evenly across its sources, so classes are balanced and downloads stay small.

## Pipeline
```
download.py      raw subset per class -> data/raw/<dataset>/<class>/
prepare_data.py  map to 5 categories, verify + shrink to 512px, stratified 70/15/15 -> data/splits/*.csv
train.py         fine-tune MobileNetV3-Large (or --arch efficientnet_b0), best by val macro-F1
evaluate.py      per-class precision/recall/F1, confusion matrix, accuracy per confidence tier
export_onnx.py   ONNX with normalisation + softmax inside, parity-checked with onnxruntime
```

## Train on Colab or Kaggle (free GPU)
1. Zip this folder without `.venv`, `data`, `artifacts`.
2. Open [notebooks/train_colab.ipynb](notebooks/train_colab.ipynb) in Colab, set the runtime to GPU, run the cells top to bottom. (On Kaggle, upload the notebook, enable GPU and Internet, and skip the upload cell.)
3. For ASDID, create a free Dryad account and set `DRYAD_CLIENT_ID` / `DRYAD_CLIENT_SECRET` (the notebook prompts for them). Alternative: download the zips by hand and pass `--asdid-zip-dir`.
4. Download `krishimitra_model.zip` and put `soybean_vision.onnx` + `soybean_vision.json` into `backend/models/` (ONNX files are git-ignored).

## ONNX contract
Input `image`: float32 RGB in [0,1], shape (N,3,224,224). Output `probs`: softmax probabilities in the order of `classes` in `soybean_vision.json`. No preprocessing beyond resize and scaling is needed.

## Local checks (no GPU, no datasets)
```powershell
cd ml
python -m venv .venv; .venv\Scripts\Activate.ps1
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
pytest
```
Tests use synthetic images and run mapping, splits, and a one-epoch train -> evaluate -> export smoke test.

## Caveats
- ASDID has no plant/session IDs, so random splits can leak near-duplicates; test scores will be optimistic. Use the held-out Indian dataset for honest numbers (`evaluate.py --csv <heldout.csv> --name heldout`).
- ASDID is US field imagery and Mignoni is Brazilian; expect a domain gap on Maharashtra photos.
- Softmax confidence is not calibrated probability. Check the confidence-tier table in `metrics_*.json` before trusting the 0.60 / 0.85 thresholds.
