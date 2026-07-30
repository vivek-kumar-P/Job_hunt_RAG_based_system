# 🎯 Job Hunt Memory

A personal RAG-powered assistant that tracks every job application, resume version, and job description — so you never lose track of where you applied, what you sent, or what they wanted.

**Live demo:** https://jobhuntragbasedsystem.streamlit.app/

---

## Why

After 10s of applications, it's impossible to remember which resume went where, what each JD asked for, or which companies you already applied to. This tool fixes that with structured tracking + natural-language search over your own job hunt history.

## Features

- **Add applications** — paste a job link, auto-fetch the JD (via `trafilatura`), upload the resume you submitted
- **Track status** — applied / interview / rejected / offer, with notes per application
- **View & manage resumes** — inline PDF preview, download, or replace the file for any application
- **Full CRUD** — edit or permanently delete any record, synced across the database, files, and search index
- **Ask questions** — chat interface powered by RAG: *"Which companies wanted Python skills?"*, *"Did I apply to any Bengaluru roles?"*
- **Mobile-friendly** — responsive layout, tested on real devices

## Tech Stack

| Layer | Tool |
|---|---|
| Embeddings | `sentence-transformers` (all-MiniLM-L6-v2) |
| Vector search | ChromaDB |
| Structured storage | SQLite |
| LLM | Google Gemini API |
| Link → JD extraction | `trafilatura` |
| Resume parsing | `pypdf`, `python-docx` |
| UI | Streamlit |

Built in raw Python (no LangChain) — deliberately, for full interview explainability of the RAG pipeline.

## Architecture

```
Job link → fetcher.py → JD text
Resume file → resume_parser.py → extracted text
                    ↓
              sync.py (keeps in sync)
          ↓                    ↓
   applications.db      chroma_db (vectors)
      (SQLite)            (semantic search)
                    ↓
              app.py (Streamlit UI)
        Add | My Applications | Ask
```

Every application is stored as a structured SQLite record **and** embedded as a vector for semantic search — so you get both a reliable table view and natural-language Q&A.

## Setup

```bash
git clone https://github.com/vivek-kumar-P/Job_hunt_RAG_based_system.git
cd Job_hunt_RAG_based_system
pip install -r requirements.txt
```

Create a `.env` file:
```
GEMINI_API_KEY=your_key_here
```

Run:
```bash
python db.py            # initialize the database
python -m streamlit run app.py
```

## Known Limitations

- JavaScript-heavy career portals (e.g. IBM's Workday-based site) can't be auto-fetched — paste the JD manually as a fallback
- The public demo deploy has no persistent storage (Streamlit Cloud free tier) — data resets on redeploy. Run locally for real day-to-day tracking.

## Author

Vivek Kumar P — [GitHub](https://github.com/vivek-kumar-P)
