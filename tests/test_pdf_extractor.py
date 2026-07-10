import unittest
import sys
import os

# Ensure the workspace root is in python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ingestion.pdf_extractor import clean_text, extract_and_remove_headers, normalize_spaced_text

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

    def test_extract_and_remove_headers(self):
        # DSA 1
        raw1 = "CHAPTER 1. INTRODUCTION 2\nThis is the first sentence."
        clean, chap, title, sub = extract_and_remove_headers(raw1, 2)
        self.assertEqual(clean.strip(), "This is the first sentence.")
        self.assertEqual(chap, "Chapter 1")
        self.assertEqual(title, "INTRODUCTION")
        self.assertEqual(sub, "")

        # DSA 2 Even
        raw2 = "2 ■ Chapter 1 Object-Oriented Programming Using C++\nSome body text."
        clean, chap, title, sub = extract_and_remove_headers(raw2, 2)
        self.assertEqual(clean.strip(), "Some body text.")
        self.assertEqual(chap, "Chapter 1")
        self.assertEqual(title, "Object-Oriented Programming Using C++")
        self.assertEqual(sub, "")

        # DSA 2 Odd
        raw3 = "Section 1.2 Encapsulation ■ 3\nMore body text."
        clean, chap, title, sub = extract_and_remove_headers(raw3, 3)
        self.assertEqual(clean.strip(), "More body text.")
        self.assertEqual(chap, "")
        self.assertEqual(title, "")
        self.assertEqual(sub, "1.2 Encapsulation")

        # Standalone chapter start page
        raw4 = "Chapter 2\nLinked Lists\nLinked lists are data structures."
        clean, chap, title, sub = extract_and_remove_headers(raw4, 9)
        self.assertEqual(clean.strip(), "Linked lists are data structures.")
        self.assertEqual(chap, "Chapter 2")
        self.assertEqual(title, "Linked Lists")
        self.assertEqual(sub, "")

        # Spaced DSA 2 Even
        raw_spaced = "2 ■ C h a p t e r 1 O b j e c t - O r i e n t e d P r o g r a m m i n g U s i n g C + +\nSome body text."
        clean, chap, title, sub = extract_and_remove_headers(raw_spaced, 2)
        self.assertEqual(clean.strip(), "Some body text.")
        self.assertEqual(chap, "Chapter 1")
        self.assertEqual(title, "Object-Oriented Programming Using C++")
        self.assertEqual(sub, "")

    def test_normalize_spaced_text(self):
        spaced = "C h a p t e r 1 O b j e c t - O r i e n t e d"
        expected = "Chapter 1 Object-Oriented"
        self.assertEqual(normalize_spaced_text(spaced), expected)

if __name__ == "__main__":
    unittest.main()
