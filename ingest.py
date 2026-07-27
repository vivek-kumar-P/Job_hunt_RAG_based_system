import os
import chromadb
from sentence_transformers import SentenceTransformer

# --- Config ---
DATA_DIR = "data"
DB_DIR = "chroma_db"
COLLECTION_NAME = "job_hunt_memory"

# --- Setup ---
print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

client = chromadb.PersistentClient(path=DB_DIR)
collection = client.get_or_create_collection(name=COLLECTION_NAME)

# --- Read all files from data/ subfolders ---
def load_documents():
    docs = []
    for category in os.listdir(DATA_DIR):
        category_path = os.path.join(DATA_DIR, category)
        if not os.path.isdir(category_path):
            continue
        for filename in os.listdir(category_path):
            if filename.endswith(".txt"):
                filepath = os.path.join(category_path, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    docs.append({
                        "id": f"{category}_{filename}",
                        "text": content,
                        "category": category,
                        "filename": filename
                    })
    return docs

# --- Ingest into ChromaDB ---
def ingest():
    docs = load_documents()
    if not docs:
        print("No documents found. Add some .txt files under data/jds, data/resumes, data/notes.")
        return

    print(f"Found {len(docs)} documents. Embedding and storing...")

    texts = [d["text"] for d in docs]
    embeddings = model.encode(texts).tolist()

    collection.upsert(
        ids=[d["id"] for d in docs],
        embeddings=embeddings,
        documents=texts,
        metadatas=[{"category": d["category"], "filename": d["filename"]} for d in docs]
    )

    print(f"✅ Ingested {len(docs)} documents into ChromaDB at '{DB_DIR}'")

if __name__ == "__main__":
    ingest()