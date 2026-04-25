import os
import json
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.ingestion.pdf_extractor import extract_text, clean_text

CHUNK_SIZE    = 200
CHUNK_OVERLAP = 50
BASE_DIR      = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# ─────────────────────────────
# 👇 ADD BOOK
# ─────────────────────────────
BOOKS = [
    {
        "pdf_path"    : os.path.join(BASE_DIR, "data", "raw", "dsa", "clrs_sample.pdf"),
        "output_path" : os.path.join(BASE_DIR, "data", "processed", "dsa_clrs_chunks.json"),
        "source"      : "CLRS",
        "subject"     : "DSA"
    },
    {
        "pdf_path"    : os.path.join(BASE_DIR, "data", "raw", "dsa", "karumanchi_sample.pdf"),
        "output_path" : os.path.join(BASE_DIR, "data", "processed", "dsa_karumanchi_chunks.json"),
        "source"      : "Karumanchi",
        "subject"     : "DSA"
    },
    {
        "pdf_path"    : os.path.join(BASE_DIR, "data", "raw", "os", "silberschatz_sample.pdf"),
        "output_path" : os.path.join(BASE_DIR, "data", "processed", "os_silberschatz_chunks.json"),
        "source"      : "Silberschatz",
        "subject"     : "OS"
    },
]


# ─────────────────────────────
# CHUNK
# ─────────────────────────────
def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    words  = text.split()
    chunks = []
    i      = 0

    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap

    return chunks


# ─────────────────────────────
# SAVE
# ─────────────────────────────
def save_chunks(chunks, output_path, source, subject):
    if os.path.exists(output_path):
        os.remove(output_path)
        print(f"  🗑️  Purani file delete ki")

    data = []
    for idx, chunk in enumerate(chunks):
        data.append({
            "chunk_index" : idx,
            "text"        : chunk,
            "source"      : source,
            "subject"     : subject
        })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"  💾 Saved: {output_path}")
    return data


# ─────────────────────────────
# PROCESS ONE BOOK
# ─────────────────────────────
def process_book(book):
    pdf_path    = book["pdf_path"]
    output_path = book["output_path"]
    source      = book["source"]
    subject     = book["subject"]

    # PDF exist karta hai?
    if not os.path.exists(pdf_path):
        print(f"  ⚠️  PDF nahi mila — skip: {pdf_path}")
        return

    print(f"\n{'='*50}")
    print(f"📚 Processing: {source} ({subject})")
    print(f"{'='*50}")

    # Extract
    print("📥 Extracting text...")
    text = extract_text(pdf_path)
    print(f"  ✅ {len(text):,} characters")

    # Clean
    print("🧹 Cleaning text...")
    text = clean_text(text)
    print(f"  ✅ {len(text):,} characters")

    # Chunk
    print("✂️  Chunking...")
    chunks = chunk_text(text)
    print(f"  ✅ {len(chunks)} chunks")

    # Save
    print("💾 Saving JSON...")
    data = save_chunks(chunks, output_path, source, subject)

    print(f"  ✅ Done — {len(data)} chunks saved")


# ─────────────────────────────
# MAIN
# ─────────────────────────────
if __name__ == "__main__":
    print("\n🚀 Multi-Book Ingestion Pipeline Start\n")

    for book in BOOKS:
        process_book(book)

    print(f"\n{'='*50}")
    print("✅ All Books Processed!")
    print(f"{'='*50}\n")