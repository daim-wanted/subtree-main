from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# Session related schemas
class SessionCreateRequest(BaseModel):
    username: Optional[str] = Field(None, description="사용자명 (선택사항)", example="john_doe")

class SessionCreateResponse(BaseModel):
    session_id: str = Field(..., description="생성된 세션 ID", example="550e8400-e29b-41d4-a716-446655440000")
    username: str = Field(..., description="사용자명", example="john_doe")
    message: str = Field(..., description="응답 메시지", example="Session created successfully")

class SessionMessageResponse(BaseModel):
    timestamp: float = Field(..., description="메시지 생성 시간 (Unix timestamp)", example=1640995200.0)
    session_id: str = Field(..., description="세션 ID", example="550e8400-e29b-41d4-a716-446655440000")
    username: str = Field(..., description="사용자명", example="john_doe")
    counter: int = Field(..., description="메시지 카운터", example=5)
    message: str = Field(..., description="메시지 내용", example="Message #5 for john_doe")

class SessionInfoResponse(BaseModel):
    session_id: str = Field(..., description="세션 ID")
    username: str = Field(..., description="사용자명")
    message_counter: int = Field(..., description="현재 메시지 카운터")
    connected_at: str = Field(..., description="연결 시간 (ISO format)")
    last_activity: str = Field(..., description="마지막 활동 시간 (ISO format)")
    last_ping: str = Field(..., description="마지막 ping 시간 (ISO format)")
    ping_pending: bool = Field(..., description="ping 대기 중인지 여부")
    ping_miss_count: int = Field(..., description="놓친 ping 횟수")

class PingStatusResponse(BaseModel):
    session_id: str = Field(..., description="세션 ID")
    ping_pending: bool = Field(..., description="ping 대기 중인지 여부")
    last_ping: Optional[str] = Field(None, description="마지막 ping 시간 (ISO format)")
    ping_miss_count: int = Field(..., description="놓친 ping 횟수")
    requires_pong: bool = Field(..., description="pong 응답이 필요한지 여부")

class PongResponse(BaseModel):
    message: str = Field(..., description="응답 메시지", example="Pong received successfully")
    session_id: str = Field(..., description="세션 ID")
    timestamp: float = Field(..., description="응답 시간 (Unix timestamp)")

class DisconnectResponse(BaseModel):
    message: str = Field(..., description="응답 메시지", example="Session disconnected successfully")

# System related schemas
class HealthResponse(BaseModel):
    status: str = Field(..., description="시스템 상태", example="healthy")
    timestamp: float = Field(..., description="체크 시간 (Unix timestamp)")

class ActiveSessionsResponse(BaseModel):
    active_sessions_count: int = Field(..., description="현재 활성 세션 수", example=5)
    timestamp: float = Field(..., description="조회 시간 (Unix timestamp)")

class BackgroundTaskStatus(BaseModel):
    running: bool = Field(..., description="실행 중인지 여부")
    ping_task_active: bool = Field(..., description="ping 태스크 활성 상태")
    cleanup_task_active: bool = Field(..., description="정리 태스크 활성 상태")
    ping_interval: int = Field(..., description="ping 간격 (초)")
    ping_timeout: int = Field(..., description="ping 타임아웃 (초)")
    timestamp: str = Field(..., description="상태 조회 시간 (ISO format)")

class PingSystemStatusResponse(BaseModel):
    background_tasks: BackgroundTaskStatus = Field(..., description="백그라운드 태스크 상태")
    sessions_needing_ping: int = Field(..., description="ping이 필요한 세션 수")
    active_sessions: int = Field(..., description="전체 활성 세션 수")

# User related schemas
class UserResponse(BaseModel):
    id: int = Field(..., description="유저 ID")
    username: str = Field(..., description="사용자명")
    email: str = Field(..., description="이메일")

class EventResponse(BaseModel):
    id: int = Field(..., description="이벤트 ID")
    title: str = Field(..., description="이벤트 제목")
    content: Optional[str] = Field(None, description="이벤트 내용")

# Error schemas
class ErrorResponse(BaseModel):
    detail: str = Field(..., description="에러 메시지", example="Session not found")