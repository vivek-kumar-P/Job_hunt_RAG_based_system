import db
import sync

def resync_all():
    rows = db.get_all_applications()
    print(f"Found {len(rows)} applications to re-embed...")

    for row in rows:
        app_id = row[0]
        full_row = db.get_application_by_id(app_id)
        _, company, role, job_link, jd_text, resume_filename, resume_text, date_applied, status, notes = full_row

        sync._upsert_vector(app_id, company, role, jd_text, resume_text, notes, status, job_link)
        print(f"  Re-embedded: {company} — {role}")

    print("✅ Done. Vector DB now matches your real applications only.")

if __name__ == "__main__":
    resync_all()