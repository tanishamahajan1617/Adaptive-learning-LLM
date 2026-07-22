import json
import faiss
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

# ----------------------------
# Project Paths
# ----------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

INDEX_PATH = BASE_DIR / "vectorstores" / "faiss_index.bin"

CHUNKS_PATH = (
    BASE_DIR
    / "src"
    / "ingestion"
    / "Chunking"
    / "Chunking_Output.json"
)

# ----------------------------
# Load Embedding Model
# ----------------------------

print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

# ----------------------------
# Load FAISS Index
# ----------------------------

print("Loading FAISS index...")
index = faiss.read_index(str(INDEX_PATH))

# ----------------------------
# Load Chunk Metadata
# ----------------------------

print("Loading chunk metadata...")

with open(CHUNKS_PATH, "r", encoding="utf-8") as file:
    chunks = json.load(file)

print(f"Loaded {len(chunks)} chunks.")

# ----------------------------
# Retrieval Function
# ----------------------------

def retrieve(query, top_k=10):
    """
    Retrieve the most relevant chunks for a user query.
    """

    # Convert query into embedding
    query_embedding = model.encode(
    [query],
    convert_to_numpy=True
).astype(np.float32)

    # Search in FAISS
    distances, indices = index.search(query_embedding, top_k)

    # Collect retrieved chunks
    retrieved_chunks = []

    for idx, distance in zip(indices[0], distances[0]):
        if idx < len(chunks):
            chunk = chunks[idx].copy()
            chunk["distance"] = float(distance)
            retrieved_chunks.append(chunk)

    return retrieved_chunks


# ----------------------------
# Testing
# ----------------------------

if __name__ == "__main__":

    print("\n" + "=" * 90)
    print("               ADAPTIVE LEARNING LLM - RETRIEVAL MODULE")
    print("=" * 90)

    question = input("\nEnter your question: ")

    results = retrieve(question)

    print("\n" + "=" * 90)
    print(f"Top {len(results)} Relevant Chunks Retrieved Successfully")
    print("=" * 90)

    for i, chunk in enumerate(results, start=1):

        print(f"\nResult #{i}")
        print("-" * 90)

        print(f"FAISS Distance (Lower is Better): {chunk['distance']:.4f}")
        print(f"Source File : {chunk.get('source_file')}")
        print(f"Chapter     : {chunk.get('chapter')}")
        print(f"Heading     : {chunk.get('heading')}")
        print(f"Subheading  : {chunk.get('subheading')}")

        content = chunk.get("content", "").replace("\n", " ")

        preview = content[:250]

        if len(content) > 250:
            preview += "..."

        print("\nPreview")
        print("-" * 90)
        print(preview)

        while True:

            choice = input("\nView complete chunk? (Y/N): ").strip().lower()

            if choice == "y":

                print("\nComplete Chunk")
                print("-" * 90)
                print(content)
                break

            elif choice == "n":
                break

            else:
                print("Please enter Y or N.")

        print("\n" + "=" * 90)

    print("\nRetrieval completed successfully.")