# app/parsers/parser_selector.py

from app.parsers.hybrid_parser import HybridParser
from app.parsers.pypdfparser import PyPdfParser
from app.parsers.OCRparser import OCRParser
from app.detectors.parser_detector import PDFDetector


class ParserSelector:

    def get_parser(self, file_path: str):

        info = PDFDetector.detect(file_path)

        # scanned → full OCR
        if info["type"] == "scanned":
            return OCRParser()

        # digital but has images → hybrid
        if info["has_images"]:
            return HybridParser()

        # default
        return PyPdfParser()
