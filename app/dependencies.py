from fastapi import Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from .database import get_database
from .session_manager import session_manager

# 공통 의존성들
DatabaseDep = Annotated[AsyncSession, Depends(get_database)]

async def get_session_or_404(session_id: Annotated[str, Path()]) -> dict:
    """세션을 가져오고 없으면 404 에러를 발생시킵니다."""
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

async def validate_session_exists(session_id: Annotated[str, Path()]) -> str:
    """세션이 존재하는지 확인하고 session_id를 반환합니다."""
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session_id