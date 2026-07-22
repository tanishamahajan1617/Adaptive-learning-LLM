import json
import numpy as np
import faiss
from pathlib import Path

# Project Paths

BASE_DIR = Path(__file__).resolve().parent.parent

EMBEDDINGS_PATH = BASE_DIR / "vectorstores" / "embeddings.npy"

# CHUNKS_PATH = (
#     BASE_DIR
#     / "src"
#     / "ingestion"
#     / "Chunking"
#     / "Chunking_Output.json"
# )
METADATA_PATH = (
    BASE_DIR
    / "vectorstores"
    / "metadata.json"
)

VECTORSTORE_DIR = BASE_DIR / "vectorstores"
VECTORSTORE_DIR.mkdir(exist_ok=True)

# Load Embeddings

print("Loading embeddings...")

embeddings = np.load(EMBEDDINGS_PATH)

# Load Metadata

print("Loading metadata...")

with open(METADATA_PATH, "r", encoding="utf-8") as f:
    chunks = json.load(f)

print(f"Loaded metadata entries : {len(chunks)}")

# Validation

if len(embeddings) != len(chunks):
    raise ValueError(
        f"Mismatch detected!\n"
        f"Embeddings: {len(embeddings)}\n"
        f"Metadata: {len(chunks)}"
    )

# Create FAISS Index

dimension = embeddings.shape[1]

print(f"Embedding dimension: {dimension}")

# Embeddings are normalized, inner product is equivalent to cosine similarity

index = faiss.IndexFlatIP(dimension)

# Add embeddings to FAISS

index.add(embeddings.astype(np.float32))

print(f"Added {index.ntotal} vectors to FAISS index")

# Save Index

index_path = VECTORSTORE_DIR / "faiss_index.bin"

faiss.write_index(index, str(index_path))

# Output

print(f"FAISS vector store created successfully!")

print(f"Index Location : {index_path}")
print(f"Total vectors : {index.ntotal}")