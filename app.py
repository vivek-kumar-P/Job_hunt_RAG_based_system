import os
import streamlit as st
from google import genai
from dotenv import load_dotenv
import time
from google.genai import types

import db
import sync
from fetcher import fetch_jd_text
from sync import _get_model, _get_collection

MODEL_NAME = "gemini-3.5-flash"
FALLBACK_MODEL = "gemini-2.5-flash-lite"

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

st.set_page_config(page_title="Job Hunt Memory", page_icon="🎯", layout="centered")

st.markdown("""
<style>
    /* Base cleanup */
    .block-container {
        padding-top: 1.5rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 800px;
    }

    /* Bigger, touch-friendly buttons everywhere */
    .stButton button, .stDownloadButton button, .stFormSubmitButton button {
        min-height: 44px;
        border-radius: 8px;
        font-size: 15px;
        width: 100%;
    }

    /* Expander cards */
    div[data-testid="stExpander"] {
        border: 1px solid rgba(128,128,128,0.2);
        border-radius: 10px;
        margin-bottom: 10px;
    }

    /* Tabs: keep readable, no wrap issues */
    button[data-baseweb="tab"] {
        font-size: 14px;
        padding: 8px 10px;
    }

    /* Mobile-specific: screens under 768px */
    @media (max-width: 768px) {
        .block-container {
            padding-left: 0.6rem;
            padding-right: 0.6rem;
        }
        h1 { font-size: 1.5rem !important; }
        h3 { font-size: 1.1rem !important; }
        .stTextInput input, .stTextArea textarea {
            font-size: 16px !important; /* prevents iOS auto-zoom on focus */
        }
        div[data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
        }
    }
</style>
""", unsafe_allow_html=True)


# ---------------- Custom styling ----------------

@st.cache_resource
def load_genai_client():
    return genai.Client(api_key=GEMINI_API_KEY)

client_genai = load_genai_client()

def generate_with_fallback(prompt):
    for model_name in [MODEL_NAME, FALLBACK_MODEL]:
        try:
            response = client_genai.models.generate_content(model=model_name, contents=prompt)
            return response.text
        except Exception as e:
            st.toast(f"⚠️ {model_name} failed: {type(e).__name__}: {str(e)[:150]}", icon="⚠️")
            continue
    return None

st.title("🎯 Job Hunt Memory")
st.caption("Track applications, manage resumes, and ask questions about your job hunt")

tab1, tab2, tab3 = st.tabs(["➕ Add Application", "📋 My Applications", "💬 Ask"])

# ==================== TAB 1: ADD ====================
with tab1:
    st.subheader("Add a new application")

    if "fetched_jd" not in st.session_state:
        st.session_state.fetched_jd = ""
    if "fetched_title" not in st.session_state:
        st.session_state.fetched_title = ""

    job_link = st.text_input(
        "Job link",
        placeholder="Paste the direct job posting URL (not a search page)",
        help="Works best with company career pages or a single job's detail page."
    )

    if st.button("🔗 Fetch job description", use_container_width=False):
        if not job_link.strip():
            st.toast("⚠️ Paste a job link first.", icon="⚠️")
        else:
            with st.spinner("Fetching job description..."):
                result = fetch_jd_text(job_link)
            if result["success"]:
                st.session_state.fetched_jd = result["text"]
                st.session_state.fetched_title = result["title"]
                st.toast("✅ Job description fetched — review it below.", icon="✅")
            else:
                st.toast(f"⚠️ {result['error']}", icon="⚠️")

    st.divider()

    with st.form("add_application_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            company = st.text_input("Company *", placeholder="e.g. Accenture")
        with col2:
            role = st.text_input("Role *", value=st.session_state.fetched_title, placeholder="e.g. Data Analyst")

        jd_text = st.text_area(
            "Job Description",
            value=st.session_state.fetched_jd,
            height=180,
            placeholder="Fetched JD will appear here — or paste it manually if fetch didn't work."
        )
        resume_file = st.file_uploader("Resume *", type=["pdf", "docx"], help="PDF or DOCX only")
        notes = st.text_area("Notes (optional)", height=70, placeholder="Any extra context, referral info, etc.")

        submitted = st.form_submit_button("✅ Save Application", type="primary", use_container_width=True)

        if submitted:
            missing = []
            if not company.strip(): missing.append("Company")
            if not role.strip(): missing.append("Role")
            if not resume_file: missing.append("Resume")

            if missing:
                st.toast(f"⚠️ Missing: {', '.join(missing)}", icon="⚠️")
            else:
                try:
                    with st.spinner("Saving..."):
                        app_id = sync.create_application_record(
                            company=company.strip(),
                            role=role.strip(),
                            job_link=job_link.strip(),
                            jd_text=jd_text.strip(),
                            resume_file_bytes=resume_file.getbuffer(),
                            resume_original_filename=resume_file.name,
                            notes=notes.strip()
                        )
                    st.session_state.fetched_jd = ""
                    st.session_state.fetched_title = ""
                    st.toast(f"✅ Saved: {company} — {role}", icon="✅")
                    st.rerun()
                except Exception as e:
                    st.toast(f"⚠️ Save failed: {str(e)}", icon="⚠️")

# ==================== TAB 2: MY APPLICATIONS ====================
with tab2:
    st.subheader("Your applications")

    rows = db.get_all_applications()

    if not rows:
        st.info("No applications yet — add your first one in the **Add Application** tab.")
    else:
        status_options = ["All", "applied", "interview", "rejected", "offer"]
        status_filter = st.selectbox("Filter by status", status_options)

        filtered = [r for r in rows if status_filter == "All" or r[6] == status_filter]

        if not filtered:
            st.info(f"No applications with status '{status_filter}'.")

        status_icons = {"applied": "📤", "interview": "🎤", "rejected": "❌", "offer": "🎉"}

        for row in filtered:
            app_id, company, role, job_link, resume_filename, date_applied, status = row
            icon = status_icons.get(status, "•")

            with st.expander(f"{icon} **{company}** — {role}  ·  {date_applied}"):
                full_row = db.get_application_by_id(app_id)
                _, _, _, _, jd_text, _, resume_text, _, _, notes = full_row

                if job_link:
                    st.markdown(f"🔗 [Job posting]({job_link})")

                st.markdown(f"📄 Resume: `{resume_filename or 'N/A'}`")

                resume_path = os.path.join("resumes", resume_filename) if resume_filename else None

                if resume_path and os.path.exists(resume_path):
                    with open(resume_path, "rb") as f:
                        resume_bytes = f.read()

                    ext = os.path.splitext(resume_filename)[1].lower()

                    vcol1, vcol2, vcol3 = st.columns([1, 1, 1])
                    with vcol1:
                        view_clicked = st.button("👁️ View resume", key=f"view_{app_id}")
                    with vcol2:
                        st.download_button(
                            "⬇️ Download",
                            data=resume_bytes,
                            file_name=resume_filename,
                            key=f"download_{app_id}"
                        )
                    with vcol3:
                        replace_clicked = st.button("🔄 Replace", key=f"replace_btn_{app_id}")

                    if view_clicked:
                        st.session_state[f"show_resume_{app_id}"] = not st.session_state.get(f"show_resume_{app_id}", False)

                    if replace_clicked:
                        st.session_state[f"show_replace_{app_id}"] = not st.session_state.get(f"show_replace_{app_id}", False)

                    # Inline preview
                    if st.session_state.get(f"show_resume_{app_id}"):
                        if ext == ".pdf":
                            import base64
                            b64_pdf = base64.b64encode(resume_bytes).decode("utf-8")
                            pdf_display = f"""
                                <iframe src="data:application/pdf;base64,{b64_pdf}"
                                        width="100%" height="600px" style="border:1px solid #444; border-radius:8px;">
                                </iframe>
                            """
                            st.markdown(pdf_display, unsafe_allow_html=True)
                        else:
                            st.text_area("Resume content (text preview)", value=resume_text or "No text extracted.", height=400, key=f"preview_{app_id}")

                    # Inline replace uploader
                    if st.session_state.get(f"show_replace_{app_id}"):
                        new_resume = st.file_uploader(
                            "Upload new resume",
                            type=["pdf", "docx"],
                            key=f"replace_upload_{app_id}"
                        )
                        if new_resume and st.button("Confirm replace", key=f"confirm_replace_{app_id}"):
                            sync.replace_resume(app_id, new_resume.getbuffer(), new_resume.name)
                            st.toast(f"✅ Resume replaced for {company}", icon="✅")
                            st.session_state[f"show_replace_{app_id}"] = False
                            st.rerun()
                else:
                    st.warning("Resume file not found on disk.")

                c1, c2 = st.columns([1, 2])
                with c1:
                    new_status = st.selectbox(
                        "Status", ["applied", "interview", "rejected", "offer"],
                        index=["applied", "interview", "rejected", "offer"].index(status),
                        key=f"status_{app_id}"
                    )
                    if new_status != status:
                        sync.update_application_record(app_id, status=new_status)
                        st.toast(f"✅ Status updated to '{new_status}'", icon="✅")
                        st.rerun()

                new_notes = st.text_area("Notes", value=notes or "", key=f"notes_{app_id}", height=80)

                cbtn1, cbtn2, cbtn3 = st.columns([1, 1, 3])
                with cbtn1:
                    if st.button("💾 Save notes", key=f"save_{app_id}"):
                        sync.update_application_record(app_id, notes=new_notes)
                        st.toast("✅ Notes saved", icon="✅")
                        st.rerun()
                with cbtn2:
                    if st.button("🗑️ Delete", key=f"del_{app_id}"):
                        st.session_state[f"confirm_delete_{app_id}"] = True

                if st.session_state.get(f"confirm_delete_{app_id}"):
                    st.warning("This permanently deletes the application, resume file, and search index entry.")
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        if st.button("Yes, delete permanently", key=f"confirm_{app_id}", type="primary"):
                            sync.delete_application_record(app_id)
                            st.toast(f"🗑️ Deleted {company} — {role}", icon="🗑️")
                            del st.session_state[f"confirm_delete_{app_id}"]
                            st.rerun()
                    with cc2:
                        if st.button("Cancel", key=f"cancel_{app_id}"):
                            del st.session_state[f"confirm_delete_{app_id}"]
                            st.rerun()

                if jd_text:
                    with st.popover("View full JD"):
                        st.write(jd_text)

# ==================== TAB 3: ASK ====================
with tab3:
    st.subheader("Ask about your applications")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if not st.session_state.messages:
        st.info("Try asking things like *\"Which companies wanted Python skills?\"* or *\"Did I apply to any Bengaluru roles?\"*")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg["role"] == "assistant" and msg.get("sources"):
                with st.expander("Sources"):
                    for src in msg["sources"]:
                        st.write(f"- {src.get('company', '')} — {src.get('role', '')} ({src.get('status', '')})")

    if query := st.chat_input("Ask about your job applications..."):
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.write(query)

        with st.chat_message("assistant"):
            status_placeholder = st.empty()
            status_placeholder.info("🔎 Searching your applications...")

            model = _get_model()
            collection = _get_collection()

            if collection.count() == 0:
                status_placeholder.empty()
                answer = "You haven't added any applications yet — add one in the first tab and I'll be able to answer questions about it."
                metadatas = []
            else:
                query_embedding = model.encode([query]).tolist()
                results = collection.query(query_embeddings=query_embedding, n_results=3)
                docs = results["documents"][0]
                metadatas = results["metadatas"][0]

                context = "\n\n".join(docs)
                prompt = f"""You are a helpful assistant answering questions about the user's job applications.

Use ONLY the context below to answer. If the answer isn't in the context, say so.

Context:
{context}

Question: {query}

Answer:"""
                status_placeholder.info("🤖 Generating answer (up to ~25s)...")
                start_time = time.time()
                answer = generate_with_fallback(prompt)
                elapsed = round(time.time() - start_time, 1)

                status_placeholder.empty()

                if answer is None:
                    answer = f"⚠️ The AI model didn't respond after {elapsed}s. This is usually Google's servers being overloaded — please try again in a minute."
                    st.toast("⚠️ No response from AI — try again shortly.", icon="⚠️")

            st.write(answer)
            if metadatas:
                with st.expander("Sources"):
                    for src in metadatas:
                        st.write(f"- {src.get('company', '')} — {src.get('role', '')} ({src.get('status', '')})")

        st.session_state.messages.append({"role": "assistant", "content": answer, "sources": metadatas})