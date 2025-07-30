from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import asyncio
import json
import time
from typing import AsyncGenerator

from ..dependencies import DatabaseDep
from ..session_manager import session_manager

router = APIRouter(tags=["stream"])

@router.get("/stream",
    summary="Server-Sent Events 스트림",
    description="""
    Server-Sent Events (SSE) 스트림을 제공합니다.
    
    - 2초마다 새로운 메시지를 전송합니다.
    - 브라우저에서 EventSource로 연결할 수 있습니다.
    - 실시간 데이터 스트리밍에 사용됩니다.
    
    **사용 예시:**
    ```javascript
    const eventSource = new EventSource('/stream');
    eventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);
        console.log(data);
    };
    ```
    """,
    responses={
        200: {
            "description": "SSE 스트림",
            "content": {
                "text/event-stream": {
                    "example": 'data: {"timestamp": 1640995200.0, "counter": 1, "message": "Server message #1"}\\n\\n'
                }
            }
        }
    }
)
async def stream_events():
    async def event_generator() -> AsyncGenerator[str, None]:
        counter = 0
        while True:
            data = {
                "timestamp": time.time(),
                "counter": counter,
                "message": f"Server message #{counter}"
            }
            
            yield f"data: {json.dumps(data)}\n\n"
            counter += 1
            await asyncio.sleep(2)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )

@router.get("/stream/{session_id}",
    summary="세션별 Server-Sent Events 스트림",
    description="""
    특정 세션을 위한 개별화된 Server-Sent Events 스트림을 제공합니다.
    
    - 세션별로 고유한 메시지를 전송합니다.
    - 세션의 활동 상태를 실시간으로 업데이트합니다.
    - ping/pong 상태도 스트림에 포함됩니다.
    - 세션이 존재하지 않으면 404 에러를 반환합니다.
    
    **사용 예시:**
    ```javascript
    const eventSource = new EventSource('/stream/your-session-id');
    eventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);
        console.log('Session message:', data);
    };
    ```
    """,
    responses={
        200: {
            "description": "세션별 SSE 스트림",
            "content": {
                "text/event-stream": {
                    "example": 'data: {"timestamp": 1640995200.0, "session_id": "abc123", "username": "john", "counter": 1, "message": "Message #1 for john", "ping_status": "ok"}\\n\\n'
                }
            }
        },
        404: {
            "description": "세션을 찾을 수 없음"
        }
    }
)
async def stream_session_events(session_id: str, db: DatabaseDep):
    # 세션 존재 여부 확인
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    async def session_event_generator() -> AsyncGenerator[str, None]:
        try:
            while True:
                # 세션이 여전히 존재하는지 확인
                current_session = await session_manager.get_session(session_id)
                if not current_session:
                    # 세션이 종료되었음을 알리고 스트림 종료
                    disconnect_data = {
                        "type": "session_disconnected",
                        "timestamp": time.time(),
                        "session_id": session_id,
                        "message": "Session has been disconnected"
                    }
                    yield f"data: {json.dumps(disconnect_data)}\n\n"
                    break
                
                # 세션 활동 업데이트
                await session_manager.update_session_activity(db, session_id)
                
                # 다음 메시지 카운터 가져오기
                counter = await session_manager.get_next_message_counter(session_id)
                
                # 세션별 메시지 생성
                message_content = f"Stream message #{counter} for {current_session.get('username', 'Anonymous')}"
                
                # 메시지를 데이터베이스에 저장
                await session_manager.save_message(db, session_id, message_content, counter)
                
                # ping 상태 확인
                ping_status = "pending" if current_session.get("ping_pending", False) else "ok"
                
                # 스트림 데이터 생성
                stream_data = {
                    "type": "message",
                    "timestamp": time.time(),
                    "session_id": session_id,
                    "username": current_session.get("username", "Anonymous"),
                    "counter": counter,
                    "message": message_content,
                    "ping_status": ping_status,
                    "ping_miss_count": current_session.get("ping_miss_count", 0)
                }
                
                yield f"data: {json.dumps(stream_data)}\n\n"
                
                # ping이 pending 상태이면 ping 이벤트도 전송
                if current_session.get("ping_pending", False):
                    ping_data = {
                        "type": "ping_required",
                        "timestamp": time.time(),
                        "session_id": session_id,
                        "message": "Server is requesting pong response"
                    }
                    yield f"data: {json.dumps(ping_data)}\n\n"
                
                await asyncio.sleep(2)
                
        except Exception as e:
            # 에러 발생 시 클라이언트에게 알림
            error_data = {
                "type": "error",
                "timestamp": time.time(),
                "session_id": session_id,
                "message": f"Stream error: {str(e)}"
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        session_event_generator(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )