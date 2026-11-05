#!/usr/bin/env python3
"""
Apex-Sovereign: Pure Python Transformer Language & Reasoning Architecture
RoPE, Grouped-Query Attention (GQA), RMSNorm, SwiGLU, and KV-Cache
100% Pure Python Standard Library | Zero Dependencies
"""

from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional, Tuple

from apex_council.transformer.config import TransformerConfig


def _mat_vec_mul(mat: List[List[float]], vec: List[float]) -> List[float]:
    """Multiplies matrix (R x C) by vector (C), returning vector (R)."""
    return [sum(mat[r][c] * vec[c] for c in range(len(vec))) for r in range(len(mat))]


def _rmsnorm(x: List[float], weight: List[float], eps: float = 1e-5) -> List[float]:
    variance = sum(v * v for v in x) / len(x)
    inv_std = 1.0 / math.sqrt(variance + eps)
    return [x[i] * inv_std * weight[i] for i in range(len(x))]


def _apply_rope(vec: List[float], pos: int, rope_theta: float = 10000.0) -> List[float]:
    """Applies Rotary Position Embedding (RoPE) to a head vector of even dimension."""
    dim = len(vec)
    out = list(vec)
    for i in range(0, dim, 2):
        freq = 1.0 / (rope_theta ** (i / dim))
        angle = pos * freq
        cos_val = math.cos(angle)
        sin_val = math.sin(angle)
        x0 = vec[i]
        x1 = vec[i + 1] if i + 1 < dim else 0.0
        out[i] = x0 * cos_val - x1 * sin_val
        if i + 1 < dim:
            out[i + 1] = x0 * sin_val + x1 * cos_val
    return out


class TransformerBlock:
    def __init__(self, config: TransformerConfig, layer_idx: int) -> None:
        self.config = config
        self.layer_idx = layer_idx
        d = config.d_model
        d_ff = config.d_ff
        h = config.n_heads
        kv_h = config.n_kv_heads
        head_dim = d // h

        # Deterministic seeded pseudo-random initialization
        rng = random.Random(42 + layer_idx * 1337)
        scale = 1.0 / math.sqrt(d)

        # Norms
        self.attn_norm = [1.0] * d
        self.ffn_norm = [1.0] * d

        # Q, K, V, Out projections
        self.wq = [[rng.gauss(0.0, scale) for _ in range(d)] for _ in range(h * head_dim)]
        self.wk = [[rng.gauss(0.0, scale) for _ in range(d)] for _ in range(kv_h * head_dim)]
        self.wv = [[rng.gauss(0.0, scale) for _ in range(d)] for _ in range(kv_h * head_dim)]
        self.wo = [[rng.gauss(0.0, scale) for _ in range(h * head_dim)] for _ in range(d)]

        # SwiGLU FFN projections
        ff_scale = 1.0 / math.sqrt(d)
        self.w_gate = [[rng.gauss(0.0, ff_scale) for _ in range(d)] for _ in range(d_ff)]
        self.w_up = [[rng.gauss(0.0, ff_scale) for _ in range(d)] for _ in range(d_ff)]
        self.w_down = [[rng.gauss(0.0, 1.0 / math.sqrt(d_ff)) for _ in range(d_ff)] for _ in range(d)]


class TransformerModel:
    """
    Pure Python Decoder-Only Transformer with RoPE, GQA, RMSNorm, SwiGLU, and KV Cache.
    """

    def __init__(self, config: TransformerConfig) -> None:
        self.config = config
        d = config.d_model
        v = config.vocab_size

        rng = random.Random(1337)
        scale = 1.0 / math.sqrt(d)

        # Embedding table [vocab_size, d_model]
        self.embeddings = [[rng.gauss(0.0, scale) for _ in range(d)] for _ in range(v)]

        # Layers
        self.layers = [TransformerBlock(config, i) for i in range(config.n_layers)]

        # Final RMSNorm
        self.norm = [1.0] * d

        # Output head [vocab_size, d_model]
        self.lm_head = [[rng.gauss(0.0, scale) for _ in range(d)] for _ in range(v)]

    def forward(
        self,
        tokens: List[int],
        kv_cache: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[List[List[float]], List[Dict[str, Any]]]:
        """
        Forward pass over tokens sequence.
        Returns (logits [seq_len, vocab_size], updated_kv_cache).
        """
        if not tokens:
            return [], (kv_cache or [])

        seq_len = len(tokens)
        cfg = self.config
        d = cfg.d_model
        h = cfg.n_heads
        kv_h = cfg.n_kv_heads
        head_dim = d // h
        group_size = h // kv_h

        # Initialize KV Cache structure if not provided
        if kv_cache is None:
            updated_cache = [{"k": [], "v": []} for _ in range(cfg.n_layers)]
            start_pos = 0
        else:
            updated_cache = kv_cache
            start_pos = len(kv_cache[0]["k"])

        # 1. Embeddings lookup: [seq_len, d_model]
        hidden_states = [list(self.embeddings[min(t, cfg.vocab_size - 1)]) for t in tokens]

        # 2. Iterate through Transformer Blocks
        for layer_idx, block in enumerate(self.layers):
            layer_cache = updated_cache[layer_idx]
            new_hidden: List[List[float]] = []

            # Process token by token (or sequence with causal masking)
            for t_idx, x in enumerate(hidden_states):
                pos = start_pos + t_idx

                # Attention Norm
                norm_x = _rmsnorm(x, block.attn_norm, cfg.norm_eps)

                # Project Q, K, V
                q = _mat_vec_mul(block.wq, norm_x)
                k = _mat_vec_mul(block.wk, norm_x)
                v = _mat_vec_mul(block.wv, norm_x)

                # Apply RoPE per head
                q_heads = []
                for head in range(h):
                    start = head * head_dim
                    end = start + head_dim
                    q_heads.append(_apply_rope(q[start:end], pos, cfg.rope_theta))

                k_heads = []
                for kv_head in range(kv_h):
                    start = kv_head * head_dim
                    end = start + head_dim
                    k_heads.append(_apply_rope(k[start:end], pos, cfg.rope_theta))

                v_heads = []
                for kv_head in range(kv_h):
                    start = kv_head * head_dim
                    end = start + head_dim
                    v_heads.append(v[start:end])

                # Append to KV cache for current layer
                layer_cache["k"].append(k_heads)
                layer_cache["v"].append(v_heads)

                # Total key/value positions available for attention (causal history up to pos)
                total_k = layer_cache["k"][: pos + 1]
                total_v = layer_cache["v"][: pos + 1]
                hist_len = len(total_k)

                # Compute GQA Attention output for all Q heads
                attn_out = [0.0] * d
                inv_sqrt_d = 1.0 / math.sqrt(head_dim)

                for head in range(h):
                    kv_head = head // group_size
                    q_vec = q_heads[head]

                    # Dot product attention scores against all keys up to pos
                    scores = []
                    for p in range(hist_len):
                        k_vec = total_k[p][kv_head]
                        dot = sum(q_vec[i] * k_vec[i] for i in range(head_dim)) * inv_sqrt_d
                        scores.append(dot)

                    # Softmax
                    max_s = max(scores) if scores else 0.0
                    exp_s = [math.exp(s - max_s) for s in scores]
                    sum_exp = sum(exp_s) or 1.0
                    weights = [e / sum_exp for e in exp_s]

                    # Weighted sum of values
                    head_out = [0.0] * head_dim
                    for p in range(hist_len):
                        w = weights[p]
                        v_vec = total_v[p][kv_head]
                        for i in range(head_dim):
                            head_out[i] += w * v_vec[i]

                    # Pack into attention vector
                    start = head * head_dim
                    for i in range(head_dim):
                        attn_out[start + i] = head_out[i]

                # Project out & add residual
                proj_attn = _mat_vec_mul(block.wo, attn_out)
                x_after_attn = [x[i] + proj_attn[i] for i in range(d)]

                # FFN Norm
                norm_ffn_x = _rmsnorm(x_after_attn, block.ffn_norm, cfg.norm_eps)

                # SwiGLU: (swish(x @ W_gate)) * (x @ W_up) @ W_down
                gate = _mat_vec_mul(block.w_gate, norm_ffn_x)
                up = _mat_vec_mul(block.w_up, norm_ffn_x)
                swiglu = []
                for g, u in zip(gate, up):
                    # Swish(g) = g * sigmoid(g)
                    sig = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, g))))
                    swiglu.append((g * sig) * u)

                ffn_out = _mat_vec_mul(block.w_down, swiglu)
                x_out = [x_after_attn[i] + ffn_out[i] for i in range(d)]
                new_hidden.append(x_out)

            hidden_states = new_hidden

        # 3. Final RMSNorm
        final_normed = [_rmsnorm(x, self.norm, cfg.norm_eps) for x in hidden_states]

        # 4. Project to vocabulary logits: [seq_len, vocab_size]
        logits = [_mat_vec_mul(self.lm_head, x) for x in final_normed]

        return logits, updated_cache
