import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import database

logger = logging.getLogger(__name__)
router = APIRouter()


class CreateThreadRequest(BaseModel):
    user_id: int
    name: str = "Nueva conversación"


class RenameThreadRequest(BaseModel):
    name: str


@router.post("/")
def create_thread(req: CreateThreadRequest):
    with database.get_cursor() as (cur, conn):
        cur.execute(
            """INSERT INTO conversation_threads (user_id, name)
               VALUES (%s, %s)
               RETURNING id, user_id, name, created_at, last_message_at""",
            (req.user_id, req.name),
        )
        row = cur.fetchone()
        conn.commit()
    return dict(row)


@router.get("/{user_id}")
def list_threads(user_id: int):
    with database.get_cursor() as (cur, conn):
        cur.execute(
            """SELECT id, name, created_at, last_message_at
               FROM conversation_threads
               WHERE user_id = %s
               ORDER BY last_message_at DESC""",
            (user_id,),
        )
        rows = cur.fetchall()
    return [dict(r) for r in rows]


@router.patch("/{thread_id}/rename")
def rename_thread(thread_id: str, req: RenameThreadRequest):
    with database.get_cursor() as (cur, conn):
        cur.execute(
            "UPDATE conversation_threads SET name = %s WHERE id = %s RETURNING id, name",
            (req.name, thread_id),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Hilo no encontrado")
        conn.commit()
    return dict(row)


@router.delete("/{thread_id}")
def delete_thread(thread_id: str):
    with database.get_cursor(dict_cursor=False) as (cur, conn):
        cur.execute(
            "DELETE FROM conversation_threads WHERE id = %s",
            (thread_id,),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Hilo no encontrado")
        conn.commit()
    return {"message": "Hilo eliminado"}
