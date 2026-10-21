# 向量数据库操作封装
# app/services/vector_service.py
import chromadb
import httpx
import numpy as np
from chromadb.utils.embedding_functions import (
    EmbeddingFunction,
    register_embedding_function,
)
from optimum.onnxruntime import ORTModelForSequenceClassification
from rank_bm25 import BM25Okapi
from transformers import AutoTokenizer

from app.core.config import settings


# 1. 定义 Embedding 类 (使用通义千问)
@register_embedding_function
class QwenEmbedding(EmbeddingFunction):
    def __call__(self, input: list[str]) -> list[list[float]]:
        embeddings = []
        headers = {"Authorization": f"Bearer {settings.EMBEDDING_API_KEY}"}
        url = f"{settings.EMBEDDING_BASE_URL}/embeddings"
        with httpx.Client(timeout=30.0) as client:
            for text in input:
                res = client.post(url, headers=headers, json={"model": settings.EMBEDDING_MODEL, "input": text})
                res.raise_for_status()
                embeddings.append(res.json()["data"][0]["embedding"])
        return embeddings

# 2. 向量与检索服务类
class VectorService:
    def __init__(self, collection_name: str = "documind"):
        self.client = chromadb.PersistentClient(path=settings.CHROMA_DB_DIR)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=QwenEmbedding()
        )
        # 延迟加载 Rerank 模型，避免每次启动都卡住
        self._reranker = None
        self._bm25 = None
        self._bm25_docs = []
        self._reranker = None
        self._tokenizer = None

    @property
    def reranker(self):
        if self._reranker is None:
            model_id = settings.RERANK_MODEL
            # 使用 ONNX 引擎加载模型，速度飞快，不依赖 PyTorch
            self._reranker = ORTModelForSequenceClassification.from_pretrained(
                model_id, export=True
            )
            self._tokenizer = AutoTokenizer.from_pretrained(model_id)
        return self._reranker

    def add_documents(self, chunks: list[dict]):
        """存入数据库并重建 BM25 索引"""
        if not chunks:
            return
        self.collection.upsert(
            documents=[c["text"] for c in chunks],
            metadatas=[c["metadata"] for c in chunks],
            ids=[f"{c['metadata']['source']}_{c['metadata']['page']}_{c['metadata']['chunk_index']}" for c in chunks]
        )
        self._rebuild_bm25()

    def _rebuild_bm25(self):
        """每次新增文档后，重建 BM25 索引"""
        all_data = self.collection.get()
        self._bm25_docs = all_data["documents"]
        if self._bm25_docs:
            tokenized_corpus = [list(doc) for doc in self._bm25_docs]
            self._bm25 = BM25Okapi(tokenized_corpus)

    def hybrid_search(self, query: str, top_k: int = 10) -> list[dict]:
        """混合检索"""
        if not self._bm25_docs:
            self._rebuild_bm25()
            if not self._bm25_docs:
                return []

        # 1. 向量检索
        vector_res = self.collection.query(query_texts=[query], n_results=top_k)
        vector_docs = vector_res["documents"][0] if vector_res["documents"] else []
        
        # 2. BM25 检索
        tokenized_query = list(query)
        bm25_scores = self._bm25.get_scores(tokenized_query)
        bm25_top_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:top_k]

        # 3. RRF 融合
        rrf_scores = {}
        for rank, doc in enumerate(vector_docs, start=1):
            rrf_scores[doc] = rrf_scores.get(doc, 0) + 1 / (60 + rank)
        for rank, idx in enumerate(bm25_top_indices, start=1):
            doc = self._bm25_docs[idx]
            rrf_scores[doc] = rrf_scores.get(doc, 0) + 1 / (60 + rank)

        # 4. 组合结果，找元数据
        text_to_meta = {}
        if vector_res["metadatas"]:
            for doc, meta in zip(vector_res["documents"][0], vector_res["metadatas"][0]):
                text_to_meta[doc] = meta

        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [{"document": doc, "metadata": text_to_meta.get(doc, {})} for doc, _ in sorted_docs]

    def rerank(self, query: str, candidates: list[dict], top_n: int = 3) -> list[dict]:
        """Cross-encoder 精排 (ONNX 版本)"""
        if not candidates:
            return []
            
        model = self.reranker
        
        # 1. 构造 (问题, 文档) 对
        pairs = [[query, c["document"]] for c in candidates]
        
        # 2. 分词并预测
        inputs = self._tokenizer(pairs, padding=True, truncation=True, return_tensors="pt")
        # 新版 optimum 会将 pt 转为 numpy
        outputs = model(**inputs)
        
        # 取出得分
        logits = outputs.logits.detach().numpy()
        # Sigmoid 归一化 (如果有多个分类，取正类)
        scores = 1 / (1 + np.exp(-logits[:, 0]))
        
        # 3. 把得分加进结果字典里
        for i, score in enumerate(scores):
            candidates[i]["rerank_score"] = float(score)
            
        # 4. 按新得分重新排序，取 Top-K
        sorted_candidates = sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)
        return sorted_candidates[:top_n]

# 全局单例
vector_service = VectorService()