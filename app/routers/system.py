from fastapi import APIRouter
import time

from ..background_tasks import background_task_manager
from ..session_manager import session_manager
from ..schemas import HealthResponse, PingSystemStatusResponse

router = APIRouter(prefix="/api/system", tags=["system"])

@router.get("/ping-status",
    response_model=PingSystemStatusResponse,
    summary="Ping 시스템 상태 조회",
    description="""
    전체 ping/pong 시스템의 상태를 조회합니다.
    
    반환 정보:
    - 백그라운드 태스크 실행 상태
    - ping이 필요한 세션 수
    - 전체 활성 세션 수
    - ping 간격 및 타임아웃 설정
    """
)
async def get_ping_system_status():
    status = background_task_manager.get_status()
    return PingSystemStatusResponse(
        background_tasks=status,
        sessions_needing_ping=len(session_manager.get_sessions_needing_ping()),
        active_sessions=session_manager.get_active_sessions_count()
    )

@router.get("/health",
    response_model=HealthResponse,
    summary="시스템 헬스 체크",
    description="서버의 기본적인 상태를 확인합니다. 정상 동작 시 'healthy' 상태를 반환합니다."
)
async def health_check():
    return HealthResponse(status="healthy", timestamp=time.time())