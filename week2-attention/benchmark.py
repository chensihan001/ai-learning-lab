#!/usr/bin/env python3
"""W2 实验：同一个 attention，循环版 vs 矩阵版，慢多少倍？

跑 `python benchmark.py`，把输出的表格抄进 README。这张表就是
"为什么深度学习框架都在拼矩阵乘法"的第一手证据。

注意：循环版在 n=1024 时会慢到十几秒，所以大 n 只测向量化版。
"""

from __future__ import annotations

import time

import numpy as np

from attention import attention_naive, attention_vectorized, causal_mask


def timeit(fn, Q, K, V, mask, repeat: int = 3) -> float:
    """跑 repeat 次取最小值——最小值受系统抖动影响最小，比平均值稳。"""
    best = float("inf")
    for _ in range(repeat):
        t0 = time.perf_counter()
        fn(Q, K, V, mask)
        best = min(best, time.perf_counter() - t0)
    return best


def main() -> None:
    d = 64
    rng = np.random.default_rng(0)
    print(f"{'n':>6} {'循环版(ms)':>12} {'矩阵版(ms)':>12} {'加速比':>8}")
    print("-" * 42)

    for n in (64, 128, 256, 512):
        Q = rng.normal(size=(n, d))
        K = rng.normal(size=(n, d))
        V = rng.normal(size=(n, d))
        mask = causal_mask(n)
        t_loop = timeit(attention_naive, Q, K, V, mask) * 1000
        try:
            t_vec = timeit(attention_vectorized, Q, K, V, mask) * 1000
            print(f"{n:>6} {t_loop:>12.2f} {t_vec:>12.2f} {t_loop / t_vec:>7.0f}x")
        except NotImplementedError:
            print(f"{n:>6} {t_loop:>12.2f} {'TODO':>12} {'-':>8}")
            if n == 64:
                print("（先把 attention_vectorized 写完，再跑一次）")
            break

    print("\n补充观察：n 翻倍时，循环版耗时约变成 4 倍——这就是 O(n²) 的代价。"
          "\n上下文从 4K 涨到 32K 时，注意力计算量变成 64 倍，这也是长上下文贵的原因。")


if __name__ == "__main__":
    main()
