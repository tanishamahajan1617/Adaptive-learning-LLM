import pdfplumber
import json
import os

from src.config import CHUNK_SIZE


# ✅ STEP 1: Extract text from PDF
def extract_text(pdf_path):
    text = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

    return text

# ✅ STEP 2: Clean text (IMPORTANT)
def clean_text(text):
    text = text.replace("\n", " ")
    text = text.replace("  ", " ")
    text = text.strip()
    return text


# ✅ STEP 3: Chunk text
def chunk_text(text, chunk_size=CHUNK_SIZE):
    words = text.split()
    chunks = []

    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)

    return chunks


# ✅ STEP 4: Save chunks as JSON
def save_chunks(chunks, output_path, source, subject):
    data = []

    for chunk in chunks:
        data.append({
            "text": chunk,
            "source": source,
            "subject": subject
        })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ✅ MAIN PIPELINE
if __name__ == "__main__":
    pdf_path = r"C:\Projects\Capstone_LLM\Adaptive-learning-LLM\data\raw\dsa\Cormen Introduction to Algorithms-26-63.pdf"

    source = "CLRS"
    subject = "DSA"

    print("📥 Extracting text...")
    text = extract_text(pdf_path)

    print("🧹 Cleaning text...")
    text = clean_text(text)

    print("✂️ Chunking text...")
    chunks = chunk_text(text)

    print(f"📦 Total chunks created: {len(chunks)}")

    output_path = r"C:\Projects\Capstone_LLM\Adaptive-learning-LLM\data\processed\dsa_clrs_chunks.json"

    print("💾 Saving JSON...")
    save_chunks(chunks, output_path, source, subject)

    print("✅ Ingestion Complete!")