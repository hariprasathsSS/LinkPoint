from fastapi import FastAPI
from app.routes.v1.ingest import router
from app.routes.v1.query import qrouter

app = FastAPI()
app.include_router(router)
app.include_router(qrouter)
