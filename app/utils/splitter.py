# 文本切分工具
# app/utils/splitter.py
def split_text(
    text: str, 
    source: str, 
    page: int = 1, 
    chunk_size: int = 500, 
    overlap: int = 50
) -> list[dict]:
    """按固定长度切分文本，相邻块保留 overlap 个字符的重叠。"""
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap 必须大于等于 0 且小于 chunk_size")

    chunks = []
    start = 0
    index = 0
    # 注意：返回的是 list[dict]（字典列表），不是 list[str]（字符串列表）
    while start < len(text):
        end = start + chunk_size
        chunks.append(
            {
            "text": text[start:end],
            "metadata": {
                "source": source,
                "page": page,
                "chunk_index": index,
            },
        })
        if end >= len(text):
            break
        start = end - overlap
        index += 1    
    return chunks