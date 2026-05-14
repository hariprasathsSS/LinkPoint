from app.model.parse_model import ParseModel
from typing import Any
from pathlib import Path
from app.universal_parser.noice_handler import NoiseFilter
from app.universal_parser.normalization import NormalizationLayer
from app.universal_parser.OCR_parser import OCRLayer
from app.universal_parser.table_enhancer import TableEnhancer
from app.universal_parser.unstructured import UnstructuredParser

class PDFParserService:
    """
    Primary orchestrator that runs all five pipeline steps in order.

    Each step is encapsulated in its own class and called through a
    dedicated method on this service, keeping the pipeline transparent
    and individually testable.

    Usage:
        service = PDFParserService()
        results = service.parse("report.pdf")
        for item in results:
            print(item["type"], "→", item["text"][:80])

    Customisation:
        Pass pre-configured step instances to override defaults:

        service = PDFParserService(
            unstructured_parser=UnstructuredParser(strategy="hi_res"),
            table_enhancer=TableEnhancer(flavor="stream"),
            ocr_layer=OCRLayer(lang="tam+eng"),
            noise_filter=NoiseFilter(repeat_threshold=2),
        )
    """

    def __init__(
        self,
        unstructured_parser: UnstructuredParser | None = None,
        table_enhancer:      TableEnhancer      | None = None,
        ocr_layer:           OCRLayer           | None = None,
        noise_filter:        NoiseFilter        | None = None,
        normalization_layer: NormalizationLayer | None = None,
    ) -> None:
        self.unstructured_parser = unstructured_parser or UnstructuredParser()
        self.table_enhancer      = table_enhancer      or TableEnhancer()
        self.ocr_layer           = ocr_layer           or OCRLayer()
        self.noise_filter        = noise_filter        or NoiseFilter()
        self.normalization_layer = normalization_layer or NormalizationLayer()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, pdf_path: str) -> list[dict[str, Any]]:
        """
        Full pipeline: PDF → LLM-ready structured elements.

        Steps executed in order:
            1. _run_unstructured_parser  → semantic element extraction
            2. _run_table_enhancer       → Camelot table rows
            3. _run_ocr_layer            → image/diagram text
            4. _run_noise_filter         → remove headers, footers, blanks
            5. _run_normalization_layer  → unified schema

        Args:
            pdf_path: Absolute or relative path to the PDF file.

        Returns:
            List of dicts with keys: "type", "text", "metadata".
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        logger.info("=== PDFParserService: starting pipeline for %s ===", path.name)

        elements = self._run_unstructured_parser(str(path))
        elements = self._run_table_enhancer(elements, str(path))
        elements = self._run_ocr_layer(elements, str(path))
        elements = self._run_noise_filter(elements)
        result   = self._run_normalization_layer(elements)

        logger.info(
            "=== PDFParserService: done — %d elements returned ===", len(result)
        )
        return result

    # ------------------------------------------------------------------
    # Step dispatchers (one method per class, thin wrappers)
    # ------------------------------------------------------------------

    def _run_unstructured_parser(self, pdf_path: str) -> list[ParseModel]:
        """Step 1 — delegates to UnstructuredParser.parse()."""
        return self.unstructured_parser.parse(pdf_path)

    def _run_table_enhancer(
        self,
        elements: list[ParseModel],
        pdf_path: str,
    ) -> list[ParseModel]:
        """Step 2 — delegates to TableEnhancer.enhance()."""
        return self.table_enhancer.enhance(elements, pdf_path)

    def _run_ocr_layer(
        self,
        elements: list[ParseModel],
        pdf_path: str,
    ) -> list[ParseModel]:
        """Step 3 — delegates to OCRLayer.process()."""
        return self.ocr_layer.process(elements, pdf_path)

    def _run_noise_filter(
        self,
        elements: list[ParseModel],
    ) -> list[ParseModel]:
        """Step 4 — delegates to NoiseFilter.filter()."""
        return self.noise_filter.filter(elements)

    def _run_normalization_layer(
        self,
        elements: list[ParseModel],
    ) -> list[dict[str, Any]]:
        """Step 5 — delegates to NormalizationLayer.normalize()."""
        return self.normalization_layer.normalize(elements)
