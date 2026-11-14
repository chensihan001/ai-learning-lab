# ai-intern-labs

AI 应用开发实习冲刺：每周一个可运行的产出，从零手写
个人学习过程记录

## 进度

| 周 | 产出 | 内容 | 状态 |
|---|---|---|---|
| W1 | [week1-cli-chat](week1-cli-chat/) | 命令行聊天客户端：流式输出 / 多轮上下文 / 历史预算截断 | ✅ |
| W2 | week2-attention | 用 numpy 手写 self-attention，对比 F.scaled_dot_product_attention | ⬜ |
| W3-4 | rag-from-scratch | 检索增强问答：切块 / 向量化 / 检索 / 评测集 | ⬜ |
| W5-6 | mini-agent | 手写 ReAct 循环 + 工具调用 + 记忆 | ⬜ |
| W7 | week7-lora | LLaMA-Factory + Qwen 微调，LoRA rank 对比实验 | ⬜ |

## 说明

- 每个目录都有独立 README
- 不含任何 API Key，本地用 `.env`（已忽略）
week i的readme以及基础代码(如终端交互 流式输出)由ai辅助生成 下述文字由本人执笔
W1: 在遇到windows终端BOM编码导致的读取bug时，笔者借助ai修改了chat.py中的读取方式并最终跑通的真实的多轮对话