import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXTRACTED_INPUT_PATH = ROOT / "ingestion" / "phase-2" / "2.2-extractor" / "output" / "extracted-latest.json"
OUTPUT_DIR = ROOT / "ingestion" / "phase-2" / "2.3-cleaner" / "output"
OUTPUT_PATH = OUTPUT_DIR / "cleaned-latest.json"


BOILERPLATE_PATTERNS = [
    r"(?i)^download app$",
    r"(?i)^open demat account$",
    r"(?i)^invest now$",
    r"(?i)^sign in$",
    r"(?i)^sign up$",
    r"(?i)^login$",
    r"(?i)^read more$",
    r"(?i)^view all$",
]


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_whitespace(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"[\t\r\n]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_symbols(text: str) -> str:
    text = text.replace("•", "- ")
    text = text.replace("●", "- ")
    text = text.replace("₹", "Rs ")
    return text


def is_boilerplate(text: str) -> bool:
    if len(text) <= 2:
        return True
    for pattern in BOILERPLATE_PATTERNS:
        if re.match(pattern, text):
            return True
    return False


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen = set()
    output = []
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def clean_content_items(items: list[str]) -> list[str]:
    cleaned = []
    for raw in items:
        text = normalize_symbols(normalize_whitespace(raw))
        if not text or is_boilerplate(text):
            continue
        cleaned.append(text)
    return dedupe_preserve_order(cleaned)


def run() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with EXTRACTED_INPUT_PATH.open("r", encoding="utf-8") as f:
        extracted = json.load(f)

    cleaned_documents = []
    total_removed_lines = 0

    for doc in extracted.get("documents", []):
        cleaned_sections = []
        for section in doc.get("sections", []):
            heading = normalize_symbols(normalize_whitespace(section.get("heading", "")))
            if not heading:
                heading = "Untitled Section"

            original_content = section.get("content", [])
            cleaned_content = clean_content_items(original_content)
            total_removed_lines += max(0, len(original_content) - len(cleaned_content))

            if not cleaned_content:
                continue

            cleaned_sections.append(
                {
                    "heading_level": section.get("heading_level", "h2"),
                    "heading": heading,
                    "content": cleaned_content,
                }
            )

        cleaned_full_text = " ".join(
            content for sec in cleaned_sections for content in sec.get("content", [])
        )
        cleaned_full_text = normalize_whitespace(cleaned_full_text)

        cleaned_documents.append(
            {
                "url": doc.get("url"),
                "source_fetched_at": doc.get("source_fetched_at"),
                "response_fingerprint": doc.get("response_fingerprint"),
                "format": doc.get("format", "html"),
                "sections": cleaned_sections,
                "full_text": cleaned_full_text,
            }
        )

    output = {
        "phase": "2.3",
        "generated_at": iso_now(),
        "input_extracted_file": "ingestion/phase-2/2.2-extractor/output/extracted-latest.json",
        "document_count": len(cleaned_documents),
        "removed_noise_lines": total_removed_lines,
        "documents": cleaned_documents,
    }

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote cleaner output to: {OUTPUT_PATH}")
    print(f"Documents cleaned: {len(cleaned_documents)}")
    print(f"Removed noisy lines: {total_removed_lines}")


if __name__ == "__main__":
    run()
