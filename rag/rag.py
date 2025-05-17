from pathlib import Path

from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from transformers import AutoTokenizer

from rag.utils import download_embedding_model
from statute.statuteparser import StatuteParser



class StatuteRAG:

    QUERY_PREFIX = "query: "
    PASSAGE_PREFIX = "passage: "

    def __init__(
        self,
        db_path: Path | None = Path("data") / "rag_db",
        model_name="nlpaueb/legal-bert-base-uncased",
        model_path: Path = Path("data") / "embedding_models",
        persist=True,
    ):
        self.model_path = download_embedding_model(model_name, model_path)
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        self.max_tokens = (
            self.tokenizer.model_max_length
            if self.tokenizer.model_max_length < 1000000
            else 512
        )
        self.embeddings = HuggingFaceEmbeddings(model_name=self.model_path)
        self.collection_name = "statutes"

        self.QUERY_TOKEN_PADDING = self._get_token_count(self.QUERY_PREFIX)
        self.PASSAGE_TOKEN_PADDING = self._get_token_count(self.PASSAGE_PREFIX)
        
        persist_directory = None
        if persist:
            persist_directory = str(db_path)
        
        self.vectorstore = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=persist_directory,
            client_settings=Settings(anonymized_telemetry=False),
        )

    def _split_long_chunks(self, texts: list[str], metadatas: list[dict], token_padding=0):
        splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
            self.tokenizer, chunk_size=self.max_tokens - token_padding, chunk_overlap=20
        )
        split_texts = []
        split_metadatas = []

        for text, meta in zip(texts, metadatas):
            token_count = self._get_token_count(text)
            if token_count <= self.max_tokens:
                split_texts.append(text)
                split_metadatas.append(meta)
            else:
                print(
                    f"Text for citation {meta.get('citation')} exceeds the maximum ({self.max_tokens}) tokens with {token_count} tokens, splitting."
                )
                chunks = splitter.split_text(text)
                for i, chunk in enumerate(chunks):
                    new_meta = meta.copy()
                    new_meta["chunk_index"] = i
                    split_texts.append(chunk)
                    split_metadatas.append(new_meta)

        return split_texts, split_metadatas

    def _get_token_count(self, text: str):
        token_count = self.tokenizer(
            text,
            return_attention_mask=False,
            return_token_type_ids=False,
            return_length=True,
            truncation=False,
            max_length=1e30
        )["length"][0]
        return token_count

    def _ingest(
        self,
        texts: list[str],
        metadatas: list[dict] | None = None,
        ids: list[str] | None = None,
        verbose=False,
    ):
        if metadatas is None:
            metadatas = [{} for _ in texts]

        if ids is None:
            ids = [f"doc_{i}" for i in range(len(texts))]

        formatted_texts = [f'{self.PASSAGE_PREFIX} {text}' for text in texts]
 
        self.vectorstore.add_texts(formatted_texts, metadatas=metadatas, ids=ids)
        if verbose:
            print(f"Ingested {len(texts)} documents into ChromaDB.")

    def ingest_statute(self, st: StatuteParser, verbose=False):
        citation = st.parse_citation()
        title = st.full_title
        section = st.full_section
        full_text = st.formatted_text()

        base_meta = {
            "citation": citation,
            "title": title,
            "section": section,
        }

        texts, metadatas = self._split_long_chunks([full_text], [base_meta], token_padding=self.PASSAGE_TOKEN_PADDING)

        ids = [f"{citation}_chunk{i}" for i in range(len(texts))]

        self._ingest(texts, metadatas, ids, verbose=verbose)

    def query(self, query_text: str, top_k: int = 3):
        formatted_query_text = f"{self.QUERY_PREFIX} {query_text}"
        results = self.vectorstore.similarity_search(formatted_query_text, k=top_k)

        return [(r.page_content, r.metadata, r.id) for r in results]
