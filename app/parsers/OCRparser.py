# app/parsers/ocr_parser.py

import os
from typing import List, Dict, Any
import pytesseract
from pdf2image import convert_from_path
from app.parsers.base_parser import BaseParser
from app.utils.cleaner import clean_text


class OCRParser(BaseParser):

    def parse(self, file_path: str) -> List[Dict[str, Any]]:

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        documents = []

        try:
            images = convert_from_path(file_path)

            base_metadata = {
                "source": os.path.basename(file_path),
                "total_pages": len(images),
                "author": "Unknown"
            }

            for i, image in enumerate(images):
                page_number = i + 1

                raw_text = pytesseract.image_to_string(image)

                if not raw_text or len(raw_text.strip()) < 10:
                    print(f"Page {page_number} OCR empty/skipped.")
                    continue

                processed_text = clean_text(raw_text)

                documents.append({
                    "content": processed_text,
                    "metadata": {
                        **base_metadata,
                        "page": page_number
                    }
                })

            print(f"OCR parsed {len(documents)} pages from {file_path}")

            return documents

        except Exception as e:
            raise RuntimeError(f"Failed to parse PDF: {file_path}") from e
        return documents
