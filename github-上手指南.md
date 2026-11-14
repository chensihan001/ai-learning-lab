# 把你的产出变成 GitHub 仓库（新手版，Windows / PowerShell）

目标：明天你简历上能写下一行可点击的链接，而不是"做过一些练习"。

---

## 0. 先定架构：一个总仓库 + 两个精修仓库

**不要**每个练习建一个仓库。理由很实际：面试官只会点开 1-2 个链接，
9 个碎片仓库会让他觉得"这是一堆教程作业"，而一个持续提交 9 周的总仓库会让他觉得"这人在认真干"。

```
ai-intern-labs/           ← 练习场，每周往里加一个目录，公开
├── README.md             ← 进度表 + 每个产出的链接 + 当前状态
├── plan/                 ← 9 周计划、笔记
├── week1-cli-chat/
├── week2-attention/      （W2 加）
└── ...

rag-from-scratch/         ← W4 结束时单独建，精修 README，简历主挂这个
mini-agent/               ← W6 结束时单独建，简历次挂
```

`ai-intern-labs` 现在就能建；后两个等做出来再说。

---

## 1. 修 git 身份（先做，否则贡献图不显示你的名字）

目前 `week1-cli-chat` 里的两次提交，作者是我建仓时用的临时值
`chen sihan <chensihan@example.com>` —— GitHub 不会把它算成你的贡献。

```powershell
# 换成你自己的（用户名就是 github.com/ 后面那串）
git config --global user.name "你的GitHub用户名"
git config --global user.email "你的GitHub注册邮箱"

# 确认
git config --global --list | Select-String "user."
```

> 不想暴露真实邮箱？GitHub 提供隐私邮箱：Settings → Emails → 勾
> "Keep my email addresses private"，复制那个 `数字+用户名@users.noreply.github.com` 填进去。

历史里那两个旧提交：因为下面要重新组织目录，**直接丢掉重建更干净**
（只有 2 个提交，没有价值需要保留）。如果你就是想保留，用
`git rebase -i --root` 逐个 `commit --amend --reset-author`，新手不必折腾。

---

## 2. 把 ailearning 变成总仓库

```powershell
cd C:\Users\陈司翰\Documents\deepseek-harness\ailearning

# 丢掉 week1-cli-chat 内层的 .git（否则外层会把它当 submodule，踩坑）
Remove-Item -Recurse -Force week1-cli-chat\.git

# 外层重新初始化
git init -b main
```

然后在 `ailearning\` 下建两个文件：

**`.gitignore`**（根级，管全仓）

```gitignore
# 密钥——这一条最重要
.env
.env.*
!.env.example

# Python
__pycache__/
*.py[cod]
.venv/
venv/
.pytest_cache/

# 数据/模型/大文件（RAG 阶段会用到）
data/
*.faiss
*.index
*.bin
*.safetensors

# 编辑器 / 系统
.vscode/
.idea/
.DS_Store
Thumbs.db
*.log
```

**`README.md`**（总索引，仓库的脸）

```markdown
# ai-intern-labs

AI 应用开发实习冲刺的练习场：每周一个可运行的产出，从零手写，不用现成框架糊。

目标：寒假前拿到大模型应用开发方向实习。方向选择与取舍见 [plan/](plan/)。

## 进度

| 周 | 产出 | 内容 | 状态 |
|---|---|---|---|
| W1 | [week1-cli-chat](week1-cli-chat/) | 命令行聊天客户端：流式输出 / 多轮上下文 / 历史预算截断 | ✅ |
| W2 | week2-attention | 用 numpy 手写 self-attention，对比 F.scaled_dot_product_attention | ⬜ |
| W3-4 | rag-from-scratch | 检索增强问答：切块 / 向量化 / 检索 / 评测集 | ⬜ |
| W5-6 | mini-agent | 手写 ReAct 循环 + 工具调用 + 记忆 | ⬜ |
| W7 | week7-lora | LLaMA-Factory + Qwen 微调，LoRA rank 对比实验 | ⬜ |

## 说明

- 每个目录都有独立 README：讲清"为什么这么做"和"踩了什么坑"。
- 不含任何 API Key，本地用 `.env`（已忽略）。
```

提交：

```powershell
git add -A
git commit -m "chore: init ai-intern-labs, add W1 cli chat"
```

---

## 3. 在 GitHub 网页建仓库

1. 打开 https://github.com/new
2. **Repository name**：`ai-intern-labs`
3. **Description**：`AI 应用开发实习冲刺练习场：每周一个从零手写的产出（RAG / Agent）`
4. 选 **Public**（私有仓库面试官看不到，等于没做）
5. **三个初始化选项全部不要勾**：Add a README / Add .gitignore / Choose a license
   （本地已经有文件，勾了会冲突，你得再 `git pull --rebase`，新手容易卡住）
6. 点 **Create repository**

建完页面会显示一片"快速开始"命令，忽略它，用下一节。

---

## 4. 关联并推送

```powershell
cd C:\Users\陈司翰\Documents\deepseek-harness\ailearning
git remote add origin https://github.com/<你的用户名>/ai-intern-labs.git
git push -u origin main
```

### 认证：会弹窗，别慌

第一次推送时 Git Credential Manager 会弹出窗口，选 **"Sign in with your browser"** →
浏览器里登录 GitHub → 点 Authorize。之后就记住了，以后 push 不用再登。

**如果没弹窗、或 push 报 `Authentication failed`**，用 PAT：

1. GitHub 右上角头像 → Settings → 左侧拉到底 **Developer settings**
2. **Personal access tokens** → **Tokens (classic)** → **Generate new token (classic)**
3. Note 填 `laptop-push`，Expiration 选 90 days，勾选 **`repo`** 这一整项
4. Generate → **立刻复制那串 `ghp_...`**（页面一关就再也看不到）
5. 再 push 一次，用户名填 GitHub 用户名，**密码栏粘贴 PAT**（不是账号密码，账号密码早就不支持了）

存起来免得每次输：

```powershell
git config --global credential.helper manager
```

---

## 5. push 完立刻验证这 3 件事

```powershell
# 1) 本地确认密钥没被跟踪（只应看到 .env.example）
git ls-files | Select-String "env"

# 2) 确认远端有了
git log --oneline -1
git remote -v
```

3. 打开 `https://github.com/<你的用户名>/ai-intern-labs`，检查：
   - [ ] README 正常渲染，进度表能看到
   - [ ] 点进 `week1-cli-chat/`，`chat.py` 能在线看
   - [ ] 仓库里搜不到任何 `sk-` 开头的字符串
   - [ ] 头像旁边显示的是你的名字（不是 chen sihan）

第 3 条是红线：**公开仓库里的 Key 会在几分钟内被爬虫扫到并刷光额度**。
你已经 `copy .env.example .env` 过，确认 `.env` 没进仓库；万一进过，
立刻去 DeepSeek 后台删除那个 Key 重新生成。

---

## 6. 以后的日常节奏

```powershell
git add -A
git commit -m "week2: 手写 self-attention + 与 PyTorch 实现数值对比"
git push
```

commit message 的规矩：`动词: 具体做了什么`，别写 `update`、`fix bug`。
你以后面试讲项目时会回看这些 message——它们就是你的工作日志。

**每周至少 2 次提交**，不是刷绿格子，是让仓库看起来"活着"。
HR 打开仓库第一眼看的是"最后一次提交是什么时候"。

---

## 附：如果你坚持每个项目独立仓库

```powershell
cd week1-cli-chat
git config user.name "你的用户名"; git config user.email "你的邮箱"
git commit --amend --reset-author --no-edit
# 网页新建空仓库 week1-cli-chat（同样三个选项都不勾）
git remote add origin https://github.com/<用户名>/week1-cli-chat.git
git push -u origin main
```

能用，但九周下来你会有一堆星标为 0 的小仓库，简历上也只能写一个链接。
