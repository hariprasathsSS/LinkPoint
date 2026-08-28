# app/parsers/hybrid_parser.py

import os
import pdfplumber
import pytesseract
from PIL import Image
from app.utils.cleaner import clean_text

class HybridParser:

    def parse(self, file_path: str) -> str:
        documents = []
        with pdfplumber.open(file_path) as pdf:

            base_metadata = {
                "source": os.path.basename(file_path),
                "total_pages": len(pdf.pages),
                "author": "Unknown"
            }

            for page_num, page in enumerate(pdf.pages):

                page_text_parts = []

                # 1️⃣ Extract normal text
                text = page.extract_text()
                if text:
                    text = clean_text(text)
                    page_text_parts.append(text)

                # 2️⃣ Extract tables
                tables = page.extract_tables()

                for table in tables:
                    table_text = self._convert_table_to_text(table)
                    table_text = clean_text(table_text)
                    page_text_parts.append(table_text)

                # 3️⃣ Extract images → OCR
                images = page.images

                for img in images:
                    try:
                        cropped = page.crop((
                            img["x0"], img["top"],
                            img["x1"], img["bottom"]
                        ))

                        pil_img = cropped.to_image().original
                        ocr_text = pytesseract.image_to_string(pil_img)

                        ocr_text = clean_text(ocr_text)
                        if ocr_text:
                            page_text_parts.append(ocr_text)

                    except Exception:
                        continue

                # Merge page content
                processed_text = "\n".join(page_text_parts)
                documents.append({
                    "content": processed_text,
                    "metadata": {
                        **base_metadata,
                        "page": page_num
                    }
                })

        return documents

    def _convert_table_to_text(self, table):
        rows = []
        for row in table:
            cleaned_row = [cell if cell else "" for cell in row]
            rows.append(" | ".join(cleaned_row))
        return "\n".join(rows)
