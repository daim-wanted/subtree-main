import asyncio
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from .database import AsyncSessionLocal
from .session_manager import session_manager

logger = logging.getLogger(__name__)

class BackgroundTaskManager:
    def __init__(self):
        self.running = False
        self.ping_task = None
        self.cleanup_task = None

    async def start_ping_checker(self):
        """ping 체크 백그라운드 태스크를 시작합니다."""
        if self.running:
            return
        
        self.running = True
        self.ping_task = asyncio.create_task(self._ping_checker_loop())
        self.cleanup_task = asyncio.create_task(self._cleanup_checker_loop())
        logger.info("Background ping checker started")

    async def stop_ping_checker(self):
        """ping 체크 백그라운드 태스크를 중지합니다."""
        self.running = False
        
        if self.ping_task:
            self.ping_task.cancel()
            try:
                await self.ping_task
            except asyncio.CancelledError:
                pass
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Background ping checker stopped")

    async def _ping_checker_loop(self):
        """주기적으로 세션들에 ping을 전송하는 루프입니다."""
        while self.running:
            try:
                # ping이 필요한 세션들 확인
                sessions_needing_ping = session_manager.get_sessions_needing_ping()
                
                if sessions_needing_ping:
                    logger.info(f"Sending ping to {len(sessions_needing_ping)} sessions")
                    
                    for session_info in sessions_needing_ping:
                        session_id = session_info["session_id"]
                        username = session_info["username"]
                        
                        # ping 전송
                        await session_manager.send_ping(session_id)
                        logger.debug(f"Ping sent to session {session_id[:8]}... (user: {username})")
                
                # 20초마다 체크 (ping_interval과 동일)
                await asyncio.sleep(session_manager.ping_interval)
                
            except Exception as e:
                logger.error(f"Error in ping checker loop: {e}")
                await asyncio.sleep(5)  # 에러 발생 시 5초 후 재시도

    async def _cleanup_checker_loop(self):
        """주기적으로 비활성 세션들을 정리하는 루프입니다."""
        while self.running:
            try:
                async with AsyncSessionLocal() as db:
                    # 비활성 세션들 확인 및 정리
                    inactive_sessions = await session_manager.check_inactive_sessions(db)
                    
                    if inactive_sessions:
                        logger.info(f"Cleaned up {len(inactive_sessions)} inactive sessions")
                        
                        for session_info in inactive_sessions:
                            session_id = session_info["session_id"]
                            username = session_info["username"]
                            reason = session_info["reason"]
                            logger.info(f"Session {session_id[:8]}... (user: {username}) removed due to {reason}")
                
                # 30초마다 정리 작업 수행
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in cleanup checker loop: {e}")
                await asyncio.sleep(10)  # 에러 발생 시 10초 후 재시도

    def get_status(self) -> dict:
        """백그라운드 태스크 상태를 반환합니다."""
        return {
            "running": self.running,
            "ping_task_active": self.ping_task and not self.ping_task.done(),
            "cleanup_task_active": self.cleanup_task and not self.cleanup_task.done(),
            "ping_interval": session_manager.ping_interval,
            "ping_timeout": session_manager.ping_timeout,
            "timestamp": datetime.now().isoformat()
        }

# 전역 백그라운드 태스크 매니저 인스턴스
background_task_manager = BackgroundTaskManager()