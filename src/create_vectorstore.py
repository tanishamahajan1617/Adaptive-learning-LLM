import json
import numpy as np
import faiss
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

EMBEDDINGS_PATH = BASE_DIR / "vectorstores" / "embeddings.npy"
CHUNKS_PATH = BASE_DIR / "extracted_data" / "chunked_data" / "chunks.json"

VECTORSTORE_DIR = BASE_DIR / "vectorstores"
VECTORSTORE_DIR.mkdir(exist_ok=True)

print("Loading embeddings...")
embeddings = np.load(EMBEDDINGS_PATH)

print("Loading metadata...")
with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
    chunks = json.load(f)

dimension = embeddings.shape[1]

print(f"Embedding dimension: {dimension}")


index = faiss.IndexFlatL2(dimension)


index.add(embeddings.astype("float32"))

print(f"Added {index.ntotal} vectors to FAISS index")


faiss.write_index(
    index,
    str(VECTORSTORE_DIR / "faiss_index.bin")
)

print("FAISS index saved successfully!")