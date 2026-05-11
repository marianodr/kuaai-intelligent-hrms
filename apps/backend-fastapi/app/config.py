from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # PostgreSQL
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "kuaai"
    postgres_user: str = "kuaai_user"
    postgres_password: str = "kuaai_password"

    # MinIO
    minio_endpoint: str = "minio"
    minio_port: int = 9000
    minio_access_key: str = "kuaai_access"
    minio_secret_key: str = "kuaai_secret"
    minio_bucket_documents: str = "documents"

    # Groq
    groq_api_key: str
    groq_model: str = "llama-3.1-8b-instant"

    # SentenceTransformers
    embeddings_model: str = "all-MiniLM-L6-v2"
    embeddings_dimensions: int = 384

    # FastAPI
    fastapi_port: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
