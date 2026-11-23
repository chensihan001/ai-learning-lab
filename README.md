# ai-learning-lab

AI 应用开发实习冲刺：每周一个可运行的产出，从零手写，不用现成框架糊。

目标：寒假前拿到大模型应用开发方向的实习。九周计划见 [ai-intern-9week-plan.md](ai-intern-9week-plan.md)。

## 进度

| 周 | 产出 | 内容 | 状态 |
|---|---|---|---|
| W1 | [week1-cli-chat](week1-cli-chat/) | 命令行聊天客户端：流式输出 / 多轮上下文 / 历史预算截断 | ✅ |
| W2 | [week2-attention](week2-attention/) | 用 numpy 手写 self-attention：循环版 vs 矩阵版，数值等价 + 性能对比 | ✅ |
| W3-4 | [week3-rag](week3-rag/) | 检索增强问答：切块 / BM25 检索 / 带引用回答（评测集与向量检索进行中） | 🚧 |
| W5-6 | mini-agent | 手写 ReAct 循环 + 工具调用 + 记忆 | ⬜ |
| W7 | week7-lora | LLaMA-Factory + Qwen 微调，LoRA rank 对比实验 | ⬜ |

## 说明

- 每个目录都有独立 README，写清「为什么这么做 / 踩了什么坑 / 实测结果」。
- 不含任何 API Key：本地用 `.env`，已被 `.gitignore` 排除；仓库里只有 `.env.example`。

## AI 使用声明

脚手架、注释、测试用例由 AI 辅助生成；**核心实现、实验与结论由本人完成**，过程记录如下：

- **W1**：遇到 Windows 终端 BOM 编码导致 `.env` 读取失败的 bug（`OPENAI_API_KEY` 前的 BOM 让变量名变成 `\ufeffOPENAI_API_KEY`），定位后把读取方式从 `utf-8` 改为 `utf-8-sig`，并补上「占位符 Key 提前拦截」，最终跑通真实的多轮对话。
- **W2**：独立完成 self-attention 的矩阵乘法实现，与双循环版本逐元素对齐（最大误差 1e-16），并跑出 144–173 倍的性能差距；README 里的结论与观察由本人撰写。
