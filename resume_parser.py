import os
from pypdf import PdfReader
from docx import Document

def extract_resume_text(filepath: str) -> dict:
    """
    Extracts text from a resume file (.pdf or .docx).
    Returns a dict with success flag and extracted text.
    """
    if not os.path.exists(filepath):
        return {"success": False, "text": "", "error": "File not found."}

    ext = os.path.splitext(filepath)[1].lower()

    try:
        if ext == ".pdf":
            text = _extract_pdf(filepath)
        elif ext == ".docx":
            text = _extract_docx(filepath)
        else:
            return {"success": False, "text": "", "error": f"Unsupported file type: {ext}. Use PDF or DOCX."}

        if not text or len(text.strip()) < 20:
            return {"success": False, "text": "", "error": "File processed but little/no text found. It may be a scanned image PDF."}

        return {"success": True, "text": text.strip(), "error": None}

    except Exception as e:
        return {"success": False, "text": "", "error": f"Extraction failed: {str(e)}"}


def _extract_pdf(filepath: str) -> str:
    reader = PdfReader(filepath)
    pages_text = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages_text)


def _extract_docx(filepath: str) -> str:
    doc = Document(filepath)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


if __name__ == "__main__":
    test_path = "resumes/Vivek_Kumar_P_Accenture_Resume.pdf"
    if os.path.exists(test_path):
        result = extract_resume_text(test_path)
        print("Success:", result["success"])
        print("Error:", result["error"])
        print("\n--- Extracted Text (first 500 chars) ---\n")
        print(result["text"][:500])
    else:
        print(f"No test file found at {test_path}. Update the path in the script to test.")