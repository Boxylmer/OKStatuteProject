from pathlib import Path
import warnings

# import chromadb
from chromadb.config import Settings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from rag.utils import download_embedding_model

class StatuteRAG:
    def __init__(
        self,
        db_path: Path = Path("data") / "rag_db",
        model_name="nlpaueb/legal-bert-base-uncased",
        model_dir: Path = Path("data") / "embedding_models",
    ):
        self.model_path = download_embedding_model(model_name, model_dir)
        self.embeddings = HuggingFaceEmbeddings(model_name=self.model_path)
        self.db_path = db_path
        self.collection_name = "rag_collection"
        self.vectorstore = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=str(self.db_path),
            client_settings=Settings(anonymized_telemetry=False),
        )
        

    def ingest(self, texts: list[str], metadatas: list[dict] | None = None, verbose=False):
        if metadatas is None:
            metadatas = [{} for _ in texts]
        ids = [f"doc_{i}" for i in range(len(texts))]
        self.vectorstore.add_texts(texts, metadatas=metadatas, ids=ids)
        if verbose:
            print(f"Ingested {len(texts)} documents into ChromaDB.")

    def query(self, query_text: str, top_k: int = 3):
        results = self.vectorstore.similarity_search(query_text, k=top_k)
        return [(r.page_content, r.metadata) for r in results]
