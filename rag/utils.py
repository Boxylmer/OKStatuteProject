import os
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer


def ensure_sentencetransformer_model(
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



def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))