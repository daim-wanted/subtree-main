from fastapi import APIRouter
import time

from ..session_manager import session_manager
from ..schemas import ActiveSessionsResponse

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

@router.get("/active",
    response_model=ActiveSessionsResponse,
    summary="활성 세션 수 조회",
    description="현재 서버에 연결된 활성 세션의 총 개수를 반환합니다."
)
async def get_active_sessions():
    return ActiveSessionsResponse(
        active_sessions_count=session_manager.get_active_sessions_count(),
        timestamp=time.time()
    )