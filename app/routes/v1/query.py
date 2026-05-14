# app/routes/v1/query.py
from fastapi import APIRouter, Depends
from app.model.query_model import QueryRequest,QueryResponse
from app.dependencies import get_query_service

qrouter = APIRouter()


@qrouter.post("/query", response_model=QueryResponse)
def query(
    request: QueryRequest,
    service = Depends(get_query_service)
):
    return service.ask(request)
