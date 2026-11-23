#!/usr/bin/env python3
"""W3 第 1 步：切块。

RAG 的第一步永远是切块（chunking）。模型一次能读的字有限，
而你的资料可能是一本 300 页的 PDF——必须先切成小块，检索时只把最相关的几块塞进 prompt。

切块有三个必须自己想明白的取舍：
  1. 块太小 → 语义被切碎，检索到半句话，模型答不准
  2. 块太大 → 一块里混进多个主题，检索到"沾边"的噪声，还白烧 token
  3. 块之间不重叠 → 关键句子正好被切断，两边的块各拿到半句，谁都答不出

所以这里的实现是「按字符长度切 + 在句末标点处对齐 + 相邻块重叠 overlap 字符」。
"""

from __future__ import annotations

import re

SENTENCE_ENDS = "。！？!?；;\n"


def split_text(
    text: str,
    size: int = 400,
    overlap: int = 80,
    min_len: int = 60,
) -> list[dict]:
    """把长文本切成块，返回 [{"text":..., "start":..., "end":...}]。

    size    每块最多多少字符（中文 1 字≈1 token，400 字约 400 token）
    overlap 相邻块重叠多少字符，防止句子被切断后两边都读不懂
    min_len 太短的碎片（比如只剩一行标题）直接丢掉，噪声比信息多
    """
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    if not text:
        return []

    chunks: list[dict] = []
    start = 0
    n = len(text)

    while start < n:
        end = min(start + size, n)

        # 没到结尾时，往回找一个句末标点，让块结束在完整的句子后面
        if end < n:
            floor = max(start + size // 2, end - 120)     # 最多往回退 120 字，别退太狠
            window = text[floor:end]
            cut = max(window.rfind(p) for p in SENTENCE_ENDS)
            if cut >= 0:
                end = floor + cut + 1

        piece = text[start:end].strip()
        if len(piece) >= min_len or end >= n:
            chunks.append({"text": piece, "start": start, "end": end})

        if end >= n:
            break
        start = max(end - overlap, start + 1)             # 回退 overlap 字，防止切在句子中间

    return chunks


def load_corpus(directory: str) -> list[dict]:
    """读目录下所有 .md / .txt，返回 [{"text":..., "source":文件名}]。"""
    import os

    docs: list[dict] = []
    for name in sorted(os.listdir(directory)):
        if not name.lower().endswith((".md", ".txt")):
            continue
        with open(os.path.join(directory, name), encoding="utf-8-sig") as f:
            docs.append({"text": f.read(), "source": name})
    return docs


if __name__ == "__main__":
    demo = (
        "检索增强生成（RAG）先把资料切成小块。每个小块被转换成向量存进索引。"
        "用户提问时，先检索出最相关的小块，再把这些小块和问题一起交给模型。"
        "这样做的好处是模型不需要把所有知识都背在参数里。"
    )
    for i, c in enumerate(split_text(demo, size=60, overlap=20)):
        print(f"[{i}] start={c['start']:>3} end={c['end']:>3} {c['text']}")
