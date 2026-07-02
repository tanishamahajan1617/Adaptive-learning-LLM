import os
import json

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# -----------------------------------------
# Input / Output
# -----------------------------------------

INPUT_FILE = r"C:\Users\shibu\OneDrive\Documents\GitHub\Adaptive-learning-LLM\extracted_text\extracted_documents.json"

OUTPUT_FOLDER = r"C:\Users\shibu\OneDrive\Documents\GitHub\Adaptive-learning-LLM\extracted_data\chunked_data"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

OUTPUT_FILE = os.path.join(OUTPUT_FOLDER, "chunks.json")

# -----------------------------------------
# Load extracted documents
# -----------------------------------------

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    documents = json.load(f)

print(f"Loaded {len(documents)} pages")

# -----------------------------------------
# Chunking Configuration
# -----------------------------------------

text_splitter = RecursiveCharacterTextSplitter(

    chunk_size=1000,
    chunk_overlap=200,

    separators=[
        "\n\n",
        "\n",
        ". ",
        " ",
        ""
    ]
)

all_chunks = []

chunk_id = 1

# -----------------------------------------
# Chunk every document
# -----------------------------------------

for doc in documents:

    document = Document(
        page_content=doc["content"],
        metadata={
            "id": doc["id"],
            "source": doc["source"],
            "page": doc["page"],
            "chapter": doc["chapter"],
            "heading": doc["heading"]
        }
    )

    chunks = text_splitter.split_documents([document])

    for number, chunk in enumerate(chunks, start=1):

        all_chunks.append({

            "chunk_id": chunk_id,

            "document_id": chunk.metadata["id"],

            "chunk_number": number,

            "source": chunk.metadata["source"],

            "page": chunk.metadata["page"],

            "chapter": chunk.metadata["chapter"],

            "heading": chunk.metadata["heading"],

            "content": chunk.page_content

        })

        chunk_id += 1

# -----------------------------------------
# Save
# -----------------------------------------

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(all_chunks, f, indent=4, ensure_ascii=False)

print(f"\nChunking Completed")
print(f"Total Chunks : {len(all_chunks)}")
print(f"Saved : {OUTPUT_FILE}")