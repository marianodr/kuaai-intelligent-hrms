from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import agent_service

router = APIRouter()


class ChatRequest(BaseModel):
    question: str
    user_id: int
    thread_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    thread_id: str


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """
    Endpoint principal del agente RAG.
    Recibe pregunta del usuario, invoca el agente LangChain y retorna respuesta.
    """
    thread_id = req.thread_id or f"user-{req.user_id}"
    try:
        answer = agent_service.chat(req.question, req.user_id, thread_id)
        return ChatResponse(answer=answer, thread_id=thread_id)
    except Exception as e:
        err_str = str(e)
        if "rate_limit_exceeded" in err_str or "Rate limit" in err_str:
            raise HTTPException(
                status_code=429,
                detail="Límite de solicitudes alcanzado. Esperá unos segundos e intentá de nuevo.",
            )
        raise HTTPException(status_code=500, detail=f"Error del agente: {err_str}")


@router.get("/history/{user_id}")
def get_history(user_id: int, limit: int = 50):
    """Retorna el historial de conversación de un usuario desde la DB."""
    return agent_service.get_history(user_id, limit)
