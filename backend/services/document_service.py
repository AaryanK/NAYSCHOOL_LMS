import re
from pypdf import PdfReader
from sqlalchemy.orm import Session
from backend.models import CourseFile, DocumentChunk

def extract_text_from_file(file_path: str, file_type: str) -> str:
    """
    Extracts text from a given file path based on its extension.
    Supports txt, md, pdf, docx, pptx, and image formats via OCRService.
    Raises ValueError for unsupported types, and RuntimeError on extraction failures.
    """
    ext = file_type.lower().strip()
    if ext in [".txt", ".md"]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            except Exception as e:
                raise RuntimeError(f"Failed to read text file: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Failed to read text file: {str(e)}")

    elif ext == ".pdf":
        try:
            reader = PdfReader(file_path)
            pages_text = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    pages_text.append(text)
            return "\n".join(pages_text)
        except Exception as e:
            raise RuntimeError(f"PDF extraction failed: {str(e)}")

    elif ext == ".docx":
        try:
            import docx
            doc = docx.Document(file_path)
            paragraphs_text = [p.text for p in doc.paragraphs]
            
            # Extract table text
            tables_text = []
            for table in doc.tables:
                for row in table.rows:
                    row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_text:
                        tables_text.append(" | ".join(row_text))
            
            full_text = "\n".join(p for p in (paragraphs_text + tables_text) if p.strip())
            return full_text
        except Exception as e:
            raise RuntimeError(f"DOCX extraction failed: {str(e)}")

    elif ext == ".pptx":
        try:
            from pptx import Presentation
            prs = Presentation(file_path)
            slides_text = []
            for i, slide in enumerate(prs.slides):
                slide_content = []
                # Extract text from shapes
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        slide_content.append(shape.text.strip())
                
                # Extract speaker notes if present
                try:
                    if slide.notes_slide and slide.notes_slide.notes_text_frame:
                        notes = slide.notes_slide.notes_text_frame.text.strip()
                        if notes:
                            slide_content.append(f"[Speaker Notes: {notes}]")
                except Exception:
                    pass
                
                slides_text.append(f"--- Slide {i+1} ---\n" + "\n".join(slide_content))
            return "\n\n".join(slides_text)
        except Exception as e:
            raise RuntimeError(f"PPTX extraction failed: {str(e)}")

    elif ext in [".png", ".jpg", ".jpeg"]:
        from backend.services.ocr_service import OCRService
        return OCRService.extract_text_from_image(file_path)

    else:
        raise ValueError(f"Unsupported file extension: {ext}")

def chunk_text(text: str, max_chars: int = 1000, overlap: int = 150) -> list[str]:
    """
    Splits text into chunks of roughly max_chars with overlap characters.
    Cleans up whitespace and avoids creating empty chunks.
    """
    # Clean up whitespace
    cleaned_text = re.sub(r'\s+', ' ', text).strip()
    if not cleaned_text:
        return []

    chunks = []
    start = 0
    text_len = len(cleaned_text)

    while start < text_len:
        end = start + max_chars
        
        # If not at the end of the text, try to find a clean sentence/space boundary
        if end < text_len:
            split_idx = -1
            # Look back up to 120 chars for period/space boundary, but never past the start boundary
            max_offset = end - start - 1
            search_limit = min(120, max_offset)
            if search_limit > 0:
                for offset in range(search_limit):
                    char = cleaned_text[end - offset]
                    if char in ['.', '!', '?']:
                        split_idx = end - offset + 1
                        break
                    elif char == ' ' and split_idx == -1:
                        split_idx = end - offset

            if split_idx != -1:
                end = split_idx

        chunk = cleaned_text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Slide window back by overlap
        next_start = end - overlap
        if next_start >= end or next_start <= start:
            # Fallback to prevent infinite loops
            start = end
        else:
            start = next_start

        # Stop if remaining text is trivial
        if text_len - start < 50:
            break

    # TODO: Implement a production-grade recursive token-based or sentence splitter.
    return chunks

def create_chunks_for_course_file(db: Session, course_file: CourseFile, text: str) -> int:
    """
    Chunks extracted text and saves it as DocumentChunk entities.
    Deletes any existing chunks for this file if reprocessing.
    """
    # Delete old chunks if any
    db.query(DocumentChunk).filter(DocumentChunk.course_file_id == course_file.id).delete()
    db.commit()

    if not text.strip():
        return 0

    chunks = chunk_text(text)
    
    # Bulk insert
    db_chunks = []
    for i, content in enumerate(chunks):
        db_chunk = DocumentChunk(
            course_file_id=course_file.id,
            course_id=course_file.course_id,
            chunk_index=i,
            content=content
        )
        db_chunks.append(db_chunk)

    if db_chunks:
        db.add_all(db_chunks)
        db.commit()

    return len(chunks)
