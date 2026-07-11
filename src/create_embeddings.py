import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------
# Project Paths
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

CHUNKS_PATH = (
    BASE_DIR
    / "src"
    / "ingestion"
    / "Chunking"
    / "Chunking_Output.json"
)

VECTORSTORE_DIR = BASE_DIR / "vectorstores"
VECTORSTORE_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------
# Load Chunk Data
# ---------------------------------------------------------

print("Loading chunk data...")

with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
    chunks = json.load(f)

print(f"Loaded {len(chunks)} chunks")

# ---------------------------------------------------------
# Prepare Text for Embedding
# ---------------------------------------------------------

texts = []

for chunk in chunks:

    text = f"""
Source File: {chunk.get("source_file", "")}

Chapter: {chunk.get("chapter", "")}

Heading: {chunk.get("heading", "")}

Subheading: {chunk.get("subheading", "")}

Content:
{chunk.get("content", "")}
"""

    texts.append(text.strip())

# ---------------------------------------------------------
# Load Embedding Model
# ---------------------------------------------------------

print("Loading embedding model...")

model = SentenceTransformer("all-MiniLM-L6-v2")

# ---------------------------------------------------------
# Generate Embeddings
# ---------------------------------------------------------

print("Generating embeddings...")

embeddings = model.encode(
    texts,
    show_progress_bar=True,
    convert_to_numpy=True
)

# ---------------------------------------------------------
# Save Embeddings
# ---------------------------------------------------------

embedding_path = VECTORSTORE_DIR / "embeddings.npy"

np.save(
    embedding_path,
    embeddings
)

print(f"Embeddings saved successfully!")

print(f"Location : {embedding_path}")
print(f"Shape    : {embeddings.shape}")