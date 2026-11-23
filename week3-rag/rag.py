#!/usr/bin/env python3
"""W3 第 3 步：把「检索」和「生成」接起来，这就是一个 RAG。

完整流水线只有四步：
    读文档 → 切块 → 建索引 → 提问时检索 top-k 并拼进 prompt

    python rag.py --question "RAG 为什么要切块"
    python rag.py --question "BM25 有什么缺点" --no-llm     # 只看检索结果，不调模型（省钱、好调试）
    python rag.py --question "..." --mock                   # 没 Key 也想跑通流程时用

调试顺序很重要：先 `--no-llm` 确认检索捞对了，再看模型回答。
否则答得不好，你分不清是检索的锅还是模型的锅。
"""

from __future__ import annotations

import argparse
import os
import sys

from bm25 import BM25Index
from chunker import load_corpus, split_text

SYSTEM_PROMPT = """你是资料问答助手。必须遵守以下规则：
1. 只根据【资料】里的内容回答，不要用你自己的知识补充。
2. 资料里找不到答案时，直接说「资料里没有提到」，不要猜。
3. 每个结论后面用 [编号] 标出它来自哪一块资料。
4. 回答用中文，简洁，不要复述资料原文的整段。"""


def load_env(path: str = ".env") -> None:
    """极简 .env 读取（不引第三方库）；已存在的环境变量优先。

    会从当前目录往上找 3 层，这样在 week3-rag/ 里跑也能读到仓库根目录的 .env。
    """
    candidates = [path]
    base = os.path.dirname(os.path.abspath(__file__))
    for _ in range(3):
        candidates.append(os.path.join(base, ".env"))
        base = os.path.dirname(base)

    for candidate in candidates:
        if not os.path.exists(candidate):
            continue
        with open(candidate, encoding="utf-8-sig") as f:   # utf-8-sig：兼容记事本保存的 BOM
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
        return


def build_index(corpus_dir: str) -> tuple[list[dict], BM25Index]:
    chunks: list[dict] = []
    for doc in load_corpus(corpus_dir):
        for piece in split_text(doc["text"]):
            chunks.append({"text": piece["text"], "source": doc["source"]})
    if not chunks:
        raise SystemExit(f"语料目录 {corpus_dir} 里没有可用的 .md/.txt 文件")
    return chunks, BM25Index([c["text"] for c in chunks])


def build_prompt(question: str, hits: list[tuple[int, float]], chunks: list[dict]) -> str:
    """把检索结果拼成带编号的上下文——编号是让模型能引用、让你能核对的关键。"""
    blocks = [
        f"[{rank}] 来源：{chunks[i]['source']}（相关度 {score:.2f}）\n{chunks[i]['text']}"
        for rank, (i, score) in enumerate(hits, start=1)
    ]
    return "【资料】\n" + "\n\n".join(blocks) + f"\n\n【问题】\n{question}"


def ask_llm(prompt: str, model: str, temperature: float = 0.2) -> None:
    """流式打印回答。"""
    from openai import OpenAI

    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
        base_url=os.environ.get("OPENAI_BASE_URL") or None,
    )
    stream = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            print(delta, end="", flush=True)
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="最小可用 RAG：BM25 检索 + 大模型回答")
    parser.add_argument("--question", "-q", help="要问的问题；不给则进入交互模式")
    parser.add_argument("--corpus", default=os.path.join(os.path.dirname(__file__), "corpus"),
                        help="语料目录（默认 ./corpus）")
    parser.add_argument("--top-k", type=int, default=3, help="检索几块资料（默认 3）")
    parser.add_argument("--no-llm", action="store_true", help="只打印检索结果，不调用模型")
    parser.add_argument("--mock", action="store_true", help="不调用模型，用假回答验证流程")
    parser.add_argument("--model", default=os.environ.get("MODEL", "deepseek-chat"))
    args = parser.parse_args()

    load_env()
    chunks, index = build_index(args.corpus)
    print(f"语料：{len(chunks)} 块，来自 {len({c['source'] for c in chunks})} 个文件", file=sys.stderr)

    def answer(question: str) -> None:
        hits = index.search(question, k=args.top_k)
        if not hits:
            print("（没有检索到任何相关内容——换个说法，或扩充语料）")
            return
        prompt = build_prompt(question, hits, chunks)

        if args.no_llm:
            print(prompt)
            return
        if args.mock:
            refs = " ".join(f"[{r}]" for r in range(1, len(hits) + 1))
            print(f"（mock 模式）根据资料 {refs}，这里会是模型的回答。检索到的块数：{len(hits)}")
            return

        if not os.environ.get("OPENAI_API_KEY"):
            raise SystemExit("没有配置 OPENAI_API_KEY。先 `cp .env.example .env` 填 Key，或加 --no-llm / --mock")
        ask_llm(prompt, model=args.model)

    if args.question:
        answer(args.question)
        return

    print("RAG 交互模式（输入 exit 退出）", file=sys.stderr)
    while True:
        try:
            question = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question.lower() in {"exit", "quit", "q", ""}:
            break
        answer(question)


if __name__ == "__main__":
    main()
