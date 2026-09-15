import json
from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image


PDF_DIR = Path("data/pdfs")
OUTPUT_FILE = Path("data/extracted_text.json")

# If Tesseract is not in your Windows PATH,
# uncomment this and change the path if necessary.
# pytesseract.pytesseract.tesseract_cmd = (
#     r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# )


def extract_text_from_page(page):
    """
    Try normal PDF text extraction first.
    If no text is found, use OCR.
    """

    text = page.get_text("text").strip()

    if text:
        return text, "text"

    # Render PDF page as an image
    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2))

    image = Image.frombytes(
        "RGB",
        [pixmap.width, pixmap.height],
        pixmap.samples
    )

    # OCR the rendered page
    text = pytesseract.image_to_string(image).strip()

    return text, "ocr"


def extract_pdfs():
    documents = []

    pdf_files = list(PDF_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in: {PDF_DIR}")
        return

    print(f"Found {len(pdf_files)} PDF files.\n")

    for pdf_path in pdf_files:
        print(f"Processing: {pdf_path.name}")

        doc = pymupdf.open(pdf_path)

        pages = []
        text_pages = 0
        ocr_pages = 0
        empty_pages = 0

        for page_number, page in enumerate(doc, start=1):

            text, method = extract_text_from_page(page)

            if method == "text":
                text_pages += 1

            elif method == "ocr":
                ocr_pages += 1

            if not text:
                empty_pages += 1

            pages.append({
                "page_number": page_number,
                "text": text,
                "method": method
            })

        documents.append({
            "filename": pdf_path.name,
            "page_count": len(doc),
            "text_pages": text_pages,
            "ocr_pages": ocr_pages,
            "empty_pages": empty_pages,
            "pages": pages
        })

        doc.close()

        print(f"  Pages: {len(pages)}")
        print(f"  Normal text: {text_pages}")
        print(f"  OCR: {ocr_pages}")
        print(f"  Empty: {empty_pages}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(
            documents,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("\nExtraction complete.")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    extract_pdfs()