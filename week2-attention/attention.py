#!/usr/bin/env python3
"""W2：把 attention 拆开看——从双循环到一次矩阵乘法。

这个文件里有四个函数，前三个已经写好，`attention_vectorized` 是留给你的作业。
作业完成后 `python test_attention.py` 必须全绿，两个实现的结果要逐元素相等。

为什么值得亲手写一遍：
  "注意力机制就是把 Q 和 K 的点积做 softmax，再拿去加权 V"
  这句话你能背下来，但只有自己写过一遍，才知道 d_k 为什么要开根号、
  mask 到底加在 softmax 之前还是之后、为什么它能一次算完整个序列。

背景符号：
  Q —— query，长度为 n 的"我在找什么"（n = 输出位置的个数）
  K —— key，  长度为 m 的"我能提供什么"
  V —— value, 长度为 m 的"我实际给出的内容"
  打分矩阵 scores[i][j] = Q[i] · K[j] / sqrt(d_k)，表示第 i 个输出位置对第 j 个输入的关注度。
"""

from __future__ import annotations

import numpy as np


# ----------------------------------------------------------------- 1. softmax
def softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    """减最大值再取指数，防止 exp 溢出。

    不减去 max 的话，输入里只要有一个 100，exp(100) 就变成 inf，整行变 nan。
    这行 `x - x.max()` 不改变结果（softmax 对整体平移不变），只是让它算得出来。
    """
    shifted = x - np.max(x, axis=axis, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=axis, keepdims=True)


# ----------------------------------------------------------------- 2. 因果掩码
def causal_mask(n: int) -> np.ndarray:
    """下三角为 True 的 (n, n) 布尔矩阵。

    mask[i][j] = True 表示"第 i 个位置允许看到第 j 个位置"。
    语言模型在预测第 i 个 token 时不能偷看第 i+1 个，所以上三角必须置负无穷。
    """
    return np.tril(np.ones((n, n), dtype=bool))


# ----------------------------------------------------------------- 3. 双重循环版（慢，但公式最清楚）
def attention_naive(
    Q: np.ndarray,
    K: np.ndarray,
    V: np.ndarray,
    mask: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """返回 (输出, 注意力权重)，形状分别是 (n, d_v) 和 (n, m)。

    故意用两层 for 循环写，慢几十倍，但每一行就是论文里的一个符号。
    先把它看懂，再去看向量化版本为什么等价。
    """
    n, d_k = Q.shape
    m, d_v = V.shape
    assert K.shape == (m, d_k), f"K 应该是 ({m}, {d_k})，实际 {K.shape}"

    scores = np.zeros((n, m), dtype=np.float64)
    for i in range(n):
        for j in range(m):
            scores[i, j] = np.dot(Q[i], K[j]) / np.sqrt(d_k)   # 点积 + 缩放

    if mask is not None:
        # 用 -1e9 而不是 -inf：-inf 参与减法后仍可能生成 nan（inf - inf）
        scores = np.where(mask, scores, -1e9)

    weights = softmax(scores)            # 每行归一化，行和 = 1

    output = np.zeros((n, d_v), dtype=np.float64)
    for i in range(n):
        for j in range(m):
            output[i] += weights[i, j] * V[j]
    return output, weights


# ----------------------------------------------------------------- 4. 向量化版（你的作业）
def attention_vectorized(
    Q: np.ndarray,
    K: np.ndarray,
    V: np.ndarray,
    mask: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """和 attention_naive 数学上完全等价，但用矩阵乘法一次算完。

    提示（照着这个顺序写，五行左右）：
      1. scores = Q @ K.T        —— (n,d_k) @ (d_k,m) 得到 (n,m) 的所有点积
      2. scores = scores / sqrt(d_k)
      3. mask 不为 None 时：scores = np.where(mask, scores, -1e9)
      4. weights = softmax(scores)
      5. output = weights @ V    —— (n,m) @ (m,d_v) 得到 (n,d_v)
    写完跑 `python test_attention.py`，等价性测试应该从红变绿。
    """
    d_k = Q.shape[1]                        # 提示里漏了这行，导致 NameError
    scores = Q @ K.T                        # (n,d_k) @ (d_k,m) → (n,m)
    scores = scores / np.sqrt(d_k)
    if mask is not None:
        scores = np.where(mask, scores, -1e9)
    weights = softmax(scores)
    output = weights @ V                    # (n,m) @ (m,d_v) → (n,d_v)
    return output, weights

# ----------------------------------------------------------------- demo
if __name__ == "__main__":
    rng = np.random.default_rng(0)
    n, m, d_k, d_v = 4, 4, 8, 8
    Q, K, V = (rng.normal(size=(n, d_k)), rng.normal(size=(m, d_k)), rng.normal(size=(m, d_v)))

    out, w = attention_naive(Q, K, V, causal_mask(n))
    print("输出形状:", out.shape, " 权重形状:", w.shape)
    print("每行权重和:", np.round(w.sum(axis=1), 6))
    print("第 0 行的权重:", np.round(w[0], 3), "（只看得到自己，所以只有一个 1）")
