#!/usr/bin/env python3
"""
Apex-Sovereign: Multi-Domain Text Loader & Data Ingestion Pipeline
100% Pure Python Standard Library | Zero Dependencies
"""

from __future__ import annotations

import os
from typing import List, Optional

from apex_council.transformer.tokenizer import ByteTokenizer


class MultiDomainTextLoader:
    """
    Ingests books, technical articles, source code, and documents,
    tokenizing and chunking text into training sequences.
    """

    def __init__(self, tokenizer: Optional[ByteTokenizer] = None, chunk_size: int = 32) -> None:
        self.tokenizer = tokenizer or ByteTokenizer()
        self.chunk_size = chunk_size

    def load_dataset(self, paths: List[str]) -> List[List[int]]:
        """Loads and tokenizes text from multiple file paths into training sequences."""
        all_samples: List[List[int]] = []

        for p in paths:
            if not os.path.exists(p):
                continue

            if os.path.isfile(p):
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read().strip()
                if content:
                    tokens = self.tokenizer.encode(content)
                    if len(tokens) <= self.chunk_size:
                        all_samples.append(tokens)
                    else:
                        # Chunk into overlapping / contiguous sequences
                        for i in range(0, len(tokens), self.chunk_size):
                            chunk = tokens[i : i + self.chunk_size]
                            if len(chunk) >= 4:  # Minimum viable training chunk
                                all_samples.append(chunk)

            elif os.path.isdir(p):
                for root, _, files in os.walk(p):
                    for file in files:
                        full_path = os.path.join(root, file)
                        sub_samples = self.load_dataset([full_path])
                        all_samples.extend(sub_samples)

        return all_samples
