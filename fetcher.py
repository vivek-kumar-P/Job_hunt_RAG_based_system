import trafilatura

def fetch_jd_text(url: str) -> dict:
    """
    Fetches a job posting URL and extracts the main readable content.
    Returns a dict with success flag, extracted text, and title (if found).
    """
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return {
                "success": False,
                "text": "",
                "title": "",
                "error": "Could not fetch the page. It may be blocking automated requests or the link is invalid."
            }

        text = trafilatura.extract(downloaded, include_comments=False, include_tables=True)
        metadata = trafilatura.extract_metadata(downloaded)
        title = metadata.title if metadata and metadata.title else ""

        if not text or len(text.strip()) < 50:
            return {
                "success": False,
                "text": "",
                "title": title,
                "error": "Page fetched but no meaningful content could be extracted. Try pasting the JD manually."
            }

        return {
            "success": True,
            "text": text.strip(),
            "title": title,
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "text": "",
            "title": "",
            "error": f"Fetch failed: {str(e)}"
        }


if __name__ == "__main__":
    # Quick test using the Accenture link
    test_url = "https://www.accenture.com/in-en/careers/jobdetails?id=ATCI-5683942-S2058933_en&title=Application+Support"
    result = fetch_jd_text(test_url)

    print("Success:", result["success"])
    print("Title:", result["title"])
    print("Error:", result["error"])
    print("\n--- Extracted Text (first 800 chars) ---\n")
    print(result["text"][:800])