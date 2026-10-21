# 请求体结构
# app/models/request.py

from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    question: str = Field(..., description="用户的提问", min_length=1)
    history: list[dict] = Field(default=[], description="历史对话（用于多轮）")

class DocumentUploadRequest(BaseModel):
    # 为了简化，我们先用 JSON 传文本内容。后面再做真实的文件上传。
    file_name: str
    content: str