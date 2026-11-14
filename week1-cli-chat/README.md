# week1-cli-chat

一个 **几十行核心逻辑 + 可跑通** 的命令行 LLM 聊天客户端。W1 的产出物：不是"我看完了教程"，而是"这是我的仓库，你 clone 下来就能跑"。

## 它做了什么

| 能力 | 实现要点 | 为什么面试会问 |
|---|---|---|
| 多轮对话 | 客户端自己维护 `messages` 列表，每轮把全量历史重发 | 模型无状态，"记忆"是应用层的事 |
| 流式输出 | `stream=True`，拿到 `delta.content` 就 `print(flush=True)` | 首字延迟从 5-8 秒降到 0.3-0.5 秒 |
| 历史截断 | 估算 token，超预算从最老的消息丢，system 永远保留、截断后必须从 user 开始 | 上下文是有限资源，不做截断迟早 400 报错 |
| 容错 | 请求失败回滚本轮 user 消息；Ctrl+C 中断保留已收内容 | 生产里网络抖动是常态 |
| 可测 | 截断逻辑抽成 `History` 纯类，`MockClient` 假模型替代网络 | "你怎么测的"有答案 |

## 快速开始

```powershell
cd week1-cli-chat
python -m pip install -r requirements.txt
python chat.py --mock                 # 先不花钱，验证交互是否正常
copy .env.example .env                # 然后填入 DeepSeek 的 Key
python chat.py                        # 真实对话
```

没有 Key 也能跑：`--mock` 用假模型跑通整个流式/多轮/截断流程，方便改代码时快速回归。

其他用法：

```powershell
python chat.py --once "用一句话解释什么是 token"     # 单轮，适合写脚本
python chat.py --max-context-tokens 800              # 故意压小预算，观察截断日志
python chat.py --model deepseek-reasoner             # 换模型
python test_chat.py                                  # 离线单测，不联网
```

## 交互命令

```
/exit     退出
/clear    清空历史（开新会话）
/tokens   看当前 token 占用
/help     帮助
```

## 设计取舍

- **估算 token 而不装 tiktoken**：W1 目标是理解机制，误差 20% 完全够用，还能省一个依赖。等做到 RAG 算 chunk 预算时再换真 tokenizer。
- **预算默认 4000 而不是顶满模型上限**：留余量给输出，也让截断逻辑在正常聊天就能被触发、被看到。
- **只用 `openai` 一个依赖**：DeepSeek / 通义 / Kimi / 智谱都提供 OpenAI 兼容接口，换 `OPENAI_BASE_URL` 即可，这套代码不用改。

## 验收标准（W1 结束前逐项打勾）

- [ ] `python chat.py --mock` 能连续对话 5 轮，历史条数正确增长
- [ ] 真实模型下能看到"逐字"输出，不是一次性蹦出来
- [ ] 把 `--max-context-tokens` 设成 200，聊 3 轮后出现"已丢弃 N 条旧消息"且不报错
- [ ] `python test_chat.py` 全绿
- [ ] 能对着代码讲清：为什么每轮要重发历史？截断为什么不能让 system 也被丢？

## 下一步（W2 预告）

本周只做"能跑"。W2 补原理（注意力/Transformer 到底在算什么），W3 开始把 `chat.py` 里的 `stream_reply` 换成带检索的版本——那就是 RAG 的起点。

## 常见问题

| 症状 | 原因 | 处理 |
|---|---|---|
| 启动就退出，说"还没配置真的 Key" | `.env` 是从 `.env.example` 复制的，`sk-xxxx...` 还是占位符 | 把那一行换成真 Key |
| `AuthenticationError: 401` | Key 错误 / 过期 / 未充值；或 Key 与 `OPENAI_BASE_URL` 不是同一家 | DeepSeek 的 Key 必须配 `https://api.deepseek.com` |
| `ModuleNotFoundError: openai` | 没装依赖 | `python -m pip install -r requirements.txt` |
| 报 `insufficient balance` | 账户没余额 | 充 10 元，W1 全部测试用不完 1 元 |
| 乱码 | 终端编码 | `chcp 65001`，或用 Windows Terminal |
| 装成了 openai 3.x | 版本比预期高 | 不影响：`create(..., stream=True)` 这个调用形状 1.x→3.x 未变 |

