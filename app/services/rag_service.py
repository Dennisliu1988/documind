# RAG 核心管线（混合检索 + Rerank + 大模型生成）# app/services/rag_service.py
import json

from app.services.llm_service import chat_stream, chat_sync
from app.services.vector_service import vector_service


class RAGService:
    @staticmethod
    async def rewrite_query(question: str) -> list[str]:
        """查询改写"""
        prompt = f"""你是一个检索查询优化专家。请将用户的原始问题改写为 1-3 个更适合检索的问题。
只输出 JSON 数组，例如：["问题1", "问题2"]。
原始问题：{question}"""
        try:
            res = await chat_sync([{"role": "user", "content": prompt}])
            rewrites = json.loads(res)
            if isinstance(rewrites, list) and len(rewrites) > 0:
                return rewrites
        except Exception:
            pass
        return [question]  # 失败则回退到原问题

    @classmethod
    async def query_stream(cls, question: str):
        """执行完整的 RAG 流程并流式返回"""
        # 1. 改写
        rewritten_questions = await cls.rewrite_query(question)
        
        # 2. 多路召回 + 精排
        all_results = []
        for q in rewritten_questions:
            candidates = vector_service.hybrid_search(q, top_k=10)
            reranked = vector_service.rerank(q, candidates, top_n=2)  # 每个问题精排留2个
            all_results.extend(reranked)

        # 3. 去重
        unique_docs = {}
        for r in all_results:
            unique_docs[r["document"]] = r
        
        final_docs = list(unique_docs.values())[:5] # 最多取5个块给大模型

        # 4. 拼接 Context
        context = "\n\n---\n\n".join([
            f"[来源: {r['metadata'].get('source', '未知')} 第{r['metadata'].get('page', '?')}页]\n{r['document']}"
            for r in final_docs
        ])

        # 5. 组装 Prompt
        prompt = f"""你是一个专业的企业知识库助手。
请只基于以下参考文档回答用户问题，不要使用你自己的知识。

参考文档：
{context}

用户问题：
{question}

要求：
1. 回答要引用来源（文件名 + 页码）
2. 如果文档中没有相关信息，回答“文档中未提及”
"""
        messages = [{"role": "user", "content": prompt}]
        
        # 6. 流式返回
        async for chunk in chat_stream(messages):
            yield chunk