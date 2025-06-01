import os
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
from sentence_transformers import CrossEncoder


def ensure_embedding_model(
    model_name: str,
    data_dir: str | Path = Path("data"),
    verbose=False,
) -> Path:
    embedding_model_dir = Path(data_dir) / "embedding_models"
    model_path = embedding_model_dir / model_name.replace("/", "_")
    if not os.path.exists(model_path):
        if verbose:
            print(f"Downloading model {model_name} to {model_path}...")
        model = SentenceTransformer(model_name)
        model.save(str(model_path))
    else:
        if verbose:
            print(f"Model {model_name} already present at {model_path}")
    return model_path


def ensure_cross_encoder_model(
    model_name: str,
    data_dir: Path = Path("data") / "crossencoder_models",
    verbose=False,
) -> Path:
    cross_encoder_model_dir = Path(data_dir) / "embedding_models"
    model_path = cross_encoder_model_dir / model_name.replace("/", "_")    
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
