import os
import chromadb
from sentence_transformers import SentenceTransformer

import db
from resume_parser import extract_resume_text

# --- Config ---
DB_DIR = "chroma_db"
COLLECTION_NAME = "job_hunt_memory"
RESUMES_DIR = "resumes"

# --- Shared resources (reused across create/update/delete) ---
_model = None
_collection = None

def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def _get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=DB_DIR)
        _collection = client.get_or_create_collection(name=COLLECTION_NAME)
    return _collection

def _vector_id(app_id):
    return f"app_{app_id}"

def _build_embedding_text(company, role, jd_text, resume_text, notes):
    return f"""Company: {company}
Role: {role}

Job Description:
{jd_text}

Resume Submitted:
{resume_text}

Notes:
{notes}"""

def _upsert_vector(app_id, company, role, jd_text, resume_text, notes, status, job_link):
    model = _get_model()
    collection = _get_collection()

    text = _build_embedding_text(company, role, jd_text, resume_text, notes)
    embedding = model.encode([text]).tolist()

    collection.upsert(
        ids=[_vector_id(app_id)],
        embeddings=embedding,
        documents=[text],
        metadatas=[{
            "app_id": app_id,
            "company": company or "",
            "role": role or "",
            "status": status or "",
            "job_link": job_link or ""
        }]
    )

def _delete_vector(app_id):
    collection = _get_collection()
    try:
        collection.delete(ids=[_vector_id(app_id)])
    except Exception:
        pass  # vector may not exist yet, safe to ignore


# ---------------- CREATE ----------------
def create_application_record(company, role, job_link, jd_text, resume_file_bytes, resume_original_filename, notes=""):
    """
    resume_file_bytes: raw bytes of the uploaded resume file (from Streamlit's UploadedFile.getbuffer())
    resume_original_filename: original filename, used to preserve the extension
    """
    # 1. Insert SQLite row first (without resume_filename) to get app_id
    app_id = db.add_application(
        company=company, role=role, job_link=job_link, jd_text=jd_text,
        resume_filename="", resume_text="", notes=notes
    )

    # 2. Save resume file to disk using app_id in the filename (avoids collisions)
    os.makedirs(RESUMES_DIR, exist_ok=True)
    ext = os.path.splitext(resume_original_filename)[1].lower()
    resume_filename = f"app_{app_id}{ext}"
    resume_path = os.path.join(RESUMES_DIR, resume_filename)

    with open(resume_path, "wb") as f:
        f.write(resume_file_bytes)

    # 3. Extract resume text
    result = extract_resume_text(resume_path)
    resume_text = result["text"] if result["success"] else ""

    # 4. Update SQLite row with resume info
    db.update_application(app_id, resume_filename=resume_filename, resume_text=resume_text)

    # 5. Embed combined text into ChromaDB
    _upsert_vector(app_id, company, role, jd_text, resume_text, notes, status="applied", job_link=job_link)

    return app_id


# ---------------- UPDATE ----------------
def update_application_record(app_id, **fields):
    """
    Updates any subset of fields (company, role, job_link, jd_text, status, notes).
    Automatically re-embeds the vector using fresh data after the update.
    """
    updated = db.update_application(app_id, **fields)
    if not updated:
        return False

    # Re-fetch full record to rebuild the embedding with latest data
    row = db.get_application_by_id(app_id)
    if not row:
        return False

    # row columns: id, company, role, job_link, jd_text, resume_filename, resume_text, date_applied, status, notes
    _, company, role, job_link, jd_text, resume_filename, resume_text, date_applied, status, notes = row

    _upsert_vector(app_id, company, role, jd_text, resume_text, notes, status, job_link)
    return True


def replace_resume(app_id, new_resume_bytes, new_resume_original_filename):
    """
    Replaces the resume file for an existing application:
    deletes old file, saves new one, re-extracts text, re-embeds vector.
    """
    row = db.get_application_by_id(app_id)
    if not row:
        return False

    old_resume_filename = row[5]  # resume_filename column

    # Delete old file
    if old_resume_filename:
        old_path = os.path.join(RESUMES_DIR, old_resume_filename)
        if os.path.exists(old_path):
            os.remove(old_path)

    # Save new file
    os.makedirs(RESUMES_DIR, exist_ok=True)
    ext = os.path.splitext(new_resume_original_filename)[1].lower()
    new_filename = f"app_{app_id}{ext}"
    new_path = os.path.join(RESUMES_DIR, new_filename)

    with open(new_path, "wb") as f:
        f.write(new_resume_bytes)

    # Extract new text
    result = extract_resume_text(new_path)
    resume_text = result["text"] if result["success"] else ""

    # Update DB + re-embed
    update_application_record(app_id, resume_filename=new_filename, resume_text=resume_text)

    return True


# ---------------- DELETE ----------------
def delete_application_record(app_id):
    """
    Permanently deletes an application: SQLite row + resume file on disk + ChromaDB vector.
    """
    row = db.get_application_by_id(app_id)
    if not row:
        return False

    resume_filename = row[5]  # resume_filename column

    # 1. Delete resume file from disk
    if resume_filename:
        resume_path = os.path.join(RESUMES_DIR, resume_filename)
        if os.path.exists(resume_path):
            os.remove(resume_path)

    # 2. Delete vector from ChromaDB
    _delete_vector(app_id)

    # 3. Delete SQLite row
    db.delete_application(app_id)

    return True


if __name__ == "__main__":
    db.init_db()
    print("✅ sync.py ready — CRUD across SQLite + resumes/ + ChromaDB is wired up.")