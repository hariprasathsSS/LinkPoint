# app/detectors/pdf_detector.py

from pypdf import PdfReader


# app/detectors/parser_detector.py

from pypdf import PdfReader


class PDFDetector:

    @staticmethod
    def detect(file_path: str) -> dict:
        reader = PdfReader(file_path)

        sample_pages = min(3, len(reader.pages))

        total_text = ""
        image_count = 0

        for i in range(sample_pages):
            page = reader.pages[i]

            # ✅ Extract text safely
            text = page.extract_text()
            if text:
                total_text += text

            # ✅ FIXED: safe resource access
            try:
                resources = page.get("/Resources")

                if resources and "/XObject" in resources:
                    xObject = resources["/XObject"].get_object()

                    for obj in xObject:
                        if xObject[obj].get("/Subtype") == "/Image":
                            image_count += 1

            except Exception:
                # ignore malformed pages
                continue

        text_length = len(total_text.strip())

        return {
            "type": "scanned" if text_length < 50 else "digital",
            "has_images": image_count > 0,
            "text_length": text_length
        }
