"""
RAG Service — ChromaDB + Ollama embeddings.
Indexes .md documents and retrieves relevant context for each chat turn.
"""
import os
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

CHROMADB_DIR = os.getenv("CHROMADB_DIR", "./chromadb")
COLLECTION_NAME = "3notes_knowledge"


EMBED_DIMS = 1024  # Matryoshka truncation: 1024 of 4096 dims from qwen3-embedding


def _chunk_text(text: str, max_words: int = 250, overlap_words: int = 30) -> list[str]:
    """Split text into overlapping chunks by paragraphs."""
    paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
    chunks = []
    current_words: list[str] = []

    for para in paragraphs:
        words = para.split()
        if len(current_words) + len(words) > max_words and current_words:
            chunks.append(" ".join(current_words))
            current_words = current_words[-overlap_words:] + words
        else:
            current_words.extend(words)

    if current_words:
        chunks.append(" ".join(current_words))

    return chunks if chunks else [text[:2000]]


class RAGService:
    def __init__(self):
        self._client = None
        self._collection = None

    def _get_collection(self):
        if self._collection is None:
            import chromadb
            self._client = chromadb.PersistentClient(path=CHROMADB_DIR)
            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    async def indexar_documento(self, arquivo_path: str, metadata: dict) -> str:
        """Index a .md file into ChromaDB. Returns the base doc_id."""
        from app.services.ollama_service import ollama_service

        path = Path(arquivo_path)
        if not path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {arquivo_path}")

        conteudo = path.read_text(encoding="utf-8")
        chunks = _chunk_text(conteudo)

        collection = self._get_collection()
        doc_id = arquivo_path.replace("/", "_").replace("\\", "_").replace(".", "_")

        # Remove previous version if exists
        try:
            existing = collection.get(where={"arquivo_path": arquivo_path})
            if existing["ids"]:
                collection.delete(ids=existing["ids"])
        except Exception:
            pass

        ids = []
        embeddings = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            embedding = await ollama_service.embed(chunk)
            if not embedding:
                continue
            chunk_id = f"{doc_id}_chunk{i}"
            ids.append(chunk_id)
            embeddings.append(embedding)
            documents.append(chunk)
            metadatas.append({**metadata, "arquivo_path": arquivo_path, "chunk_index": i})

        if ids:
            collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)

        return doc_id

    async def buscar_contexto(
        self, query: str, n_resultados: int = 3, filtros: dict = None,
        distancia_max: float = 0.45,
    ) -> list[str]:
        """Semantic search — returns only chunks below distancia_max (cosine distance).
        distancia_max=0.45 → cosine similarity ≥ 0.55 (relevante).
        Chunks acima do threshold são descartados para evitar alucinação de citação.
        """
        from app.services.ollama_service import ollama_service

        embedding = await ollama_service.embed(query)
        if not embedding:
            return []

        try:
            collection = self._get_collection()
            where = filtros if filtros else None
            results = collection.query(
                query_embeddings=[embedding],
                n_results=min(n_resultados, max(collection.count(), 1)),
                where=where,
                include=["documents", "metadatas", "distances"],
            )
            snippets = []
            docs      = results.get("documents", [[]])[0]
            metas     = results.get("metadatas",  [[]])[0]
            distances = results.get("distances",  [[]])[0]
            for doc, meta, dist in zip(docs, metas, distances):
                if dist > distancia_max:
                    continue  # descarta chunk irrelevante
                fonte = meta.get("titulo", meta.get("arquivo_path", "desconhecido"))
                trecho = doc[:600] + "..." if len(doc) > 600 else doc
                snippets.append(f"({fonte})\n{trecho}")
            return snippets
        except Exception:
            return []

    def remover_documento(self, arquivo_path: str):
        """Remove all chunks for a document from ChromaDB."""
        try:
            collection = self._get_collection()
            existing = collection.get(where={"arquivo_path": arquivo_path})
            if existing["ids"]:
                collection.delete(ids=existing["ids"])
        except Exception:
            pass

    def listar_fontes(self) -> list[dict]:
        """List all indexed sources with metadata (deduplicated by arquivo_path)."""
        try:
            collection = self._get_collection()
            results = collection.get(include=["metadatas"])
            seen = set()
            fontes = []
            for meta in results.get("metadatas", []):
                path = meta.get("arquivo_path", "")
                if path not in seen:
                    seen.add(path)
                    fontes.append(meta)
            return fontes
        except Exception:
            return []

    def total_chunks(self) -> int:
        try:
            return self._get_collection().count()
        except Exception:
            return 0


rag_service = RAGService()
