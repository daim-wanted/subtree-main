import uuid
from typing import Optional, Dict
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from .models import UserSession, UserMessage, User
import asyncio

class SessionManager:
    def __init__(self):
        self.active_sessions: Dict[str, dict] = {}
        self.ping_timeout = 45  # 45초 후 세션 만료
        self.ping_interval = 20  # 20초마다 ping 전송

    async def create_session(self, db: AsyncSession, username: Optional[str] = None) -> str:
        """새로운 세션을 생성합니다."""
        session_id = str(uuid.uuid4())
        
        # 유저 이름이 제공된 경우 유저를 찾거나 생성
        user_id = None
        if username:
            user = await self.get_or_create_user(db, username)
            user_id = user.id
        
        # 데이터베이스에 세션 저장
        db_session = UserSession(
            session_id=session_id,
            user_id=user_id,
            is_connected=True
        )
        db.add(db_session)
        await db.commit()
        
        # 메모리에 세션 정보 저장
        self.active_sessions[session_id] = {
            "user_id": user_id,
            "username": username,
            "message_counter": 0,
            "connected_at": datetime.now(),
            "last_activity": datetime.now(),
            "last_ping": datetime.now(),
            "ping_pending": False,
            "ping_miss_count": 0
        }
        
        return session_id

    async def get_or_create_user(self, db: AsyncSession, username: str) -> User:
        """유저를 찾거나 새로 생성합니다."""
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                username=username,
                email=f"{username}@example.com",
                is_active=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        
        return user

    async def get_session(self, session_id: str) -> Optional[dict]:
        """세션 정보를 반환합니다."""
        return self.active_sessions.get(session_id)

    async def update_session_activity(self, db: AsyncSession, session_id: str):
        """세션 활동 시간을 업데이트합니다."""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["last_activity"] = datetime.now()
            
            # 데이터베이스 업데이트
            await db.execute(
                update(UserSession)
                .where(UserSession.session_id == session_id)
                .values(last_activity=datetime.now())
            )
            await db.commit()

    async def disconnect_session(self, db: AsyncSession, session_id: str):
        """세션을 종료합니다."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            
            # 데이터베이스 업데이트
            await db.execute(
                update(UserSession)
                .where(UserSession.session_id == session_id)
                .values(is_connected=False)
            )
            await db.commit()

    async def get_next_message_counter(self, session_id: str) -> int:
        """세션의 다음 메시지 카운터를 반환합니다."""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["message_counter"] += 1
            return self.active_sessions[session_id]["message_counter"]
        return 1

    async def save_message(self, db: AsyncSession, session_id: str, message_content: str, counter: int):
        """메시지를 데이터베이스에 저장합니다."""
        user_message = UserMessage(
            session_id=session_id,
            message_counter=counter,
            message_content=message_content
        )
        db.add(user_message)
        await db.commit()

    def get_active_sessions_count(self) -> int:
        """현재 활성 세션 수를 반환합니다."""
        return len(self.active_sessions)

    def get_session_info(self, session_id: str) -> Optional[dict]:
        """세션의 상세 정보를 반환합니다."""
        session = self.active_sessions.get(session_id)
        if session:
            return {
                "session_id": session_id,
                "username": session.get("username", "Anonymous"),
                "message_counter": session["message_counter"],
                "connected_at": session["connected_at"].isoformat(),
                "last_activity": session["last_activity"].isoformat(),
                "last_ping": session["last_ping"].isoformat(),
                "ping_pending": session["ping_pending"],
                "ping_miss_count": session["ping_miss_count"]
            }
        return None

    async def send_ping(self, session_id: str) -> bool:
        """세션에 ping을 전송합니다."""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session["last_ping"] = datetime.now()
            session["ping_pending"] = True
            return True
        return False

    async def handle_pong(self, session_id: str) -> bool:
        """클라이언트로부터 pong 응답을 처리합니다."""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session["ping_pending"] = False
            session["ping_miss_count"] = 0
            session["last_activity"] = datetime.now()
            return True
        return False

    async def check_inactive_sessions(self, db: AsyncSession) -> list:
        """비활성 세션들을 확인하고 정리합니다."""
        now = datetime.now()
        inactive_sessions = []
        sessions_to_remove = []

        for session_id, session in self.active_sessions.items():
            # ping이 pending 상태이고 timeout을 초과한 경우
            if session["ping_pending"]:
                time_since_ping = (now - session["last_ping"]).total_seconds()
                if time_since_ping > self.ping_timeout:
                    session["ping_miss_count"] += 1
                    
                    # 3번 연속 ping을 놓친 경우 세션 제거
                    if session["ping_miss_count"] >= 3:
                        sessions_to_remove.append(session_id)
                        inactive_sessions.append({
                            "session_id": session_id,
                            "username": session.get("username", "Anonymous"),
                            "reason": "ping_timeout"
                        })
                    else:
                        # ping을 다시 전송
                        session["ping_pending"] = False

            # 일반적인 비활성 체크 (ping 없이도)
            time_since_activity = (now - session["last_activity"]).total_seconds()
            if time_since_activity > (self.ping_timeout * 2):  # ping timeout의 2배
                sessions_to_remove.append(session_id)
                inactive_sessions.append({
                    "session_id": session_id,
                    "username": session.get("username", "Anonymous"),
                    "reason": "inactivity"
                })

        # 비활성 세션들 제거
        for session_id in sessions_to_remove:
            await self.disconnect_session(db, session_id)

        return inactive_sessions

    def get_sessions_needing_ping(self) -> list:
        """ping이 필요한 세션들의 목록을 반환합니다."""
        now = datetime.now()
        sessions_needing_ping = []

        for session_id, session in self.active_sessions.items():
            # ping이 pending이 아니고, 마지막 ping으로부터 interval이 지난 경우
            if not session["ping_pending"]:
                time_since_ping = (now - session["last_ping"]).total_seconds()
                if time_since_ping >= self.ping_interval:
                    sessions_needing_ping.append({
                        "session_id": session_id,
                        "username": session.get("username", "Anonymous")
                    })

        return sessions_needing_ping

# 전역 세션 매니저 인스턴스
session_manager = SessionManager()