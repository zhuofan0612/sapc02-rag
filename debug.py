from app.initial import client, MODEL, MAX_TOKENS
from app.rag import _embed, _reranker, _collections, TOPICS, classify_topic, ingest, _retrieve_context

# Step 1: ingest docs
print("=== Ingesting docs ===")
total = ingest()
print(f"Total chunks ingested: {total}")

# Step 2: check how many chunks per collection
print("\n=== Chunks per collection ===")
for topic in TOPICS:
    count = _collections[topic].count()
    print(f"  {topic}: {count} chunks")

# Step 3: classify the question
question = "what is SCP?"
topic = classify_topic(question)
print(f"\n=== Question classified as: {topic} ===")

# Step 4: retrieve context
context = _retrieve_context(question)
print(f"\n=== Retrieved context ===")
print(context[:1000] if context else "EMPTY — nothing retrieved")
