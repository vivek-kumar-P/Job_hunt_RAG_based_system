import os
import streamlit as st
import chromadb
from sentence_transformers import SentenceTransformer
from google import genai
from dotenv import load_dotenv

# --- Config ---
DB_DIR = "chroma_db"
COLLECTION_NAME = "job_hunt_memory"
TOP_K = 3
MODEL_NAME = "gemini-3.5-flash"
DATA_DIR = "data"

# --- Load env vars ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Cache heavy resources ---
@st.cache_resource
def load_embedding_model():
    return SentenceTransformer("all-MiniLM-L6-v2")

@st.cache_resource
def load_chroma_collection():
    client = chromadb.PersistentClient(path=DB_DIR)
    return client.get_or_create_collection(name=COLLECTION_NAME)

@st.cache_resource
def load_genai_client():
    return genai.Client(api_key=GEMINI_API_KEY)

model = load_embedding_model()
collection = load_chroma_collection()
client_genai = load_genai_client()

# --- Core functions ---
def retrieve(query, top_k=TOP_K):
    query_embedding = model.encode([query]).tolist()
    results = collection.query(query_embeddings=query_embedding, n_results=top_k)
    return results["documents"][0], results["metadatas"][0]

def build_prompt(query, docs, metadatas):
    context_blocks = [f"[{m['category']} - {m['filename']}]\n{d}" for d, m in zip(docs, metadatas)]
    context = "\n\n".join(context_blocks)
    return f"""You are a helpful assistant answering questions about the user's job applications, resumes, and interview notes.

Use ONLY the context below to answer. If the answer isn't in the context, say so.

Context:
{context}

Question: {query}

Answer:"""

def ask(query):
    docs, metadatas = retrieve(query)
    prompt = build_prompt(query, docs, metadatas)
    response = client_genai.models.generate_content(model=MODEL_NAME, contents=prompt)
    return response.text, metadatas

def ingest_file(uploaded_file, category):
    category_dir = os.path.join(DATA_DIR, category)
    os.makedirs(category_dir, exist_ok=True)
    filepath = os.path.join(category_dir, uploaded_file.name)

    with open(filepath, "wb") as f:
        f.write(uploaded_file.getbuffer())

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read().strip()

    if content:
        embedding = model.encode([content]).tolist()
        collection.upsert(
            ids=[f"{category}_{uploaded_file.name}"],
            embeddings=embedding,
            documents=[content],
            metadatas=[{"category": category, "filename": uploaded_file.name}]
        )

# --- UI ---
st.set_page_config(page_title="Job Hunt Memory", page_icon="🎯")
st.title("🎯 Job Hunt Memory")
st.caption("RAG assistant for your job applications, resumes, and notes")

# Sidebar: upload new documents
with st.sidebar:
    st.header("📁 Add a document")
    category = st.selectbox("Category", ["jds", "resumes", "notes"])
    uploaded_file = st.file_uploader("Upload a .txt file", type=["txt"])
    if uploaded_file and st.button("Ingest"):
        ingest_file(uploaded_file, category)
        st.success(f"Ingested {uploaded_file.name} into '{category}'")

# Chat state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg["role"] == "assistant" and "sources" in msg:
            with st.expander("Sources"):
                for src in msg["sources"]:
                    st.write(f"- {src['category']}/{src['filename']}")

# Chat input
if query := st.chat_input("Ask about your job applications..."):
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.write(query)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            answer, sources = ask(query)
        st.write(answer)
        with st.expander("Sources"):
            for src in sources:
                st.write(f"- {src['category']}/{src['filename']}")

    st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})