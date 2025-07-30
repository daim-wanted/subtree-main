from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")

router = APIRouter(tags=["pages"])

@router.get("/", 
    response_class=HTMLResponse,
    summary="메인 페이지",
    description="SSE 클라이언트 테스트 페이지를 제공합니다. 브라우저에서 세션 생성, 메시지 수신, ping/pong 테스트를 할 수 있습니다.",
    include_in_schema=False  # Swagger에서 HTML 페이지는 제외
)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})