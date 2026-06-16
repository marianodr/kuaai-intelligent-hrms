from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logging_config import setup_logging
from app import database, minio_client, embeddings as emb_service
from app.services.agent_service import init_agent
from app.routers import documents, agent, threads

setup_logging(settings.log_level, settings.log_file)


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_pool(settings)
    minio_client.init_client(settings)
    emb_service.init_model(settings.embeddings_model)
    init_agent(settings)
    yield
    database.close_pool()


app = FastAPI(title="Kuaai AI Backend", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(agent.router, prefix="/agent", tags=["agent"])
app.include_router(threads.router, prefix="/threads", tags=["threads"])


@app.get("/health")
def health():
    return {"status": "ok"}
