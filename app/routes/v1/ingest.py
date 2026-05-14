from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
import logging
import traceback
# Import your schemas and dependencies based on the structure we discussed
from app.schema.response import IngestResponse
from app.dependencies import get_ingestion_service
from app.service.ingestion_service import IngestionService
from app.utils.file_handler import save_upload_file

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest_pdf(
    request: Request,
    file: UploadFile = File(...),
    service: IngestionService = Depends(get_ingestion_service)
):

    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        file_path = save_upload_file(file)
        result = service.ingest(file_path)

        return result

    except Exception as e:
        traceback.print_exc()  # 🔥 THIS IS KEY
        raise HTTPException(
            status_code=500,
            detail=f"{type(e).__name__}: {str(e)}"
        )
