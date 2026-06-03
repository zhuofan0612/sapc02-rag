import os, glob
import chromadb
import boto3
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer, CrossEncoder
from app.initial import client, MODEL, MAX_TOKENS

# --- Models (loaded once at startup) ---
_embed = SentenceTransformer("all-MiniLM-L6-v2")
_reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

# --- Single collection with source metadata ---
_chroma = chromadb.Client()
_collection = _chroma.get_or_create_collection("sapc02")

# --- In-memory session store: session_id -> message history ---
_sessions: dict[str, list] = {}


# --- Helpers ---

def chunk(text: str, size: int = 800, overlap: int = 100) -> list[str]:
    out, i = [], 0
    while i < len(text):
        out.append(text[i:i + size])
        i += size - overlap
    return out


def is_meaningful(text: str) -> bool:
    """Filter out chunks that are mostly whitespace or PDF formatting garbage."""
    stripped = text.strip()
    if len(stripped) < 100:
        return False
    alnum = sum(1 for c in stripped if c.isalnum() or c == ' ')
    return alnum / len(stripped) > 0.5


def read_file(path: str) -> str:
    if path.endswith(".pdf"):
        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    with open(path, "r", errors="ignore") as f:
        return f.read()


# --- S3 sync ---

def sync_from_s3(local_folder: str = "app/docs"):
    bucket = os.environ.get("DOCS_BUCKET", "")
    if not bucket:
        return  # local mode — skip
    s3 = boto3.client("s3")
    os.makedirs(local_folder, exist_ok=True)
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            local_path = os.path.join(local_folder, os.path.basename(key))
            s3.download_file(bucket, key, local_path)


# --- Ingest ---

def ingest(folder: str = "app/docs") -> int:
    sync_from_s3(folder)

    docs, ids, metadatas = [], [], []
    idx = 0

    for path in glob.glob(f"{folder}/*"):
        source = os.path.basename(path)
        text = read_file(path)
        for c in chunk(text):
            if not is_meaningful(c):
                continue
            docs.append(c)
            ids.append(f"d{idx}")
            metadatas.append({"source": source})
            idx += 1

    if docs:
        embeds = _embed.encode(docs).tolist()
        _collection.add(documents=docs, embeddings=embeds, ids=ids, metadatas=metadatas)

    return idx


# --- Retrieval with re-ranking ---

def _retrieve_context(question: str, k: int = 10) -> str:
    q_embed = _embed.encode([question]).tolist()

    hits = _collection.query(query_embeddings=q_embed, n_results=k)
    all_chunks = hits["documents"][0] if hits["documents"] else []

    # Re-rank with cross-encoder, keep top 4
    if all_chunks:
        scores = _reranker.predict([(question, c) for c in all_chunks])
        ranked = sorted(zip(scores, all_chunks), reverse=True)
        all_chunks = [c for _, c in ranked[:4]]

    return "\n\n".join(all_chunks)


def _get_history(session_id: str | None) -> list:
    if session_id and session_id in _sessions:
        return list(_sessions[session_id])
    return []


# --- Answer (blocking) ---

def answer(question: str, session_id: str | None = None) -> str:
    context = _retrieve_context(question)
    history = _get_history(session_id)
    history.append({"role": "user", "content": question})

    msg = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=(
            "Answer the AWS SAP-C02 question using ONLY the context below. "
            "If the context is insufficient, say so.\n\n"
            f"Context:\n{context}"
        ),
        messages=history,
    )
    response_text = msg.content[0].text

    if session_id:
        history.append({"role": "assistant", "content": response_text})
        _sessions[session_id] = history

    return response_text


# --- Answer (streaming) ---

def answer_stream(question: str, session_id: str | None = None):
    context = _retrieve_context(question)
    history = _get_history(session_id)
    history.append({"role": "user", "content": question})

    full_response = []
    with client.messages.stream(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=(
            "Answer the AWS SAP-C02 question using ONLY the context below. "
            "If the context is insufficient, say so.\n\n"
            f"Context:\n{context}"
        ),
        messages=history,
    ) as stream:
        for text in stream.text_stream:
            full_response.append(text)
            yield f"data: {text}\n\n"

    if session_id:
        history.append({"role": "assistant", "content": "".join(full_response)})
        _sessions[session_id] = history
