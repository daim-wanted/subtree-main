from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from ..dependencies import DatabaseDep
from ..models import User, Event
from ..schemas import UserResponse, EventResponse

router = APIRouter(prefix="/api", tags=["users"])

@router.get("/users",
    response_model=List[UserResponse],
    summary="전체 사용자 목록 조회",
    description="데이터베이스에 등록된 모든 사용자의 목록을 반환합니다."
)
async def get_users(db: DatabaseDep):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [UserResponse(id=user.id, username=user.username, email=user.email) for user in users]

@router.get("/events",
    response_model=List[EventResponse],
    summary="전체 이벤트 목록 조회", 
    description="데이터베이스에 저장된 모든 이벤트의 목록을 반환합니다."
)
async def get_events(db: DatabaseDep):
    result = await db.execute(select(Event))
    events = result.scalars().all()
    return [EventResponse(id=event.id, title=event.title, content=event.content) for event in events]