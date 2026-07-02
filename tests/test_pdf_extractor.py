import unittest
import sys
import os

# Ensure the workspace root is in python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ingestion.pdf_extractor import clean_text

class TestPDFExtractor(unittest.TestCase):
    
    def test_unicode_normalization_and_ligatures(self):
        # Ligatures and smart quotes
        raw = "The ﬁrst step is to deﬁne a ﬂexible framework. “Smart quotes” and em—dash."
        expected = "The first step is to define a flexible framework. \"Smart quotes\" and em - dash."
        self.assertEqual(clean_text(raw), expected)
        
    def test_page_number_removal(self):
        # Page numbers on their own lines
        raw = "Paragraph one starts here.\n\n123\n\nParagraph two starts here.\n\nPage 4 of 20\n\nxiv\n\nParagraph three."
        expected = "Paragraph one starts here.\n\nParagraph two starts here.\n\nParagraph three."
        self.assertEqual(clean_text(raw), expected)
        
    def test_hyphenation_merge(self):
        # Hyphenated word split across lines
        raw = "This is a develop-\nment environment."
        expected = "This is a development environment."
        self.assertEqual(clean_text(raw), expected)
        
    def test_paragraph_reconstruction(self):
        # Line wraps should be joined with space, double newlines preserved
        raw = "This is the first line of the paragraph.\nThis is the second line of the paragraph.\n\nThis is a new paragraph."
        expected = "This is the first line of the paragraph. This is the second line of the paragraph.\n\nThis is a new paragraph."
        self.assertEqual(clean_text(raw), expected)
        
    def test_list_item_preservation(self):
        # Bullet points and ordered lists should be preserved as separate lines/paragraphs
        raw = "Here is a list:\n* Item one\n* Item two\n\nAnd some ordered list:\n1. First item\n2. Second item"
        expected = "Here is a list:\n\n* Item one\n\n* Item two\n\nAnd some ordered list:\n\n1. First item\n\n2. Second item"
        self.assertEqual(clean_text(raw), expected)
        
    def test_heading_preservation(self):
        # Short lines without sentence-ending punctuation should be treated as headings
        raw = "Chapter 1: Introduction\nThis is the introduction text which is quite long and explains everything.\nSection 1.1\nMore text follows here."
        expected = "Chapter 1: Introduction\n\nThis is the introduction text which is quite long and explains everything.\n\nSection 1.1\n\nMore text follows here."
        self.assertEqual(clean_text(raw), expected)

if __name__ == "__main__":
    unittest.main()
