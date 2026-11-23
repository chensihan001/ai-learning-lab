#!/usr/bin/env python3
"""W3 第 2 步：BM25 检索。

为什么第一版用 BM25 而不是向量检索？
  - BM25 是纯统计，30 行代码，不花钱、不联网、结果可解释：你能指着说"这块命中了 3 个词"。
  - 向量检索要先解决 embedding API、维度、归一化、相似度，出错的地方多，容易"跑不起来也说不清哪里错"。
  - 真实系统里两者是**混合**用的：BM25 擅长精确词（型号、人名、API 名），向量擅长语义（"怎么加速"≈"性能优化"）。

中文没有空格，分词是个坑。这里用「字 + 二元组」：
  "注意力机制" → 注意 / 意力 / 力机 / 机制 这 4 个 bigram
优点：不需要 jieba，零依赖，专业名词命中率高。
缺点：召回靠字面，同义词完全不认（"加速" 搜不到 "性能优化"）——这正是后面要加向量检索的原因。
"""

from __future__ import annotations

import math
import re
from collections import Counter

LATIN = re.compile(r"[a-z0-9_]+")
CJK_RUN = re.compile(r"[\u4e00-\u9fff]+")


def tokenize(text: str) -> list[str]:
    """英文按词、中文按二元组切，全部小写。"""
    lowered = text.lower()
    tokens: list[str] = LATIN.findall(lowered)
    for run in CJK_RUN.findall(lowered):
        if len(run) == 1:
            tokens.append(run)                      # 单个汉字（如"块"）也要能被搜到
        tokens.extend(run[i : i + 2] for i in range(len(run) - 1))
    return tokens


class BM25Index:
    """标准 BM25（k1 控制词频饱和、b 控制长度归一化）。"""

    def __init__(self, docs: list[str], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.docs = docs
        self.tfs = [Counter(tokenize(d)) for d in docs]
        self.lens = [sum(tf.values()) for tf in self.tfs]
        self.avgdl = (sum(self.lens) / len(self.lens)) if self.lens else 0.0

        df: Counter = Counter()
        for tf in self.tfs:
            df.update(tf.keys())
        n = len(docs)
        # 加 1 的平滑：避免 df 很高时 idf 变负数，导致"到处都有的词"起反作用
        self.idf = {term: math.log((n - d + 0.5) / (d + 0.5) + 1) for term, d in df.items()}

    def search(self, query: str, k: int = 3) -> list[tuple[int, float]]:
        """返回 [(文档下标, 分数)]，按分数从高到低。"""
        q_terms = Counter(tokenize(query))
        scores: list[float] = []
        for i, tf in enumerate(self.tfs):
            score = 0.0
            for term, q_count in q_terms.items():
                f = tf.get(term)
                if not f:
                    continue
                norm = 1 - self.b + self.b * (self.lens[i] / self.avgdl if self.avgdl else 0)
                score += self.idf.get(term, 0.0) * (f * (self.k1 + 1)) / (f + self.k1 * norm) * q_count
            scores.append(score)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return [(i, s) for i, s in ranked[:k] if s > 0]

    def explain(self, query: str, doc_index: int) -> list[tuple[str, float]]:
        """调试用：看看哪些词真正贡献了分数。"""
        q_terms = Counter(tokenize(query))
        tf = self.tfs[doc_index]
        norm = 1 - self.b + self.b * (self.lens[doc_index] / self.avgdl if self.avgdl else 0)
        hits = []
        for term in q_terms:
            f = tf.get(term)
            if f:
                hits.append((term, round(self.idf.get(term, 0.0) * (f * (self.k1 + 1)) / (f + self.k1 * norm), 3)))
        return sorted(hits, key=lambda x: x[1], reverse=True)


if __name__ == "__main__":
    docs = [
        "自注意力机制把每个位置和所有位置做点积，得到注意力权重后再加权求和。",
        "BM25 是经典的词频检索算法，靠词频和逆文档频率给文档打分。",
        "微调 LoRA 只需要训练少量的低秩矩阵，显存占用比全量微调小得多。",
    ]
    index = BM25Index(docs)
    for q in ("注意力是怎么算的", "LoRA 省显存", "数据库索引"):
        hits = index.search(q, k=2)
        print(f"\n查询：{q}")
        if not hits:
            print("  （没有命中——BM25 不认识同义词/无关词，这是它的短板）")
        for i, s in hits:
            print(f"  {s:6.2f}  {docs[i]}")
