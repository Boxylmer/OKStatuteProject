import os
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
from sentence_transformers import CrossEncoder


def ensure_embedding_model(
    model_name: str,
    model_dir: str | Path = Path("data") / "embedding_models",
    verbose=False,
):
    model_path = os.path.join(model_dir, model_name.replace("/", "_"))
    if not os.path.exists(model_path):
        if verbose:
            print(f"Downloading model {model_name} to {model_path}...")
        model = SentenceTransformer(model_name)
        model.save(model_path)
    else:
        if verbose:
            print(f"Model {model_name} already present at {model_path}")
    return model_path


def ensure_cross_encoder_model(
    model_name: str,
    model_dir: Path = Path("data") / "crossencoder_models",
    verbose=False,
) -> Path:
    model_path = model_dir / model_name.replace("/", "_")
    if not model_path.exists():
        if verbose:
            print(f"Downloading CrossEncoder model {model_name} to {model_path}")
        model = CrossEncoder(model_name)
        model.save(str(model_path))
    else:
        if verbose:
            print(f"CrossEncoder model already present at {model_path}")
    return model_path


def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
