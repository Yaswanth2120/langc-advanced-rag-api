from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_documents, routes_health, routes_query
from app.core.config import settings


app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_health.router)
app.include_router(routes_query.router)
app.include_router(routes_documents.router)
