from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.database import init_db
from app.background_tasks import background_task_manager
from app.routers import session, sessions, system, users, pages, stream

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await background_task_manager.start_ping_checker()
    yield
    await background_task_manager.stop_ping_checker()

app = FastAPI(
    title="SSE Server with Session Management",
    version="1.0.0",
    description="""
    ## SSE (Server-Sent Events) 서버 with 세션 관리

    이 API는 다음 기능들을 제공합니다:

    ### 📱 세션 관리
    * 유저별 세션 생성 및 관리
    * 세션별 메시지 카운터 추적
    * 자동 세션 정리

    ### 🏓 Ping/Pong 시스템
    * 클라이언트 생존 확인
    * 자동 비활성 세션 제거
    * 백그라운드 모니터링

    ### 📊 실시간 데이터
    * Server-Sent Events 스트림
    * 실시간 메시지 전송
    * 세션별 개별 메시지

    ### 🔧 시스템 모니터링
    * 헬스 체크
    * 활성 세션 현황
    * 시스템 상태 조회
    """,
    lifespan=lifespan,
    contact={
        "name": "API Support",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "session",
            "description": "개별 세션 관리 API - 세션 생성, 메시지 처리, ping/pong"
        },
        {
            "name": "sessions", 
            "description": "세션 목록 및 통계 API"
        },
        {
            "name": "system",
            "description": "시스템 상태 및 헬스 체크 API"
        },
        {
            "name": "users",
            "description": "유저 및 이벤트 데이터 API"
        },
        {
            "name": "stream",
            "description": "Server-Sent Events 스트림 API"
        },
        {
            "name": "pages",
            "description": "웹 페이지 및 UI"
        }
    ]
)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(pages.router)
app.include_router(stream.router)
app.include_router(session.router)
app.include_router(sessions.router)
app.include_router(system.router)
app.include_router(users.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)