from pathlib import Path

from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from sentence_transformers import CrossEncoder
from transformers import AutoTokenizer

from rag.utils import (
    ensure_embedding_model,
    ensure_cross_encoder_model,
    cosine_similarity,
)
from statute.statute import Statute


class StatuteRAG:
    QUERY_PREFIX = "query:"
    PASSAGE_PREFIX = "passage:"

    def __init__(
        self,
        db_path: Path | None = Path("data") / "rag_db",
        embedding_model_name: str = "sentence-transformers/all-mpnet-base-v2",
        reranking_model_name: str | None = None,
        data_dir: Path = Path("data"),
        collection_name="statutes",
        verbose=False,
    ):
        self.embedding_model_path = ensure_embedding_model(
            embedding_model_name, data_dir
        )
        self.tokenizer = AutoTokenizer.from_pretrained(str(self.embedding_model_path))
        self.max_tokens = (
            self.tokenizer.model_max_length
            if self.tokenizer.model_max_length < 1000000
            else 512
        )
        self.embedding_model = HuggingFaceEmbeddings(
            model_name=str(self.embedding_model_path)
        )
        if verbose:
            print(f"Embedding model loaded: {embedding_model_name}")

        if reranking_model_name:
            self.reranking_model_path = ensure_cross_encoder_model(
                reranking_model_name, data_dir
            )
            self.reranking_model = CrossEncoder(
                model_name_or_path=self.reranking_model_path
            )
            if verbose:
                print(f"Reranker model loaded: {reranking_model_name}")

        else:
            self.reranking_model = None

        self.collection_name = collection_name

        self.QUERY_TOKEN_PADDING = self._get_token_count(self.QUERY_PREFIX)
        self.PASSAGE_TOKEN_PADDING = self._get_token_count(self.PASSAGE_PREFIX)

        if db_path:
            persist_directory = str(db_path)
        else:
            persist_directory = None

        self.vectorstore = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embedding_model,
            persist_directory=persist_directory,
            client_settings=Settings(anonymized_telemetry=False),
        )

        if verbose:
            print(f"StatuteRAG initialized with {self.max_tokens} token length.")

    def _split_long_chunk(
        self,
        text: str,
        metadata: dict,
        token_padding=0,
        chunk_overlap=20,
        append_token_count_to_metadata=False,
    ):
        splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
            self.tokenizer,
            chunk_size=self.max_tokens - token_padding,
            chunk_overlap=chunk_overlap,
        )
        split_texts = []
        split_metadatas = []

        token_count = self._get_token_count(text)

        if append_token_count_to_metadata:
            metadata["token_count"] = token_count

        if token_count <= self.max_tokens:
            split_texts.append(text)
            split_metadatas.append(metadata)
        else:
            chunks = splitter.split_text(text)
            print(
                f"Text for citation {metadata.get('citation')} exceeds the maximum ({self.max_tokens}) tokens with {token_count} tokens, splitting into {len(chunks)} chunks."
            )
            for i, chunk in enumerate(chunks):
                new_meta = metadata.copy()
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
            max_length=1e30,
        )["length"][0]
        return token_count

    def ingest_statute(self, st: Statute, verbose=False, exist_ok: bool = False):
        citation = st.parse_citation()
        title = st.full_title
        section = st.full_section
        full_text = st.formatted_text()

        existing = self.vectorstore.get(where={"citation": citation})["ids"]
        if existing and not exist_ok:
            raise ValueError(f"Statute with citation '{citation}' already exists.")
        elif existing and exist_ok and verbose:
            print(
                f"Statute with citation '{citation}' already exists. Skipping ingestion."
            )
            return

        base_meta = {
            "citation": citation,
            "title": title,
            "section": section,
        }

        texts, metadatas = self._split_long_chunk(
            full_text,
            base_meta,
            token_padding=self.PASSAGE_TOKEN_PADDING,
            append_token_count_to_metadata=True,
        )

        ids = [f"{citation}_chunk{i}" for i in range(len(texts))]

        self._ingest(texts, metadatas, ids, verbose=verbose)

    def query(
        self, query_text: str, top_k: int = 3, rerank_if_available=True, verbose=False
    ):
        """
        Query up to top_k entries from the statute database.


        returns a list of results where results are (content, r.metadata, r.id)
        """
        formatted_query_text = f"{self.QUERY_PREFIX} {query_text}"
        raw_results = self.vectorstore.similarity_search(formatted_query_text, k=top_k)

        clean_results: list[tuple[str, dict, str | None]] = []

        for r in raw_results:
            content = r.page_content
            if content.startswith(self.PASSAGE_PREFIX):
                content = content[len(self.PASSAGE_PREFIX) :].lstrip()
            clean_results.append((content, r.metadata, r.id))

        if rerank_if_available and self.reranking_model:
            return self._rerank(query_text, clean_results, verbose=verbose)

        if verbose:
            query_embedding = self.embedding_model.embed_query(query_text)
            scores = [
                cosine_similarity(
                    self.embedding_model.embed_query(res[0]), query_embedding
                )
                for res in clean_results
            ]
            res_scores = [
                (round(float(score), ndigits=2), result[0][0:10])
                for result, score in zip(clean_results, scores)
            ]
            print(f"RAG results (no reranking): {res_scores}")

        return clean_results

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

        formatted_texts = [f"{self.PASSAGE_PREFIX} {text}" for text in texts]

        self.vectorstore.add_texts(formatted_texts, metadatas=metadatas, ids=ids)
        if verbose:
            print(f"Ingested {len(texts)} documents into ChromaDB for ids {ids}.")

    def _rerank(
        self, query: str, results: list[tuple[str, dict, str | None]], verbose=False
    ):
        inputs = [(query, text) for text, _, _ in results]
        scores = self.reranking_model.predict(
            inputs,
            show_progress_bar=verbose,
        )
        scored_results = sorted(zip(scores, results), key=lambda x: x[0], reverse=True)

        if verbose:
            res_scores = [
                (round(float(score), ndigits=2), result[0][0:10])
                for score, result in scored_results
            ]
            print(f"RAG results (with reranking): {res_scores}")

        return [res for _, res in scored_results]

    def reset(self):
        self.vectorstore.reset_collection()
