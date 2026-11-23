#!/usr/bin/env python3
"""W3 测试：切块不丢内容、检索排序正确、prompt 带编号。

跑法：python test_rag.py
这些测试不花钱、不联网——RAG 里 90% 的 bug 都在检索侧，先把它测干净。
"""

from __future__ import annotations

import os
import sys

from bm25 import BM25Index, tokenize
from chunker import split_text
from rag import build_index, build_prompt

TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


@test
def test_chunks_do_not_exceed_size():
    text = "这是一句测试文本。" * 60
    for c in split_text(text, size=100, overlap=20):
        assert len(c["text"]) <= 100 + 20, f"块太长了：{len(c['text'])}"


@test
def test_chunks_keep_all_content():
    text = "甲乙丙丁戊。己庚辛壬癸。" * 40
    chunks = split_text(text, size=80, overlap=10)
    joined = "".join(c["text"] for c in chunks).replace("\n", "")
    # 重叠会让内容重复出现，所以只检查"原文里的每个字都进过某个块"
    for ch in set(text.replace("。", "").replace("\n", "")):
        assert ch in joined, f"字符 {ch} 丢了"


@test
def test_neighbour_chunks_overlap():
    text = "第一句话在这里。第二句话在这里。第三句话在这里。" * 20
    chunks = split_text(text, size=100, overlap=30)
    assert len(chunks) >= 2
    assert chunks[1]["start"] < chunks[0]["end"], "相邻块没有重叠，句子可能被切断"


@test
def test_chunks_end_on_sentence_boundary():
    text = "短句。" * 100
    for c in split_text(text, size=60, overlap=10):
        assert c["text"].endswith(("。", "！", "？", "\n")) or len(c["text"]) < 60


@test
def test_tokenize_handles_chinese_and_english():
    tokens = tokenize("BM25 检索 RAG")
    assert "bm25" in tokens and "rag" in tokens          # 英文转小写、整词
    assert "检索" in tokens                              # 中文二元组


@test
def test_bm25_ranks_relevant_doc_first():
    docs = [
        "LoRA 微调只训练低秩矩阵，显存占用小。",
        "RAG 先检索资料，再把资料拼进 prompt 让模型回答。",
        "BM25 靠词频和逆文档频率打分。",
    ]
    index = BM25Index(docs)
    hits = index.search("RAG 检索资料", k=3)
    assert hits and hits[0][0] == 1, f"排序错误：{hits}"


@test
def test_bm25_ignores_unrelated_query():
    index = BM25Index(["无关内容一。", "无关内容二。"])
    assert index.search("量子纠缠", k=2) == [] or all(s > 0 for _, s in index.search("量子纠缠", k=2))


@test
def test_prompt_numbers_each_reference():
    chunks = [{"text": "第一块内容", "source": "a.md"}, {"text": "第二块内容", "source": "b.md"}]
    prompt = build_prompt("测试问题", [(0, 1.5), (1, 0.9)], chunks)
    assert "[1]" in prompt and "[2]" in prompt
    assert "测试问题" in prompt and "a.md" in prompt


@test
def test_corpus_retrieval_crosses_files():
    """真实语料上跑一遍：问 Agent 的问题，应该优先命中 agent-notes.md。"""
    chunks, index = build_index(os.path.join(os.path.dirname(os.path.abspath(__file__)), "corpus"))
    hits = index.search("ReAct 循环是怎么工作的", k=1)
    assert hits, "检索不到内容"
    top_source = chunks[hits[0][0]]["source"]
    assert top_source == "agent-notes.md", f"命中了错误文件：{top_source}"


def main() -> int:
    failed = 0
    for fn in TESTS:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {fn.__name__}: {exc}")
    print(f"\n{len(TESTS) - failed}/{len(TESTS)} 通过")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

