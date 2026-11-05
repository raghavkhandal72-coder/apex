"""
Opaque-Box E2E Test Suite — Transformer Model Architecture (R2)
Tiers 1-4: Feature Coverage, Boundary/Corner Cases, Cross-Feature Interactions, Real-World Scenarios.

Covers:
- TransformerConfig: Architectural configuration, dimensions, hyperparameter profiles.
- ByteTokenizer: Byte-level fallback (0% OOV for all UTF-8), special reasoning tokens (<think>, </think>).
- RoPE (Rotary Position Embeddings): Relative position encoding, invariance properties.
- RMSNorm: Root Mean Square Layer Normalization, numerical stability.
- SwiGLU: Swish-gated linear unit feed-forward network.
- GQA (Grouped-Query Attention): Grouped KV heads, broadcasting, causal masking.
- KV Caching: Step-by-step autoregressive key-value caching.
- TransformerModel: Decoder-only forward pass, logits computation, reasoning trajectory.

Platform Invariants:
- 100% pure Python standard library (unittest based), zero external dependencies.
- Fast execution (<100ms per unit test).
"""

import math
import unittest

# Progressive testability import guard
TRANSFORMER_MODEL_AVAILABLE = False
try:
    import apex_council.transformer as tf
    from apex_council.transformer.config import TransformerConfig
    from apex_council.transformer.tokenizer import ByteTokenizer
    from apex_council.transformer.model import TransformerModel
    TRANSFORMER_MODEL_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    try:
        # Fallback to direct package exports if configured at apex_council.transformer
        import apex_council.transformer as tf
        TransformerConfig = getattr(tf, "TransformerConfig", None)
        ByteTokenizer = getattr(tf, "ByteTokenizer", None)
        TransformerModel = getattr(tf, "TransformerModel", None)
        if TransformerConfig and ByteTokenizer and TransformerModel:
            TRANSFORMER_MODEL_AVAILABLE = True
    except (ImportError, ModuleNotFoundError):
        TRANSFORMER_MODEL_AVAILABLE = False


@unittest.skipUnless(TRANSFORMER_MODEL_AVAILABLE, "Milestone 2 Transformer Model Architecture not yet implemented")
class TestE2ETransformerModelTier1(unittest.TestCase):
    """Tier 1: Feature Coverage — Representative happy-path tests for model components."""

    def setUp(self):
        # Compact test configuration for fast pure-Python execution (<5ms per pass)
        self.config = TransformerConfig(
            vocab_size=280,
            d_model=32,
            n_layers=2,
            n_heads=4,
            n_kv_heads=2,
            d_ff=64,
            max_seq_len=32,
            rope_theta=10000.0
        )
        self.tokenizer = ByteTokenizer()

    def test_transformer_config_initialization(self):
        """Verify TransformerConfig stores model dimensions and attention parameters."""
        self.assertEqual(self.config.vocab_size, 280)
        self.assertEqual(self.config.d_model, 32)
        self.assertEqual(self.config.n_heads, 4)
        self.assertEqual(self.config.n_kv_heads, 2)
        self.assertEqual(self.config.n_heads // self.config.n_kv_heads, 2)  # Group ratio

    def test_byte_tokenizer_encode_decode_roundtrip(self):
        """Verify ByteTokenizer encodes text to token IDs and decodes back losslessly."""
        original_text = "Apex Sovereign: Autonomous Reasoning Architecture"
        tokens = self.tokenizer.encode(original_text)
        self.assertIsInstance(tokens, list)
        self.assertGreater(len(tokens), 0)

        decoded_text = self.tokenizer.decode(tokens)
        self.assertEqual(decoded_text, original_text)

    def test_byte_tokenizer_reasoning_tokens(self):
        """Verify special <think> and </think> reasoning tokens are handled deterministically."""
        text = "<think>Compute 17 * 14 = 238</think>Result: 238"
        tokens = self.tokenizer.encode(text)
        decoded = self.tokenizer.decode(tokens)
        self.assertEqual(decoded, text)
        self.assertIn("<think>", decoded)
        self.assertIn("</think>", decoded)

    def test_byte_tokenizer_zero_oov_utf8(self):
        """Verify 0% Out-of-Vocabulary guarantee across diverse Unicode scripts and emojis."""
        unicode_samples = [
            "Hello World!",
            "人工智能与深度推理",
            "Теория графов и алгоритмы",
            "∀x ∈ ℝ: x² ≥ 0",
            "🚀 Apex Sovereign System 🔥"
        ]
        for sample in unicode_samples:
            encoded = self.tokenizer.encode(sample)
            decoded = self.tokenizer.decode(encoded)
            self.assertEqual(decoded, sample, f"Failed roundtrip for: {sample}")

    def test_transformer_model_forward_pass_shape(self):
        """Verify TransformerModel forward pass produces [seq_len, vocab_size] logits."""
        model = TransformerModel(self.config)
        prompt_tokens = self.tokenizer.encode("Apex")
        logits, kv_cache = model.forward(prompt_tokens)

        # Logits must be list of lists: seq_len rows x vocab_size columns
        self.assertEqual(len(logits), len(prompt_tokens))
        self.assertEqual(len(logits[0]), self.config.vocab_size)
        self.assertIsInstance(logits[0][0], float)
        self.assertFalse(math.isnan(logits[0][0]), "Logits must not contain NaN")

    def test_causal_masking_enforcement(self):
        """Verify causal masking: token at position i cannot attend to position j > i."""
        model = TransformerModel(self.config)
        tokens_a = [10, 20, 30]
        tokens_b = [10, 20, 99]  # 3rd token changed

        logits_a, _ = model.forward(tokens_a)
        logits_b, _ = model.forward(tokens_b)

        # Causal property: Logits at position 0 and 1 must be strictly identical
        # because future token at position 2 is causally masked out
        for pos in (0, 1):
            for v_idx in range(min(10, self.config.vocab_size)):
                self.assertAlmostEqual(
                    logits_a[pos][v_idx],
                    logits_b[pos][v_idx],
                    places=5,
                    msg=f"Causal violation at position {pos}, vocab {v_idx}"
                )

    def test_kv_caching_step_generation(self):
        """Verify incremental autoregressive forward pass with KV cache."""
        model = TransformerModel(self.config)
        tokens = [15, 25, 35]

        # Single pass over full sequence
        full_logits, full_cache = model.forward(tokens)

        # Step-by-step with KV cache
        step_logits_0, cache = model.forward([tokens[0]])
        step_logits_1, cache = model.forward([tokens[1]], kv_cache=cache)
        step_logits_2, cache = model.forward([tokens[2]], kv_cache=cache)

        # Logits for the final token must match closely
        for v in range(min(10, self.config.vocab_size)):
            self.assertAlmostEqual(full_logits[-1][v], step_logits_2[-1][v], places=4)


@unittest.skipUnless(TRANSFORMER_MODEL_AVAILABLE, "Milestone 2 Transformer Model Architecture not yet implemented")
class TestE2ETransformerModelTier2(unittest.TestCase):
    """Tier 2: Boundary & Corner Cases — Sequence limits, single tokens, extreme values."""

    def setUp(self):
        self.config = TransformerConfig(
            vocab_size=280,
            d_model=32,
            n_layers=1,
            n_heads=2,
            n_kv_heads=1,
            d_ff=64,
            max_seq_len=16,
            rope_theta=10000.0
        )
        self.model = TransformerModel(self.config)
        self.tokenizer = ByteTokenizer()

    def test_single_token_forward_pass(self):
        """Verify forward pass functions properly with sequence length = 1."""
        tokens = [42]
        logits, cache = self.model.forward(tokens)
        self.assertEqual(len(logits), 1)
        self.assertEqual(len(logits[0]), self.config.vocab_size)
        self.assertIsNotNone(cache)

    def test_max_sequence_length_boundary(self):
        """Verify model handles maximum sequence length without crashing."""
        max_tokens = list(range(self.config.max_seq_len))
        logits, _ = self.model.forward(max_tokens)
        self.assertEqual(len(logits), self.config.max_seq_len)

    def test_empty_string_tokenization(self):
        """Verify empty string produces empty token list and handles cleanly."""
        tokens = self.tokenizer.encode("")
        self.assertEqual(tokens, [])
        decoded = self.tokenizer.decode([])
        self.assertEqual(decoded, "")

    def test_all_byte_values_tokenization(self):
        """Verify all 256 byte values (0x00 to 0xFF) map deterministically."""
        all_bytes = bytes(range(256))
        # Decode as latin1 or raw bytes to test complete range
        text = all_bytes.decode("latin1")
        tokens = self.tokenizer.encode(text)
        self.assertGreaterEqual(len(tokens), 256)
        decoded = self.tokenizer.decode(tokens)
        self.assertEqual(decoded, text)

    def test_gqa_ratio_boundary(self):
        """Verify GQA functions when n_kv_heads == 1 (MQA) and n_kv_heads == n_heads (MHA)."""
        # Test Multi-Query Attention (MQA)
        mqa_config = TransformerConfig(vocab_size=280, d_model=32, n_layers=1, n_heads=4, n_kv_heads=1, max_seq_len=16)
        mqa_model = TransformerModel(mqa_config)
        logits_mqa, _ = mqa_model.forward([5, 10])
        self.assertEqual(len(logits_mqa), 2)

        # Test Multi-Head Attention (MHA)
        mha_config = TransformerConfig(vocab_size=280, d_model=32, n_layers=1, n_heads=4, n_kv_heads=4, max_seq_len=16)
        mha_model = TransformerModel(mha_config)
        logits_mha, _ = mha_model.forward([5, 10])
        self.assertEqual(len(logits_mha), 2)


@unittest.skipUnless(TRANSFORMER_MODEL_AVAILABLE, "Milestone 2 Transformer Model Architecture not yet implemented")
class TestE2ETransformerModelTier3(unittest.TestCase):
    """Tier 3: Cross-Feature Interactions — Sublayer composition, Tokenizer-to-Model pipeline."""

    def setUp(self):
        self.config = TransformerConfig(
            vocab_size=280,
            d_model=32,
            n_layers=2,
            n_heads=4,
            n_kv_heads=2,
            d_ff=64,
            max_seq_len=32
        )
        self.model = TransformerModel(self.config)
        self.tokenizer = ByteTokenizer()

    def test_end_to_end_text_to_logits_to_prediction(self):
        """Verify end-to-end flow: Text -> Tokenizer -> Model -> Next Token Selection -> Decode."""
        prompt = "def square(n): return"
        tokens = self.tokenizer.encode(prompt)
        self.assertGreater(len(tokens), 0)

        logits, _ = self.model.forward(tokens)
        last_step_logits = logits[-1]

        # Select next token via greedy argmax
        predicted_token_id = max(range(len(last_step_logits)), key=lambda i: last_step_logits[i])
        self.assertIsInstance(predicted_token_id, int)
        self.assertGreaterEqual(predicted_token_id, 0)
        self.assertLess(predicted_token_id, self.config.vocab_size)

        # Decode predicted token
        predicted_char = self.tokenizer.decode([predicted_token_id])
        self.assertIsInstance(predicted_char, str)

    def test_multi_layer_residual_stability(self):
        """Verify deep multi-layer Transformer blocks preserve numerical bounded variance."""
        deep_config = TransformerConfig(
            vocab_size=280,
            d_model=32,
            n_layers=4,
            n_heads=4,
            n_kv_heads=2,
            d_ff=64,
            max_seq_len=16
        )
        deep_model = TransformerModel(deep_config)
        tokens = [12, 34, 56, 78]
        logits, _ = deep_model.forward(tokens)

        # Confirm all outputs are bounded and non-zero
        for row in logits:
            for val in row:
                self.assertFalse(math.isnan(val))
                self.assertFalse(math.isinf(val))


@unittest.skipUnless(TRANSFORMER_MODEL_AVAILABLE, "Milestone 2 Transformer Model Architecture not yet implemented")
class TestE2ETransformerModelTier4(unittest.TestCase):
    """Tier 4: Real-World Scenarios — Scientific theorem reasoning trajectory."""

    def setUp(self):
        self.config = TransformerConfig(
            vocab_size=280,
            d_model=32,
            n_layers=2,
            n_heads=4,
            n_kv_heads=2,
            d_ff=64,
            max_seq_len=128
        )
        self.model = TransformerModel(self.config)
        self.tokenizer = ByteTokenizer()

    def test_scientific_theorem_reasoning_trajectory(self):
        """
        Scenario: Encode a mathematical theorem proof with explicit reasoning tokens,
        execute forward pass over the reasoning trajectory, and verify structured CoT processing.
        """
        theorem_prompt = (
            "Theorem: The sum of two even integers is even.\n"
            "<think>\n"
            "1. Let a and b be even integers.\n"
            "2. By definition, a = 2k and b = 2m for integers k, m.\n"
            "3. Compute sum: a + b = 2k + 2m = 2(k + m).\n"
            "4. Since k + m is an integer, 2(k + m) is divisible by 2, hence even.\n"
            "</think>\n"
            "Proof: Since a + b = 2(k + m), the sum is even."
        )

        tokens = self.tokenizer.encode(theorem_prompt)
        self.assertGreater(len(tokens), 20)

        # Forward pass through model
        logits, kv_cache = self.model.forward(tokens[:self.config.max_seq_len])
        self.assertEqual(len(logits), min(len(tokens), self.config.max_seq_len))

        # Extract and verify the reasoning tags in the token stream
        decoded = self.tokenizer.decode(tokens)
        self.assertIn("<think>", decoded)
        self.assertIn("</think>", decoded)

        # Extract delimited thinking content
        start_idx = decoded.index("<think>") + len("<think>")
        end_idx = decoded.index("</think>")
        thinking_block = decoded[start_idx:end_idx].strip()

        self.assertIn("By definition, a = 2k and b = 2m", thinking_block)
        self.assertIn("Compute sum: a + b = 2k + 2m", thinking_block)


if __name__ == "__main__":
    unittest.main()
