import json
import argparse
from pathlib import Path
import pymupdf4llm

def extract_markdown_from_pdf(pdf_path: str) -> str:
    """
    Converts a PDF to Markdown using pymupdf4llm.
    """
    print(f"Processing '{pdf_path}' with PyMuPDF4LLM...")
    md_text = pymupdf4llm.to_markdown(pdf_path)
    print("Conversion complete.")
    return md_text

import re

def parse_markdown_to_json(markdown_text: str) -> list:
    """
    Parses Markdown text and segments it into a JSON-friendly list of dictionaries
    based on headings. Uses regex and heuristics to accurately detect chapters.
    """
    lines = markdown_text.split('\n')
    chunks = []
    
    current_chapter = ""
    current_heading = ""
    current_subheading = ""
    current_content = []
    
    chunk_id = 1
    
    def save_chunk():
        nonlocal chunk_id, current_content
        content_str = '\n'.join(current_content).strip()
        # Skip the entire chunk if heading is empty
        if content_str and current_heading:
            chunk = {
                "chunk_id": chunk_id,
                "chapter": current_chapter,
                "heading": current_heading,
            }
            if current_subheading:
                chunk["subheading"] = current_subheading
            chunk["content"] = content_str
            chunks.append(chunk)
            chunk_id += 1
        current_content = []

    for line in lines:
        stripped_line = line.strip()
        
        match = re.match(r'^(#{1,6})\s+(.*)$', stripped_line)
        if match:
            save_chunk()
            level = len(match.group(1))
            raw_text = match.group(2).strip()
            
            # Remove markdown bold/italic asterisks and strikethroughs
            clean_text = raw_text.strip('*_ ~')
            # Remove HTML tags from headings if they leaked in
            clean_text = re.sub(r'<[^>]+>', '', clean_text).strip()
            lower_text = clean_text.lower()
            
            # Filter out known OCR garbage / page watermarks
            garbage_list = ["ce org", "eerg ors", "chapter objectives"]
            if lower_text in garbage_list:
                continue

            # 1. Keyword heuristics — "Chapter N" / "Part N" only (requires a number after keyword)
            #    This prevents sidebars like "CHAPTER OBJECTIVES" from being treated as chapters.
            if re.match(r'^(chapter|part)\s+(\d+|[ivxlcdmIVXLCDM]+)\b', lower_text):
                current_chapter = clean_text
                current_heading = ""
                current_subheading = ""
            # 2. Numbering heuristics (e.g., 1.1.1)
            elif re.match(r'^(\d+)\.\d+\.\d+', clean_text):
                top_num = re.match(r'^(\d+)', clean_text).group(1)
                # Infer chapter from top-level number if not set or chapter number changes
                if not current_chapter or not re.search(r'\b' + top_num + r'\b', current_chapter):
                    current_chapter = f"Chapter {top_num}"
                current_subheading = clean_text
            # 3. Numbering heuristics (e.g., 1.1)
            elif re.match(r'^(\d+)\.\d+', clean_text):
                top_num = re.match(r'^(\d+)', clean_text).group(1)
                # Infer chapter from top-level number if not set or chapter number changes
                if not current_chapter or not re.search(r'\b' + top_num + r'\b', current_chapter):
                    current_chapter = f"Chapter {top_num}"
                    current_heading = ""
                # If we already have a text heading like "Introduction", make this a subheading
                if current_heading and not re.match(r'^\d+\.\d+', current_heading):
                    current_subheading = clean_text
                else:
                    current_heading = clean_text
                    current_subheading = ""
            # 4. Fallback to Markdown Heading Levels
            else:
                if level <= 2:
                    if not current_chapter:
                        current_chapter = clean_text
                    else:
                        current_heading = clean_text
                        current_subheading = ""
                elif level <= 4:
                    if not current_heading:
                        current_heading = clean_text
                        current_subheading = ""
                    else:
                        # Only overwrite heading if the current one is also text (not numbered)
                        if not re.match(r'^\d+\.\d+', current_heading):
                            current_heading = clean_text
                            current_subheading = ""
                        else:
                            current_subheading = clean_text
                else:
                    current_subheading = clean_text
        else:
            if stripped_line:
                current_content.append(line)

    # Save the last chunk
    save_chunk()
    
    return chunks

def process_single_pdf(pdf_path: Path, output_path: Path):
    """Processes a single PDF and saves its chunks to a JSON file."""
    try:
        md_text = extract_markdown_from_pdf(str(pdf_path))
        structured_data = parse_markdown_to_json(md_text)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(structured_data, f, indent=4, ensure_ascii=False)
        print(f"  -> Saved {len(structured_data)} chunks to '{output_path.name}'")
        return structured_data
    except Exception as e:
        print(f"  -> ERROR processing '{pdf_path.name}': {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Extract structure and chunks from PDF file(s).")
    parser.add_argument("pdf_path", type=str, nargs='?', default=r"C:\Users\shibu\OneDrive\Desktop\Books",
                        help="Path to a PDF file OR a folder containing PDF files.")
    parser.add_argument("--output", type=str, default="output.json",
                        help="Path for the combined output JSON file (used when processing a folder).")
    parser.add_argument("--output-dir", type=str, default=".",
                        help="Directory to save per-PDF JSON files (default: current directory).")

    args = parser.parse_args()

    input_path = Path(args.pdf_path)
    if not input_path.exists():
        print(f"Error: Path '{input_path}' does not exist.")
        return

    # ── Folder mode: process all PDFs inside ──────────────────────────────────
    if input_path.is_dir():
        pdf_files = sorted(input_path.glob("*.pdf"))
        if not pdf_files:
            print(f"No PDF files found in '{input_path}'.")
            return

        print(f"Found {len(pdf_files)} PDF(s) in '{input_path}':\n")

        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        all_chunks = []
        global_chunk_id = 1
        for i, pdf_file in enumerate(pdf_files, start=1):
            print(f"[{i}/{len(pdf_files)}] Processing: {pdf_file.name}")
            per_file_output = output_dir / (pdf_file.stem + ".json")
            chunks = process_single_pdf(pdf_file, per_file_output)
            for chunk in chunks:
                chunk["source_file"] = pdf_file.name
                chunk["chunk_id"] = global_chunk_id
                global_chunk_id += 1
            all_chunks.extend(chunks)

        # Save combined JSON
        combined_output = Path(args.output)
        with open(combined_output, 'w', encoding='utf-8') as f:
            json.dump(all_chunks, f, indent=4, ensure_ascii=False)

        print(f"\nDone! Processed {len(pdf_files)} PDF(s) -> {len(all_chunks)} total chunks.")
        print(f"  Combined output : '{combined_output}'")
        print(f"  Per-file JSONs  : '{output_dir}\\*.json'")

    # ── Single file mode ───────────────────────────────────────────────────────
    else:
        print(f"Processing single file: {input_path.name}")
        output_path = Path(args.output)
        chunks = process_single_pdf(input_path, output_path)
        print(f"\nDone! Saved {len(chunks)} chunks to '{output_path}'")

if __name__ == "__main__":
    main()
