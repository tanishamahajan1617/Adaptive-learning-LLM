import os
import re
import json
from langchain_community.document_loaders import PyPDFLoader

# Folder containing PDFs
PDF_FOLDER = r"C:\Users\shibu\OneDrive\Desktop\Books"

# Output JSON
OUTPUT_FILE = r"C:\Users\shibu\OneDrive\Documents\GitHub\Adaptive-learning-LLM\extracted_text\extracted_documents.json"

all_documents = []
document_id = 1


def clean_text(text):
    """Clean extracted text."""

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    text = text.strip()

    return text


def detect_chapter(text):
    """
    Detect chapter title.
    """

    lines = text.split("\n")

    for line in lines[:15]:

        line = line.strip()

        if re.match(r"(?i)^chapter\s+\d+", line):
            return line

        if re.match(r"^\d+\s+[A-Za-z]", line):
            return line

    return ""


def detect_heading(text):
    """
    Detect the first heading after chapter.
    """

    lines = text.split("\n")

    for line in lines:

        line = line.strip()

        if not line:
            continue

        # Ignore chapter lines
        if re.match(r"(?i)^chapter", line):
            continue

        # Ignore page numbers
        if re.match(r"^page\s+\d+", line, re.IGNORECASE):
            continue

        # Ignore very long lines
        if len(line) > 80:
            continue

        # Heading examples:
        # Arrays
        # Merge Sort
        # Linked List
        # Process Management
        if re.match(r"^[A-Z][A-Za-z0-9\s\-()]{2,60}$", line):
            return line

    return ""


# Read every PDF
for file in os.listdir(PDF_FOLDER):

    if not file.endswith(".pdf"):
        continue

    pdf_path = os.path.join(PDF_FOLDER, file)

    print(f"Reading: {file}")

    loader = PyPDFLoader(pdf_path)
    pages = loader.load()

    for page in pages:

        text = clean_text(page.page_content)

        if not text:
            continue

        chapter = detect_chapter(text)
        heading = detect_heading(text)

        all_documents.append({

            "id": document_id,

            "source": file,

            "page": page.metadata.get("page", 0) + 1,

            "chapter": chapter,

            "heading": heading,

            "content": text

        })

        document_id += 1


# Save JSON
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(all_documents, f, indent=4, ensure_ascii=False)

print("\nExtraction Completed Successfully!")
print(f"Total Pages : {len(all_documents)}")
print(f"Saved File  : {OUTPUT_FILE}")