# PDF/TXT 解析与切块
# app/services/document_service.py
from pathlib import Path
from pypdf import PdfReader
from app.utils.splitter import split_text

class DocumentService:
    @staticmethod
    def parse_pdf(file_path: str) -> list[dict]:
        """解析 PDF，返回按页切分后的 chunk 列表"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
            
        chunks = []
        with path.open("rb") as f:
            reader = PdfReader(f)
            for page_num, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                if not text.strip():
                    continue
                page_chunks = split_text(
                    text=text,
                    source=path.name,
                    page=page_num
                )
                chunks.extend(page_chunks)
        return chunks

    @staticmethod
    def parse_txt(file_path: str) -> list[dict]:
        """解析 TXT 文件"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        text = path.read_text(encoding="utf-8")
        return split_text(text=text, source=path.name)