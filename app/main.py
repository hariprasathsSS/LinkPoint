from fastapi import FastAPI
from app.routes.v1.ingest import router
from app.routes.v1.query import qrouter
from app.routes.v1.chunk import chunk_router

app = FastAPI()
app.include_router(router)
app.include_router(qrouter)
app.include_router(chunk_router)
