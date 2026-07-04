import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer


BASE_DIR = Path(__file__).resolve().parent.parent


CHUNKS_PATH = BASE_DIR / "extracted_data" / "chunked_data" / "chunks.json"


VECTORSTORE_DIR = BASE_DIR / "vectorstores"
VECTORSTORE_DIR.mkdir(exist_ok=True)

print("Loading chunks...")

with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
    chunks = json.load(f)


texts = [chunk["content"] for chunk in chunks]

print(f"Loaded {len(texts)} chunks")

print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

print("Generating embeddings...")
embeddings = model.encode(
    texts,
    show_progress_bar=True,
    convert_to_numpy=True
)

print("Saving embeddings...")
np.save(
    VECTORSTORE_DIR / "embeddings.npy",
    embeddings
)

print("Embeddings saved successfully!")
print("Embedding shape:", embeddings.shape)