#!/usr/bin/env python3
"""week1-cli-chat —— 最小可用的命令行 LLM 聊天客户端。

三个必做点（也是面试会被追问的点）：
1. 多轮对话：自己维护 messages 列表，每一轮把「全量历史」发回去。
   —— 模型是无状态的，所谓"记忆"就是每次请求重发一遍历史。
2. 流式输出：stream=True，拿到 delta 就 print(flush=True)。
   —— 用户感知延迟从「等 8 秒」变成「0.5 秒出第一个字」。
3. 历史截断：上下文有上限，超预算时丢最老的轮次，但必须保住 system prompt。
   —— 这里用「估算 token + 从最新往回保留」的策略，简单但正确。

用法：
    python chat.py                 # 交互模式（需 .env 里的 API Key）
    python chat.py --mock          # 无 Key 也能跑，用假模型验证 UI 逻辑
    python chat.py --once "你好"    # 单轮，方便脚本化测试
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time

# Windows 控制台默认 GBK，流式输出中文/符号会乱码或报错，这里强制 UTF-8。
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    # utf-8-sig：Windows 管道/重定向的输入常带 BOM，不剥掉会混进第一条消息里
    sys.stdin.reconfigure(encoding="utf-8-sig", errors="replace")
except Exception:
    pass

DEFAULT_SYSTEM = "你是一个简洁、准确的中文助手。回答直接给结论，不确定就说不确定。"
DEFAULT_BASE_URL = "https://api.deepseek.com"   # 换成 https://dashscope.aliyuncs.com/compatible-mode/v1 可用通义
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_BUDGET = 4000        # 上下文预算（token），故意设得比模型上限小很多
PER_MESSAGE_OVERHEAD = 4     # 每条消息的角色标记 + 分隔符，大约 4 token


# ---------------------------------------------------------------- 配置

def load_dotenv(path: str = ".env") -> None:
    """极简 .env 解析，避免为了读 3 个变量引入 python-dotenv。"""
    if not os.path.exists(path):
        return
    # utf-8-sig：用记事本保存的 .env 会带 BOM，不剥掉第一个变量名就变成 "\ufeffOPENAI_API_KEY"
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_config(args: argparse.Namespace) -> dict:
    load_dotenv()
    return {
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "base_url": os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL),
        "model": args.model or os.getenv("MODEL", DEFAULT_MODEL),
        "system": args.system or DEFAULT_SYSTEM,
        "budget": args.max_context_tokens,
        "temperature": args.temperature,
    }


# ---------------------------------------------------------------- token 估算
# 真实分词要 tiktoken / 各家 tokenizer；W1 只需要「够用的估算」，
# 误差 20% 以内就够，省掉一个依赖。规则：中文 1 字≈1 token，英文 4 字符≈1 token。

_CJK = re.compile(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]")


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    cjk = len(_CJK.findall(text))
    other = len(text) - cjk
    return cjk + max(1, round(other / 4)) if other else cjk


# ---------------------------------------------------------------- 历史管理

class History:
    """多轮对话状态 + 截断策略。"""

    def __init__(self, system: str, budget: int) -> None:
        self.system = system
        self.budget = budget
        self.messages: list[dict[str, str]] = []
        self.dropped = 0

    # -- 读写
    def add(self, role: str, content: str) -> None:
        assert role in ("user", "assistant"), role
        self.messages.append({"role": role, "content": content})
        self.trim()

    def clear(self) -> None:
        self.messages.clear()
        self.dropped = 0

    # -- 统计
    def system_tokens(self) -> int:
        return estimate_tokens(self.system) + PER_MESSAGE_OVERHEAD

    def total_tokens(self) -> int:
        return self.system_tokens() + sum(
            estimate_tokens(m["content"]) + PER_MESSAGE_OVERHEAD for m in self.messages
        )

    # -- 截断：超预算就从最老的开始丢，但 system 永远保留
    def trim(self) -> None:
        if self.total_tokens() <= self.budget:
            return
        kept: list[dict[str, str]] = []
        used = self.system_tokens()
        for msg in reversed(self.messages):
            cost = estimate_tokens(msg["content"]) + PER_MESSAGE_OVERHEAD
            if used + cost > self.budget:
                break
            kept.append(msg)
            used += cost
        kept.reverse()
        # 对话必须从 user 开头：丢掉开头悬空的 assistant
        while kept and kept[0]["role"] != "user":
            kept.pop(0)
        # 极端情况（单条就超预算）：至少保住最新一条，否则这轮没法回
        if not kept and self.messages:
            kept = [self.messages[-1]]
        self.dropped += len(self.messages) - len(kept)
        self.messages = kept

    # -- 发请求时用的完整 payload
    def payload(self) -> list[dict[str, str]]:
        return [{"role": "system", "content": self.system}, *self.messages]


# ---------------------------------------------------------------- 模型调用

def stream_reply(client, model: str, messages: list[dict], temperature: float):
    """逐段 yield 文本增量。"""
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        stream=True,
    )
    for chunk in stream:
        if not chunk.choices:            # 有些厂商会发一个空 choices 的收尾包
            continue
        delta = chunk.choices[0].delta
        if delta and delta.content:
            yield delta.content


class MockClient:
    """不联网的假模型：用来在没有 API Key / 断网时验证整个交互流程。"""

    def __init__(self) -> None:
        self.chat = self
        self.completions = self

    def create(self, model: str, messages: list[dict], temperature: float, stream: bool = True):
        last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        reply = (
            f"[mock:{model}] 收到 {len(messages)} 条消息，这一轮你说的是：{last_user[:40]}。"
            "这是一段用于验证流式输出与多轮拼接的假回复。"
        )
        for ch in reply:
            time.sleep(0.01)
            yield type("C", (), {"choices": [type("X", (), {"delta": type("D", (), {"content": ch})()})()]})()


def is_placeholder_key(key: str) -> bool:
    """把「空」和「还是模板里的占位符」都当作没配置。

    新手最容易踩的坑：copy .env.example .env 之后忘了改那一行，
    于是 Key 非空、程序欢快地发出去、然后拿到一个 401。
    提前拦住，比让人看 AuthenticationError 强。
    """
    k = key.strip().lower()
    if not k:
        return True
    return "xxxx" in k or "你的" in k or "your" in k or k in {"sk-test", "sk-demo"}


def make_client(config: dict):
    if is_placeholder_key(config["api_key"]):
        sys.exit(
            "看起来还没配置真的 API Key（.env 里还是模板里的 sk-xxxx... 占位符）。\n"
            "两种办法：\n"
            "  1) 打开 .env，把 OPENAI_API_KEY= 后面换成 DeepSeek 平台申请到的真 Key\n"
            "     （https://platform.deepseek.com/ → API Keys → 创建，充值 10 元够用一整个寒假）\n"
            "  2) 先用 --mock 模式体验完整流程，不需要 Key\n"
        )
    from openai import OpenAI  # 延迟导入：mock 模式不需要装 openai

    return OpenAI(api_key=config["api_key"], base_url=config["base_url"])


# ---------------------------------------------------------------- 交互

HELP = """可用命令：
  /exit        退出
  /clear       清空历史（相当于开新会话）
  /tokens      查看当前 token 占用
  /help        显示本帮助"""


def run_turn(client, config: dict, history: History, text: str) -> None:
    history.add("user", text)
    print("\n助手> ", end="", flush=True)

    started = time.time()
    pieces: list[str] = []
    try:
        for piece in stream_reply(client, config["model"], history.payload(), config["temperature"]):
            pieces.append(piece)
            print(piece, end="", flush=True)
    except KeyboardInterrupt:
        print("\n[已中断本轮，已收到的内容仍会记入历史]")
    except Exception as exc:  # 网络/额度/模型名写错，都走这里
        print(f"\n[请求失败] {type(exc).__name__}: {exc}")
        history.messages.pop()  # 这一轮没答上，把 user 消息撤回，避免历史脏
        return

    reply = "".join(pieces)
    if reply:
        history.add("assistant", reply)
    cost = time.time() - started
    print(f"\n[{cost:.1f}s | 历史 {history.total_tokens()}/{history.budget} token", end="")
    if history.dropped:
        print(f" | 已丢弃 {history.dropped} 条旧消息", end="")
    print("]")


def chat_loop(client, config: dict) -> None:
    history = History(config["system"], config["budget"])
    print(f"week1-cli-chat | model={config['model']} | 上下文上限 {config['budget']} token")
    print("输入 /help 看命令，Ctrl+C 或 /exit 退出。\n")
    while True:
        try:
            text = input("你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见。")
            return
        if not text:
            continue
        if text in ("/exit", "/quit", "/q"):
            print("再见。")
            return
        if text == "/clear":
            history.clear()
            print("历史已清空。")
            continue
        if text == "/tokens":
            print(f"system {history.system_tokens()} + 消息 {len(history.messages)} 条，"
                  f"合计 {history.total_tokens()}/{history.budget}")
            continue
        if text == "/help":
            print(HELP)
            continue
        run_turn(client, config, history, text)


# ---------------------------------------------------------------- 入口

def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="最小可用的命令行 LLM 聊天客户端")
    p.add_argument("--model", help="模型名，默认读 MODEL 环境变量")
    p.add_argument("--system", help="system prompt")
    p.add_argument("--max-context-tokens", type=int, default=DEFAULT_BUDGET,
                   help=f"历史预算，默认 {DEFAULT_BUDGET}")
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--mock", action="store_true", help="用假模型跑通流程，不需要 API Key")
    p.add_argument("--once", metavar="TEXT", help="只问一轮然后退出")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    config = load_config(args)
    client = MockClient() if args.mock else make_client(config)

    if args.once:
        history = History(config["system"], config["budget"])
        history.add("user", args.once)
        print("助手> ", end="", flush=True)
        for piece in stream_reply(client, config["model"], history.payload(), config["temperature"]):
            print(piece, end="", flush=True)
        print()
        return 0

    chat_loop(client, config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
