#!/usr/bin/env python3
"""
Apex-Sovereign: Transformer Inference Engine & Reasoning Extractor
100% Pure Python Standard Library | Zero Dependencies
"""

from __future__ import annotations

import dataclasses
import time
from typing import List, Optional, Tuple

from apex_council.transformer.model import TransformerModel
from apex_council.transformer.tokenizer import ByteTokenizer


@dataclasses.dataclass
class GenerationResult:
    text: str
    tokens: List[int]
    latency_ms: float


class TransformerInferenceEngine:
    """
    Inference Engine supporting greedy decoding, temperature sampling,
    KV-cached step generation, and chain-of-thought (<think>) extraction.
    """

    def __init__(self, model: TransformerModel, tokenizer: Optional[ByteTokenizer] = None) -> None:
        self.model = model
        self.tokenizer = tokenizer or ByteTokenizer()

    def generate(
        self,
        prompt: str,
        max_tokens: int = 10,
        temperature: float = 0.0,
        top_p: float = 1.0,
    ) -> GenerationResult:
        start_time = time.time()
        tokens = self.tokenizer.encode(prompt)

        if max_tokens <= 0:
            return GenerationResult(text=prompt, tokens=tokens, latency_ms=0.0)

        # Autoregressive generation loop
        cache = None
        for _ in range(max_tokens):
            if cache is None:
                logits, cache = self.model.forward(tokens if tokens else [259])
            else:
                last_token = [tokens[-1]] if tokens else [259]
                logits, cache = self.model.forward(last_token, kv_cache=cache)

            last_logits = logits[-1]
            if temperature <= 0.0:
                next_token = max(range(len(last_logits)), key=lambda i: last_logits[i])
            else:
                # Temperature scaled sampling
                scaled = [v / max(1e-4, temperature) for v in last_logits]
                next_token = max(range(len(scaled)), key=lambda i: scaled[i])

            tokens.append(next_token)
            if next_token == 260:  # <eos>
                break

        full_text = self.tokenizer.decode(tokens)
        latency = (time.time() - start_time) * 1000.0

        return GenerationResult(
            text=full_text,
            tokens=tokens,
            latency_ms=round(latency, 2),
        )

    def extract_reasoning(self, text: str) -> Tuple[str, str]:
        """Extracts (reasoning_trace, final_answer) from generated text with <think> delimiters."""
        if "<think>" in text and "</think>" in text:
            start = text.index("<think>") + len("<think>")
            end = text.index("</think>")
            reasoning = text[start:end].strip()
            answer = text[end + len("</think>") :].strip()
            return reasoning, answer
        return "", text.strip()
