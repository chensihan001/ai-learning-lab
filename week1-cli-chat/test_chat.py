#!/usr/bin/env python3
"""离线自测：不联网、不需要 API Key。运行 python test_chat.py 即可。

只测「逻辑」不测「模型」——这一点很重要：面试官问"你怎么测试的"，
答"我把截断逻辑抽成纯函数单独测，模型调用用 mock 替身"比答"我手动聊了聊"强得多。
"""

from chat import History, estimate_tokens


def test_estimate_tokens():
    assert estimate_tokens("") == 0
    # 中文：1 字约 1 token
    assert 8 <= estimate_tokens("你好世界你好世界你好世界") <= 12
    # 英文：4 字符约 1 token
    assert 5 <= estimate_tokens("hello world this is a test") <= 8


def test_history_under_budget():
    h = History("system", budget=1000)
    h.add("user", "短问题")
    h.add("assistant", "短回答")
    assert h.total_tokens() <= 1000
    assert len(h.messages) == 2


def test_trim_drops_oldest():
    h = History("sys", budget=60)
    h.add("user", "这是一句比较长的话" * 3)
    h.add("assistant", "这也是一句比较长的回答" * 3)
    h.add("user", "最新的问题")
    assert h.dropped > 0, "超预算后应该丢弃旧消息"
    assert h.total_tokens() <= 60 or len(h.messages) == 1
    # 最新一轮必须还在
    assert h.messages[-1]["content"] == "最新的问题"


def test_trim_keeps_user_first():
    """截断不能留下开头悬空的 assistant，否则很多模型会报错或困惑。"""
    h = History("sys", budget=30)
    h.add("user", "一" * 40)
    h.add("assistant", "二" * 40)
    h.add("user", "三三三")
    h.add("assistant", "四四四")
    assert not h.messages or h.messages[0]["role"] == "user"


def test_payload_has_system_first():
    h = History("你是助手", budget=500)
    h.add("user", "hi")
    payload = h.payload()
    assert payload[0] == {"role": "system", "content": "你是助手"}
    assert payload[-1]["role"] == "user"


def test_clear():
    h = History("sys", 500)
    h.add("user", "hi")
    h.clear()
    assert h.messages == [] and h.dropped == 0


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(tests)} 个测试全部通过")
