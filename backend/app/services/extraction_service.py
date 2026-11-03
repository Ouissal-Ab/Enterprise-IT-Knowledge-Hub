from pathlib import Path

import fitz  # PyMuPDF
from bs4 import BeautifulSoup


def _extract_pdf(path: Path) -> list[tuple[int, str]]:
    pages = []
    with fitz.open(path) as pdf:
        for index, page in enumerate(pdf, start=1):
            tables = page.find_tables().tables
            table_boxes = [fitz.Rect(t.bbox) for t in tables]

            items = []  # (position verticale, texte)
            for block in page.get_text("blocks"):
                x0, y0, x1, y1, text = block[:5]
                rect = fitz.Rect(x0, y0, x1, y1)
                if any(rect.intersects(box) for box in table_boxes):
                    continue
                if text.strip():
                    items.append((y0, text.strip()))

            for table in tables:
                rows = []
                for row in table.extract():
                    cells = [(cell or "").replace("\n", " ").strip() for cell in row]
                    rows.append(" | ".join(cells))
                items.append((table.bbox[1], "\n".join(rows)))

            items.sort(key=lambda item: item[0])
            text = "\n".join(t for _, t in items).strip()
            if text:
                pages.append((index, text))
    return pages


def _extract_html(path: Path) -> list[tuple[int, str]]:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()

    for table in soup.find_all("table"):
        lines = []
        for row in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])]
            lines.append(" | ".join(cells))
        table.replace_with("\n" + "\n".join(lines) + "\n")

    text = soup.get_text(separator="\n").strip()
    return [(1, text)] if text else []


def extract_pages(file_path: str, file_type: str) -> list[tuple[int, str]]:
    """Retourne une liste de (numéro_de_page, texte)."""
    path = Path(file_path)

    if file_type == "pdf":
        return _extract_pdf(path)
    if file_type == "html":
        return _extract_html(path)
    if file_type == "md":
        text = path.read_text(encoding="utf-8").strip()
        return [(1, text)] if text else []

    raise ValueError(f"Type de fichier non géré : {file_type}")