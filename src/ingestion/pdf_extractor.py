import pdfplumber
import re
import os

def extract_text(pdf_path):
    """PDF se raw text extract karo"""
    
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF nahi mila: {pdf_path}")
    
    text = ""
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"  📖 Total pages: {len(pdf.pages)}")
        
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    
    return text


def clean_text(text):
    """Extracted text ko clean karo"""
    
    # Hyphenated line breaks fix karo
    text = re.sub(r"-\n(\w)", r"\1", text)
    
    # Page numbers remove karo
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)
    
    # Multiple newlines fix karo
    text = re.sub(r"\n+", " ", text)
    
    # Multiple spaces fix karo
    text = re.sub(r"\s+", " ", text)
    
    return text.strip()