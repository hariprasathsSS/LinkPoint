# app/parsers/hybrid_parser.py

import pdfplumber
import pytesseract
from PIL import Image


class HybridParser:

    def parse(self, file_path: str) -> str:
        final_text = []

        with pdfplumber.open(file_path) as pdf:

            for page_num, page in enumerate(pdf.pages):

                page_text_parts = []

                # 1️⃣ Extract normal text
                text = page.extract_text()
                if text:
                    page_text_parts.append(text)

                # 2️⃣ Extract tables
                tables = page.extract_tables()

                for table in tables:
                    table_text = self._convert_table_to_text(table)
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

                        if ocr_text.strip():
                            page_text_parts.append(ocr_text)

                    except Exception:
                        continue

                # Merge page content
                final_text.append("\n".join(page_text_parts))

        return "\n\n".join(final_text)

    def _convert_table_to_text(self, table):
        rows = []
        for row in table:
            cleaned_row = [cell if cell else "" for cell in row]
            rows.append(" | ".join(cleaned_row))
        return "\n".join(rows)
