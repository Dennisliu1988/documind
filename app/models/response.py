# 响应体结构
# app/models/response.py

from pydantic import BaseModel

class ChatResponse(BaseModel):
    answer: str
    sources: list[str]

class UploadResponse(BaseModel):
    message: str
    chunks_count: int