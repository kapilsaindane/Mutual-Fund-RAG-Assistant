import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[3]
INPUT_PATH = ROOT / "ingestion" / "phase-2" / "2.3-cleaner" / "output" / "cleaned-latest.json"
OUTPUT_DIR = ROOT / "ingestion" / "phase-2" / "2.4-chunker" / "output"
OUTPUT_PATH = OUTPUT_DIR / "chunks-latest.json"

TARGET_MIN = 600
TARGET_MAX = 900
OVERLAP = 150
CLEANER_VERSION = "2.3-v1"

RELEVANCE_KEYWORDS = {
    "mutual fund",
    "fund",
    "sip",
    "nav",
    "expense ratio",
    "exit load",
    "lock-in",
    "risk",
    "benchmark",
    "aum",
    "scheme",
    "elss",
    "direct growth",
    "fund manager",
    "portfolio",
    "minimum investment",
}

NOISE_KEYWORDS = {
    "stocks",
    "intraday",
    "ipo",
    "option chain",
    "demat",
    "f&o",
    "api trading",
    "brokerage calculator",
    "margin calculator",
    "share market today",
}


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "")
    return text.strip()


def extract_scheme_from_url(url: str) -> str:
    slug = urlparse(url).path.split("/")[-1]
    name = slug.replace("-", " ").strip()
    return " ".join(part.capitalize() for part in name.split())


def relevance_score(text: str) -> float:
    lowered = text.lower()
    positive = sum(1 for kw in RELEVANCE_KEYWORDS if kw in lowered)
    negative = sum(1 for kw in NOISE_KEYWORDS if kw in lowered)
    length_bonus = 1 if len(text) >= 80 else 0
    raw_score = positive - (0.8 * negative) + length_bonus
    return round(max(0.0, raw_score / 6.0), 4)


def is_relevant(text: str, threshold: float = 0.25) -> bool:
    if not text or len(text) < 30:
        return False
    return relevance_score(text) >= threshold


def make_chunks(text: str) -> list[str]:
    text = normalize_text(text)
    if not text:
        return []
    chunks = []
    start = 0
    n = len(text)

    while start < n:
        end = min(n, start + TARGET_MAX)
        if end < n:
            window = text[start:end]
            split_at = max(window.rfind(". "), window.rfind("; "), window.rfind(", "))
            if split_at >= TARGET_MIN:
                end = start + split_at + 1
            elif end - start < TARGET_MIN:
                end = min(n, start + TARGET_MIN)

        chunk = normalize_text(text[start:end])
        if chunk:
            chunks.append(chunk)

        if end >= n:
            break
        start = max(0, end - OVERLAP)

    return chunks


def run() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with INPUT_PATH.open("r", encoding="utf-8") as f:
        cleaned = json.load(f)

    all_chunks = []
    per_doc_counts = []

    for doc_idx, doc in enumerate(cleaned.get("documents", []), start=1):
        doc_url = doc.get("url", "")
        source_date = doc.get("source_fetched_at")
        scheme = extract_scheme_from_url(doc_url)
        doc_type = "html_fund_page"
        doc_chunks = 0

        sections = doc.get("sections", [])
        for sec_idx, section in enumerate(sections, start=1):
            heading = normalize_text(section.get("heading", "")) or "Document"
            content_items = [normalize_text(c) for c in section.get("content", []) if normalize_text(c)]
            section_text = normalize_text(" ".join(content_items))
            score = relevance_score(section_text)

            if not is_relevant(section_text):
                continue

            for chunk_idx, chunk_text in enumerate(make_chunks(section_text), start=1):
                chunk_id = f"c-{doc_idx:02d}-{sec_idx:03d}-{chunk_idx:03d}"
                all_chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "text": chunk_text,
                        "metadata": {
                            "source_url": doc_url,
                            "source_date": source_date,
                            "scheme": scheme,
                            "doc_type": doc_type,
                            "section_heading": heading,
                            "cleaner_version": CLEANER_VERSION,
                            "relevance_score": score,
                        },
                    }
                )
                doc_chunks += 1

        # Fallback mode when heading quality/relevance is poor.
        if doc_chunks == 0:
            fallback_text = normalize_text(doc.get("full_text", ""))
            paragraphs = [p.strip() for p in re.split(r"(?<=[.!?])\s+", fallback_text) if p.strip()]
            filtered = [p for p in paragraphs if is_relevant(p, threshold=0.2)]
            joined = normalize_text(" ".join(filtered))
            for chunk_idx, chunk_text in enumerate(make_chunks(joined), start=1):
                chunk_id = f"c-{doc_idx:02d}-999-{chunk_idx:03d}"
                all_chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "text": chunk_text,
                        "metadata": {
                            "source_url": doc_url,
                            "source_date": source_date,
                            "scheme": scheme,
                            "doc_type": doc_type,
                            "section_heading": "Document",
                            "cleaner_version": CLEANER_VERSION,
                            "relevance_score": relevance_score(chunk_text),
                        },
                    }
                )
                doc_chunks += 1

        per_doc_counts.append({"url": doc_url, "chunk_count": doc_chunks})

    output = {
        "phase": "2.4",
        "generated_at": iso_now(),
        "input_cleaned_file": "ingestion/phase-2/2.3-cleaner/output/cleaned-latest.json",
        "chunking_strategy": {
            "target_min_chars": TARGET_MIN,
            "target_max_chars": TARGET_MAX,
            "overlap_chars": OVERLAP,
            "mode": "section-first with paragraph fallback",
        },
        "total_chunks": len(all_chunks),
        "documents": per_doc_counts,
        "chunks": all_chunks,
    }

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote chunk output to: {OUTPUT_PATH}")
    print(f"Total chunks: {len(all_chunks)}")


if __name__ == "__main__":
    run()
