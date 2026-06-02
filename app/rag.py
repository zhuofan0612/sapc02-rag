import os, glob
import chromadb
import boto3
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer, CrossEncoder
from app.initial import client, MODEL, MAX_TOKENS

# --- Models (loaded once at startup) ---
_embed = SentenceTransformer("all-MiniLM-L6-v2")
_reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

# --- Multi-collection ChromaDB ---
_chroma = chromadb.Client()
TOPICS = ["networking", "storage", "compute", "databases", "security", "migration", "general"]
_collections = {t: _chroma.get_or_create_collection(f"sapc02_{t}") for t in TOPICS}

TOPIC_KEYWORDS = {
    "networking": ["vpc", "subnet", "route53", "cloudfront", "direct connect", "transit gateway",
                   "nat", "igw", "alb", "nlb", "security group", "peering", "global accelerator"],
    "storage":    ["s3", "ebs", "efs", "fsx", "glacier", "storage gateway", "snowball", "datasync"],
    "compute":    ["ec2", "lambda", "ecs", "fargate", "auto scaling", "elastic beanstalk", "batch"],
    "databases":  ["rds", "dynamodb", "aurora", "elasticache", "redshift", "neptune", "dax"],
    "security":   ["iam", "kms", "secrets manager", "guardduty", "waf", "shield", "macie",
                   "inspector", "scp", "organization"],
    "migration":  ["dms", "datasync", "snowball", "migration hub", "server migration", "sct"],
}

# --- In-memory session store: session_id -> message history ---
_sessions: dict[str, list] = {}


# --- Helpers ---

def classify_topic(text: str) -> str:
    text_lower = text.lower()
    scores = {
        topic: sum(1 for kw in keywords if kw in text_lower)
        for topic, keywords in TOPIC_KEYWORDS.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"


def chunk(text: str, size: int = 800, overlap: int = 100) -> list[str]:
    out, i = [], 0
    while i < len(text):
        out.append(text[i:i + size])
        i += size - overlap
    return out


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

    docs_by_topic: dict[str, list[tuple[str, str]]] = {t: [] for t in TOPICS}
    idx = 0

    for path in glob.glob(f"{folder}/*"):
        text = read_file(path)
        for c in chunk(text):
            topic = classify_topic(c)
            docs_by_topic[topic].append((c, f"d{idx}"))
            idx += 1

    for topic, pairs in docs_by_topic.items():
        if not pairs:
            continue
        texts, ids = zip(*pairs)
        embeds = _embed.encode(list(texts)).tolist()
        _collections[topic].add(documents=list(texts), embeddings=embeds, ids=list(ids))

    return idx


# --- Retrieval with re-ranking ---

def _retrieve_context(question: str, k: int = 6) -> str:
    topic = classify_topic(question)
    q_embed = _embed.encode([question]).tolist()

    # Search topic collection + general as fallback
    cols = [_collections[topic]]
    if topic != "general":
        cols.append(_collections["general"])

    all_chunks = []
    for col in cols:
        hits = col.query(query_embeddings=q_embed, n_results=k)
        if hits["documents"]:
            all_chunks.extend(hits["documents"][0])

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

def answer(question: str, session_id: str | None = None, k: int = 6) -> str:
    context = _retrieve_context(question, k)
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

def answer_stream(question: str, session_id: str | None = None, k: int = 6):
    context = _retrieve_context(question, k)
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
