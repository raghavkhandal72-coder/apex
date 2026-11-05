#!/usr/bin/env python3
"""
Apex-Sovereign: Byte-Level Fallback Tokenizer (0% OOV for all UTF-8)
100% Pure Python Standard Library | Zero Dependencies
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple


class ByteTokenizer:
    """
    Byte-level fallback tokenizer guaranteeing 0% Out-of-Vocabulary rate
    for all UTF-8 text and custom reasoning tokens (<think>, </think>).
    """

    SPECIAL_TOKENS: Dict[str, int] = {
        "<think>": 256,
        "</think>": 257,
        "<pad>": 258,
        "<bos>": 259,
        "<eos>": 260,
    }

    REVERSE_SPECIAL: Dict[int, str] = {v: k for k, v in SPECIAL_TOKENS.items()}

    def __init__(self) -> None:
        self.vocab_size = 280

    def encode(self, text: str) -> List[int]:
        if not text:
            return []

        # Split on special tokens <think> and </think>
        pattern = r"(<think>|</think>|<pad>|<bos>|<eos>)"
        parts = re.split(pattern, text)
        tokens: List[int] = []

        for part in parts:
            if not part:
                continue
            if part in self.SPECIAL_TOKENS:
                tokens.append(self.SPECIAL_TOKENS[part])
            else:
                raw_bytes = part.encode("utf-8")
                tokens.extend(raw_bytes)

        return tokens

    def decode(self, tokens: List[int]) -> str:
        if not tokens:
            return ""

        result_parts: List[str] = []
        byte_buffer = bytearray()

        for token in tokens:
            if token in self.REVERSE_SPECIAL:
                if byte_buffer:
                    result_parts.append(byte_buffer.decode("utf-8", errors="replace"))
                    byte_buffer.clear()
                result_parts.append(self.REVERSE_SPECIAL[token])
            elif 0 <= token <= 255:
                byte_buffer.append(token)

        if byte_buffer:
            result_parts.append(byte_buffer.decode("utf-8", errors="replace"))

        return "".join(result_parts)
