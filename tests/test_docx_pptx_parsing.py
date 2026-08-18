import os
import tempfile
import pytest
import docx
from pptx import Presentation
from backend.services.document_service import extract_text_from_file

def test_extract_docx_success():
    # Create temporary docx file
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "test.docx")
        
        # Build docx document
        doc = docx.Document()
        doc.add_paragraph("This is paragraph 1 of the test docx.")
        doc.add_paragraph("And this is paragraph 2.")
        
        table = doc.add_table(rows=2, cols=2)
        table.cell(0, 0).text = "Header A"
        table.cell(0, 1).text = "Header B"
        table.cell(1, 0).text = "Data A"
        table.cell(1, 1).text = "Data B"
        
        doc.save(file_path)
        
        # Extract and verify
        text = extract_text_from_file(file_path, ".docx")
        assert "This is paragraph 1 of the test docx." in text
        assert "And this is paragraph 2." in text
        assert "Header A | Header B" in text
        assert "Data A | Data B" in text

def test_extract_pptx_success():
    # Create temporary pptx file
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "test.pptx")
        
        # Build pptx presentation
        prs = Presentation()
        # Add slide with blank layout
        blank_slide_layout = prs.slide_layouts[6]
        slide1 = prs.slides.add_slide(blank_slide_layout)
        
        # Add a text shape
        tx_box = slide1.shapes.add_textbox(0, 0, 100, 100)
        tf = tx_box.text_frame
        tf.text = "Hello Slide 1 Shape Text"
        
        # Add speaker notes
        notes_slide = slide1.notes_slide
        text_frame = notes_slide.notes_text_frame
        text_frame.text = "Speaker note content here."
        
        # Add slide 2
        slide2 = prs.slides.add_slide(blank_slide_layout)
        tx_box2 = slide2.shapes.add_textbox(0, 0, 100, 100)
        tf2 = tx_box2.text_frame
        tf2.text = "Hello Slide 2 Shape Text"
        
        prs.save(file_path)
        
        # Extract and verify
        text = extract_text_from_file(file_path, ".pptx")
        assert "--- Slide 1 ---" in text
        assert "Hello Slide 1 Shape Text" in text
        assert "[Speaker Notes: Speaker note content here.]" in text
        assert "--- Slide 2 ---" in text
        assert "Hello Slide 2 Shape Text" in text

def test_unsupported_file_extension():
    with pytest.raises(ValueError) as excinfo:
        extract_text_from_file("dummy_path.xyz", ".xyz")
    assert "Unsupported file extension" in str(excinfo.value)
