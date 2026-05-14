# app/parsers/pypdf_parser.py

import os
from typing import List, Dict, Any
from pypdf import PdfReader
from app.parsers.base_parser import BaseParser
from app.utils.cleaner import clean_text


class PyPdfParser(BaseParser):

    def parse(self, file_path: str) -> List[Dict[str, Any]]:

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        documents = []

        try:
            reader = PdfReader(file_path)

            base_metadata = {
                "source": os.path.basename(file_path),
                "total_pages": len(reader.pages),
                "author": reader.metadata.author if reader.metadata else "Unknown"
            }

            for i, page in enumerate(reader.pages):
                page_number = i + 1

                raw_text = page.extract_text()

                if not raw_text or len(raw_text.strip()) < 10:
                    print(f"Page {page_number} skipped (likely scanned).")
                    continue

                processed_text = clean_text(raw_text)

                documents.append({
                    "content": processed_text,
                    "metadata": {
                        **base_metadata,
                        "page": page_number
                    }
                })

            print(f"Parsed {len(documents)} pages from {file_path}")

            return documents

        except Exception as e:
            raise RuntimeError(f"Error parsing file: {file_path}") from e
