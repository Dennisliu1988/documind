# 文档上传/管理接口
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.document_service import DocumentService
from app.services.vector_service import vector_service

router = APIRouter()

class IngestRequest(BaseModel):
    file_path: str

@router.post("/ingest")
async def ingest_document(req: IngestRequest):
    """解析本地 PDF 并入库"""
    try:
        # 1. 解析
        chunks = DocumentService.parse_pdf(req.file_path)
        if not chunks:
            raise HTTPException(status_code=400, detail="文档为空或解析失败")
            
        # 2. 入库
        vector_service.add_documents(chunks)
        
        return {"message": "文档成功入库", "chunks_count": len(chunks)}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="文件不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))