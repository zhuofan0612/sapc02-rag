import os, glob
import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from anthropic import Anthropic

load_dotenv()

# Local embedding model (no API cost). First load downloads weights.
_embed = SentenceTransformer("all-MiniLM-L6-v2")
_client = chromadb.Client()
_collection = _client.get_or_create_collection("sapc02")
_anthropic = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

def chunk(text, size=800, overlap=100):
    out, i = [], 0
    while i < len(text):
        out.append(text[i:i+size])
        i += size - overlap
    return out

def ingest(folder="app/docs"):
    docs, ids, idx = [], [], 0
    for path in glob.glob(f"{folder}/*"):
        with open(path, "r", errors="ignore") as f:
            for c in chunk(f.read()):
                docs.append(c); ids.append(f"d{idx}"); idx += 1
    if docs:
        embeds = _embed.encode(docs).tolist()
        _collection.add(documents=docs, embeddings=embeds, ids=ids)
    return idx

def answer(question, k=4):
    q_embed = _embed.encode([question]).tolist()
    hits = _collection.query(query_embeddings=q_embed, n_results=k)
    context = "\n\n".join(hits["documents"][0]) if hits["documents"] else ""
    prompt = (
        "Answer the AWS SAP-C02 question using ONLY the context below. "
        "If the context is insufficient, say so.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}"
    )
    msg = _anthropic.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text
