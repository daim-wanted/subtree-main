from fastapi import APIRouter, Form, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import time
from typing import Optional

from ..dependencies import DatabaseDep, get_session_or_404, validate_session_exists
from ..session_manager import session_manager
from ..schemas import (
    SessionCreateResponse, SessionMessageResponse, SessionInfoResponse,
    PingStatusResponse, PongResponse, DisconnectResponse, ErrorResponse
)

router = APIRouter(prefix="/api/session", tags=["session"])

@router.post("/create", 
    response_model=SessionCreateResponse,
    responses={
        200: {"description": "세션이 성공적으로 생성됨"},
        500: {"model": ErrorResponse, "description": "서버 내부 오류"}
    },
    summary="새 세션 생성",
    description="""
    새로운 사용자 세션을 생성합니다.
    
    - **username**: 선택사항. 제공하지 않으면 'Anonymous'로 설정됩니다.
    - 각 세션은 고유한 UUID를 받습니다.
    - 세션별로 독립적인 메시지 카운터가 관리됩니다.
    """
)
async def create_session(db: DatabaseDep, username: Optional[str] = Form(None)):
    session_id = await session_manager.create_session(db, username)
    return SessionCreateResponse(
        session_id=session_id,
        username=username or "Anonymous",
        message="Session created successfully"
    )

@router.get("/{session_id}/message",
    response_model=SessionMessageResponse,
    responses={
        200: {"description": "메시지가 성공적으로 생성됨"},
        404: {"model": ErrorResponse, "description": "세션을 찾을 수 없음"}
    },
    summary="세션 메시지 가져오기",
    description="""
    특정 세션의 새로운 메시지를 생성하고 반환합니다.
    
    - 메시지를 요청할 때마다 카운터가 증가합니다.
    - 세션의 마지막 활동 시간이 업데이트됩니다.
    - 모든 메시지는 데이터베이스에 저장됩니다.
    """
)
async def get_user_message(session_id: str, db: DatabaseDep):
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 세션 활동 업데이트
    await session_manager.update_session_activity(db, session_id)
    
    # 다음 메시지 카운터 가져오기
    counter = await session_manager.get_next_message_counter(session_id)
    
    message_content = f"Message #{counter} for {session.get('username', 'Anonymous')}"
    
    # 메시지를 데이터베이스에 저장
    await session_manager.save_message(db, session_id, message_content, counter)
    
    return SessionMessageResponse(
        timestamp=time.time(),
        session_id=session_id,
        username=session.get("username", "Anonymous"),
        counter=counter,
        message=message_content
    )

@router.delete("/{session_id}",
    response_model=DisconnectResponse,
    responses={
        200: {"description": "세션이 성공적으로 종료됨"},
        404: {"model": ErrorResponse, "description": "세션을 찾을 수 없음"}
    },
    summary="세션 종료",
    description="지정된 세션을 종료하고 관련 리소스를 정리합니다."
)
async def disconnect_session(session_id: str, db: DatabaseDep):
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    await session_manager.disconnect_session(db, session_id)
    return DisconnectResponse(message="Session disconnected successfully")

@router.get("/{session_id}/info",
    response_model=SessionInfoResponse,
    responses={
        200: {"description": "세션 정보 조회 성공"},
        404: {"model": ErrorResponse, "description": "세션을 찾을 수 없음"}
    },
    summary="세션 정보 조회",
    description="""
    세션의 상세 정보를 조회합니다.
    
    반환되는 정보:
    - 세션 ID 및 사용자명
    - 메시지 카운터
    - 연결 시간 및 마지막 활동 시간
    - Ping 관련 상태 정보
    """
)
async def get_session_info(session_id: str):
    session_info = session_manager.get_session_info(session_id)
    if not session_info:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionInfoResponse(**session_info)

@router.get("/{session_id}/ping",
    response_model=PingStatusResponse,
    responses={
        200: {"description": "Ping 상태 조회 성공"},
        404: {"model": ErrorResponse, "description": "세션을 찾을 수 없음"}
    },
    summary="Ping 상태 확인",
    description="""
    세션의 ping/pong 상태를 확인합니다.
    
    - **requires_pong**: true인 경우 클라이언트는 pong 응답을 보내야 합니다.
    - **ping_miss_count**: 놓친 ping 횟수 (3회 연속 놓치면 세션 종료)
    """
)
async def check_ping_status(session_id: str):
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return PingStatusResponse(
        session_id=session_id,
        ping_pending=session.get("ping_pending", False),
        last_ping=session.get("last_ping").isoformat() if session.get("last_ping") else None,
        ping_miss_count=session.get("ping_miss_count", 0),
        requires_pong=session.get("ping_pending", False)
    )

@router.post("/{session_id}/pong",
    response_model=PongResponse,
    responses={
        200: {"description": "Pong 응답이 성공적으로 처리됨"},
        404: {"model": ErrorResponse, "description": "세션을 찾을 수 없음"}
    },
    summary="Pong 응답 전송",
    description="""
    서버의 ping에 대한 pong 응답을 보냅니다.
    
    - 클라이언트가 살아있음을 서버에 알립니다.
    - ping_miss_count가 리셋됩니다.
    - 세션의 마지막 활동 시간이 업데이트됩니다.
    """
)
async def handle_pong_response(session_id: str, db: DatabaseDep):
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    success = await session_manager.handle_pong(session_id)
    
    # 활동 시간도 업데이트
    await session_manager.update_session_activity(db, session_id)
    
    return PongResponse(
        message="Pong received successfully",
        session_id=session_id,
        timestamp=time.time()
    )