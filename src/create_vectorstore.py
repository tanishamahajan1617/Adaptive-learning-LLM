import json
import numpy as np
import faiss
from pathlib import Path

# Project Paths

BASE_DIR = Path(__file__).resolve().parent.parent

EMBEDDINGS_PATH = BASE_DIR / "vectorstores" / "embeddings.npy"

CHUNKS_PATH = (
    BASE_DIR
    / "src"
    / "ingestion"
    / "Chunking"
    / "Chunking_Output.json"
)

VECTORSTORE_DIR = BASE_DIR / "vectorstores"
VECTORSTORE_DIR.mkdir(exist_ok=True)

# Load Embedding

print("Loading embeddings...")

embeddings = np.load(EMBEDDINGS_PATH)

# Load Chunk Metadata

print("Loading chunk metadata...")

with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
    chunks = json.load(f)

print(f"Loaded {len(chunks)} metadata entries")

# Create FAISS Index

dimension = embeddings.shape[1]

print(f"Embedding dimension: {dimension}")

index = faiss.IndexFlatL2(dimension)

index.add(embeddings.astype(np.float32))

print(f"Added {index.ntotal} vectors to FAISS index")

# Save Index

index_path = VECTORSTORE_DIR / "faiss_index.bin"

faiss.write_index(index, str(index_path))

print(f"FAISS index saved successfully!")

print(f"Location : {index_path}")
