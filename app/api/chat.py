# 对话接口（流式/非流式）
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models.request import ChatRequest
from app.services.rag_service import RAGService

router = APIRouter()

@router.post("/chat")
async def chat(req: ChatRequest):
    """接收用户问题，流式返回 RAG 结果"""
    
    async def event_generator():
        try:
            # 调用我们写好的 RAG 核心服务，逐字产出
            async for chunk in RAGService.query_stream(req.question):
                yield f"data: {chunk}\n\n"
        except Exception as e:
            yield f"data: [错误] {str(e)}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )