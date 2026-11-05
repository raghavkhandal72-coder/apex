#!/usr/bin/env python3
"""
Apex-Sovereign: Transformer Architectural Configuration
100% Pure Python Standard Library | Zero Dependencies
"""

from __future__ import annotations

import dataclasses


@dataclasses.dataclass
class TransformerConfig:
    vocab_size: int = 280
    d_model: int = 32
    n_layers: int = 2
    n_heads: int = 4
    n_kv_heads: int = 2
    d_ff: int = 64
    max_seq_len: int = 32
    rope_theta: float = 10000.0
    norm_eps: float = 1e-5
