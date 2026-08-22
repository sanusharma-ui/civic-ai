from fastapi import APIRouter

from app.api.routes import agents, chat, conversations


api_router = APIRouter()
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(
    conversations.router,
    prefix="/conversations",
    tags=["conversations"],
)
