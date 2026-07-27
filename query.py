import os
import chromadb
from sentence_transformers import SentenceTransformer
from google import genai
from dotenv import load_dotenv

# --- Config ---
DB_DIR = "chroma_db"
COLLECTION_NAME = "job_hunt_memory"
TOP_K = 3
MODEL_NAME = "gemini-3.5-flash"

# --- Load env vars ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env")

client_genai = genai.Client(api_key=GEMINI_API_KEY)

# --- Setup ---
print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

client = chromadb.PersistentClient(path=DB_DIR)
collection = client.get_or_create_collection(name=COLLECTION_NAME)

def retrieve(query, top_k=TOP_K):
    query_embedding = model.encode([query]).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k
    )
    docs = results["documents"][0]
    metadatas = results["metadatas"][0]
    return docs, metadatas

def build_prompt(query, docs, metadatas):
    context_blocks = []
    for doc, meta in zip(docs, metadatas):
        context_blocks.append(f"[{meta['category']} - {meta['filename']}]\n{doc}")
    context = "\n\n".join(context_blocks)

    prompt = f"""You are a helpful assistant answering questions about the user's job applications, resumes, and interview notes.

Use ONLY the context below to answer. If the answer isn't in the context, say so.

Context:
{context}

Question: {query}

Answer:"""
    return prompt

def ask(query):
    docs, metadatas = retrieve(query)
    prompt = build_prompt(query, docs, metadatas)

    response = client_genai.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    print("\n--- Answer ---")
    print(response.text)

    print("\n--- Sources used ---")
    for meta in metadatas:
        print(f"- {meta['category']}/{meta['filename']}")

if __name__ == "__main__":
    print("Job Hunt Memory — ask me anything (type 'exit' to quit)\n")
    while True:
        query = input("You: ")
        if query.lower() in ("exit", "quit"):
            break
        ask(query)
        print()