#!/usr/bin/env python3
"""W2 自测：python test_attention.py

最后一个等价性测试现在是红的（NotImplementedError），
你把 attention_vectorized 写完，它就该变绿——这是本周唯一的验收标准。
"""

import numpy as np

from attention import attention_naive, attention_vectorized, causal_mask, softmax


def setup():
    rng = np.random.default_rng(42)
    n = m = 6
    d_k = d_v = 8
    Q = rng.normal(size=(n, d_k)).astype(np.float64)
    K = rng.normal(size=(m, d_k)).astype(np.float64)
    V = rng.normal(size=(m, d_v)).astype(np.float64)
    return Q, K, V


def test_softmax_rows_sum_to_one():
    x = np.array([[1.0, 2.0, 3.0], [0.0, 0.0, 0.0]])
    w = softmax(x)
    assert np.allclose(w.sum(axis=1), 1.0)
    assert np.allclose(w[1], 1 / 3)          # 全相等时均匀分布


def test_softmax_is_numerically_stable():
    """输入很大时不能溢出成 nan——这就是要先减 max 的原因。"""
    x = np.array([[1000.0, 1000.0, 1000.0]])
    w = softmax(x)
    assert not np.isnan(w).any()
    assert np.allclose(w, 1 / 3)


def test_shapes():
    Q, K, V = setup()
    out, w = attention_naive(Q, K, V)
    assert out.shape == (6, 8)
    assert w.shape == (6, 6)
    assert np.allclose(w.sum(axis=1), 1.0)   # 每一行都是概率分布


def test_causal_mask_blocks_the_future():
    """位置 0 只能看自己，所以它的输出必须严格等于 V[0]。"""
    Q, K, V = setup()
    out, w = attention_naive(Q, K, V, causal_mask(6))
    assert np.allclose(out[0], V[0], atol=1e-9)
    assert np.allclose(w[0, 0], 1.0, atol=1e-6)      # 全部注意力给了自己
    assert w[0, 1] < 1e-6                           # 未来位置权重≈0
    # 上三角必须都是 0
    assert np.allclose(np.triu(w, k=1), 0.0, atol=1e-6)


def test_scaling_matters():
    """不除以 sqrt(d_k) 时，d_k 越大点积越分散，softmax 越接近 one-hot。

    这就是论文里那个 sqrt(d_k) 的全部理由：把点积的方差拉回 1 左右，
    否则 d_k=64 时模型几乎只关注一个位置，梯度也会被压平。
    """
    rng = np.random.default_rng(1)
    d_k = 64
    q = rng.normal(size=d_k)
    K = rng.normal(size=(d_k, d_k))
    raw = K @ q                    # 未缩放的点积
    scaled = raw / np.sqrt(d_k)
    assert raw.std() > scaled.std() * 5     # 缩放后方差明显变小


def test_naive_equals_vectorized():
    """核心验收：两种写法必须逐元素相等（允许 1e-9 的浮点误差）。"""
    Q, K, V = setup()
    for mask in (None, causal_mask(6)):
        out_a, w_a = attention_naive(Q, K, V, mask)
        out_b, w_b = attention_vectorized(Q, K, V, mask)
        assert np.allclose(out_a, out_b, atol=1e-9), "输出不一致"
        assert np.allclose(w_a, w_b, atol=1e-9), "注意力权重不一致"


if __name__ == "__main__":
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except NotImplementedError:
            failed += 1
            print(f"TODO {name}  ← 还没写 attention_vectorized")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {name}  {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} 通过")
    raise SystemExit(1 if failed else 0)
