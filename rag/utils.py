import os

from pathlib import Path
from sentence_transformers import SentenceTransformer
from huggingface_hub import snapshot_download
from transformers import (
    AutoConfig,
    AutoTokenizer,
    AutoModelForCausalLM,
    AutoModelForSeq2SeqLM,
    pipeline
)
import torch

DATA_PATH = Path("data")



def download_embedding_model(
    model_name: str = "hkunlp/instructor-base",
    model_dir: str | Path = DATA_PATH / "embedding_models",
    verbose=False
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


def download_quantized_model(
    repo_id: str,
    cache_dir: Path = Path("data") / "llm_models",
    verbose: bool = True
) -> Path:
    """
    Downloads a Hugging Face model repo (can include quantized models like GPTQ).
    Returns local path to model directory.
    """
    local_dir = cache_dir / repo_id.replace("/", "_")

    if not (local_dir.exists() and any(local_dir.iterdir())):
        if verbose:
            print(f"⬇️ Downloading model '{repo_id}' to {local_dir}...")
        snapshot_download(
            repo_id=repo_id,
            local_dir=local_dir,
            local_dir_use_symlinks=False,
        )
    else:
        if verbose:
            print(f"📦 Model already exists at {local_dir}")

    return local_dir

# TODO Check and rewrite all of this, this entire function is written by chatgpt as a first-draft. 
def load_transformers_pipeline(
    model_path: str | Path,
    use_gpu: bool = True,
    verbose: bool = True,
):
    """
    Loads a pipeline from a Transformers-compatible quantized model path, including padding and stopping settings.
    """
    model_path = str(model_path)

    # Load model config to determine architecture
    config = AutoConfig.from_pretrained(model_path)
    architectures = config.architectures or []

    # Check model type (CausalLM or Seq2Seq)
    is_seq2seq = any("Seq2Seq" in arch or "T5" in arch or "Bart" in arch for arch in architectures)
    is_causal_lm = any("CausalLM" in arch or "GPT" in arch or "LLaMA" in arch for arch in architectures)

    if not is_seq2seq and not is_causal_lm:
        if verbose:
            print("⚠️ Could not determine architecture. Defaulting to CausalLM.")
        is_causal_lm = True

    # tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_path, use_fast=True)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token  # Use eos_token as pad_token if not available

    model_cls = AutoModelForSeq2SeqLM if is_seq2seq else AutoModelForCausalLM

    # Load the model with or without GPU support, using accelerate's device management
    model = model_cls.from_pretrained(
        model_path,
        device_map="auto" if use_gpu else None,
        torch_dtype=torch.float16 if use_gpu else torch.float32,
        low_cpu_mem_usage=True,
    )

    # Define task type
    task = "text2text-generation" if is_seq2seq else "text-generation"
    
    # Load pipeline without specifying `device`, as accelerate will manage it
    pipe = pipeline(task, model=model, tokenizer=tokenizer)

    # Optionally print the pipeline status
    if verbose:
        print(f"✅ Loaded pipeline: {task} (from {model_path})")

    # Return the pipeline
    return pipe

