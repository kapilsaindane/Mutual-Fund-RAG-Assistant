import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FETCH_RUN_PATH = ROOT / "ingestion" / "phase-2" / "2.1-fetcher" / "output" / "fetch-run-latest.json"
OUTPUT_DIR = ROOT / "ingestion" / "phase-2" / "2.2-extractor" / "output"
OUTPUT_PATH = OUTPUT_DIR / "extracted-latest.json"


class SectionHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.skip_tags = {"script", "style", "noscript"}
        self.block_tags = {"p", "li", "td", "th", "div", "span"}
        self.heading_tags = {"h1", "h2", "h3"}
        self.in_skip_depth = 0
        self.current_tag = None
        self.current_buffer = []
        self.current_section = {"heading_level": "h1", "heading": "Document", "content": []}
        self.sections = []

    def handle_starttag(self, tag, attrs):  # noqa: ANN001
        self.current_tag = tag
        if tag in self.skip_tags:
            self.in_skip_depth += 1
        if tag in self.heading_tags:
            self.current_buffer = []

    def handle_endtag(self, tag):  # noqa: ANN001
        if tag in self.skip_tags and self.in_skip_depth > 0:
            self.in_skip_depth -= 1
            return
        if self.in_skip_depth > 0:
            return

        text = self._flush_buffer()
        if not text:
            return

        if tag in self.heading_tags:
            if self.current_section["content"]:
                self.sections.append(self.current_section)
            self.current_section = {
                "heading_level": tag,
                "heading": text,
                "content": [],
            }
        elif tag in self.block_tags:
            self.current_section["content"].append(text)

    def handle_data(self, data):  # noqa: ANN001
        if self.in_skip_depth > 0:
            return
        if data and data.strip():
            self.current_buffer.append(data.strip())

    def _flush_buffer(self) -> str:
        if not self.current_buffer:
            return ""
        text = " ".join(self.current_buffer)
        self.current_buffer = []
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def finalize(self):
        trailing = self._flush_buffer()
        if trailing:
            self.current_section["content"].append(trailing)
        if self.current_section["content"] or self.current_section["heading"] != "Document":
            self.sections.append(self.current_section)


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def extract_sections_from_html(html_text: str) -> list[dict]:
    parser = SectionHTMLParser()
    parser.feed(html_text)
    parser.finalize()
    return parser.sections


def normalize_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def run() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with FETCH_RUN_PATH.open("r", encoding="utf-8") as f:
        fetch_run = json.load(f)

    documents = []
    for result in fetch_run.get("results", []):
        if result.get("fetch_status") != "success":
            continue
        raw_rel = result.get("raw_snapshot_path")
        if not raw_rel:
            continue

        raw_path = ROOT / Path(raw_rel.replace("/", "\\"))
        if not raw_path.exists():
            continue

        html_text = raw_path.read_text(encoding="utf-8", errors="ignore")
        sections = extract_sections_from_html(html_text)
        cleaned_sections = []
        for section in sections:
            content_items = [normalize_text(item) for item in section.get("content", []) if normalize_text(item)]
            if not content_items and not section.get("heading"):
                continue
            cleaned_sections.append(
                {
                    "heading_level": section.get("heading_level", "h2"),
                    "heading": normalize_text(section.get("heading", "")),
                    "content": content_items,
                }
            )

        full_text = " ".join(
            item for sec in cleaned_sections for item in sec.get("content", [])
        )

        documents.append(
            {
                "url": result.get("url"),
                "source_fetched_at": result.get("fetched_at"),
                "response_fingerprint": result.get("response_fingerprint"),
                "raw_snapshot_path": result.get("raw_snapshot_path"),
                "format": "html",
                "sections": cleaned_sections,
                "full_text": normalize_text(full_text),
            }
        )

    payload = {
        "phase": "2.2",
        "generated_at": iso_now(),
        "input_fetch_run": "ingestion/phase-2/2.1-fetcher/output/fetch-run-latest.json",
        "document_count": len(documents),
        "documents": documents,
    }

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"Wrote extraction output to: {OUTPUT_PATH}")
    print(f"Documents extracted: {len(documents)}")


if __name__ == "__main__":
    run()
