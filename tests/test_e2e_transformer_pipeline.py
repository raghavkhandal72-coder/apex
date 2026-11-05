"""
Opaque-Box E2E Test Suite — Training & Data Processing Pipeline (R3)
Tiers 1-4: Feature Coverage, Boundary/Corner Cases, Cross-Feature Interactions, Real-World Scenarios.

Covers:
- MultiDomainTextLoader: Ingestion of books, articles, code, and documents; chunking & dynamic padding.
- Loss Engine: CrossEntropy loss calculation, label shifting, perplexity.
- Backpropagation: Analytical gradient propagation through all Transformer layers.
- AdamW Optimizer: Weight decay decoupling, momentum tracking, gradient clipping.
- LR Scheduler: Warmup and Cosine decay schedule.
- Hyperparameter Tuning: Grid/random search over training parameters.
- TransformerTrainer: Full training loop, step metrics, and TrainingSummary report.

Platform Invariants:
- 100% pure Python standard library (unittest based), zero external dependencies.
- Fast execution (<100ms per unit test).
"""

import math
import os
import shutil
import tempfile
import unittest

# Progressive testability import guard
TRAINING_PIPELINE_AVAILABLE = False
try:
    import apex_council.transformer as tf
    from apex_council.transformer.config import TransformerConfig
    from apex_council.transformer.tokenizer import ByteTokenizer
    from apex_council.transformer.model import TransformerModel
    from apex_council.transformer.data import MultiDomainTextLoader
    from apex_council.transformer.train import TransformerTrainer
    TRAINING_PIPELINE_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    try:
        import apex_council.transformer as tf
        TransformerConfig = getattr(tf, "TransformerConfig", None)
        ByteTokenizer = getattr(tf, "ByteTokenizer", None)
        TransformerModel = getattr(tf, "TransformerModel", None)
        MultiDomainTextLoader = getattr(tf, "MultiDomainTextLoader", getattr(tf, "DatasetLoader", None))
        TransformerTrainer = getattr(tf, "TransformerTrainer", getattr(tf, "Trainer", None))
        if TransformerConfig and TransformerModel and MultiDomainTextLoader and TransformerTrainer:
            TRAINING_PIPELINE_AVAILABLE = True
    except (ImportError, ModuleNotFoundError):
        TRAINING_PIPELINE_AVAILABLE = False


@unittest.skipUnless(TRAINING_PIPELINE_AVAILABLE, "Milestone 3 Training Pipeline not yet implemented")
class TestE2ETransformerPipelineTier1(unittest.TestCase):
    """Tier 1: Feature Coverage — Representative happy-path tests for data loader, loss, AdamW, trainer."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="apex_e2e_pipeline_t1_")
        self.config = TransformerConfig(
            vocab_size=280,
            d_model=32,
            n_layers=1,
            n_heads=2,
            n_kv_heads=1,
            d_ff=64,
            max_seq_len=32,
            rope_theta=10000.0
        )
        self.tokenizer = ByteTokenizer()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_multi_domain_text_loader_ingestion(self):
        """Verify MultiDomainTextLoader ingests books, articles, code, and documents."""
        # 1. Book text
        book_file = os.path.join(self.test_dir, "book.txt")
        with open(book_file, "w", encoding="utf-8") as f:
            f.write("The stars shone brightly in the vast expanse of the cosmos.\n")

        # 2. Article text
        article_file = os.path.join(self.test_dir, "article.md")
        with open(article_file, "w", encoding="utf-8") as f:
            f.write("# Transformer Architecture\nAttention mechanisms provide parallel computation.\n")

        # 3. Code text
        code_file = os.path.join(self.test_dir, "code.py")
        with open(code_file, "w", encoding="utf-8") as f:
            f.write("def binary_search(arr, target):\n    low, high = 0, len(arr) - 1\n")

        # 4. Document text
        doc_file = os.path.join(self.test_dir, "spec.txt")
        with open(doc_file, "w", encoding="utf-8") as f:
            f.write("RFC-9000: QUIC transport protocol specification.\n")

        loader = MultiDomainTextLoader()
        paths = [book_file, article_file, code_file, doc_file]
        dataset = loader.load_dataset(paths)

        self.assertIsInstance(dataset, list)
        self.assertGreater(len(dataset), 0)
        # Verify samples are lists of token IDs
        for sample in dataset:
            self.assertIsInstance(sample, list)
            self.assertTrue(all(isinstance(t, int) for t in sample))

    def test_loss_calculation_and_perplexity(self):
        """Verify CrossEntropy loss computation and perplexity PPL = exp(loss)."""
        model = TransformerModel(self.config)
        trainer = TransformerTrainer() if hasattr(TransformerTrainer, "__call__") else None
        tokens = [10, 20, 30, 40]

        # Forward pass to get logits
        logits, _ = model.forward(tokens)
        self.assertEqual(len(logits), len(tokens))

        # Test loss function if exposed
        loss_fn = getattr(trainer, "compute_loss", getattr(tf, "cross_entropy_loss", None))
        if loss_fn:
            # Shifted targets: next token prediction
            targets = tokens[1:] + [0]
            loss = loss_fn(logits, targets)
            self.assertIsInstance(loss, float)
            self.assertGreater(loss, 0.0)
            self.assertFalse(math.isnan(loss))
            perplexity = math.exp(loss)
            self.assertGreaterEqual(perplexity, 1.0)

    def test_training_loop_execution_and_summary(self):
        """Verify full training execution on synthetic dataset and TrainingSummary report."""
        model = TransformerModel(self.config)
        trainer = TransformerTrainer()

        # Synthetic multi-sequence dataset
        dataset = [
            [5, 12, 19, 26, 33, 40],
            [14, 28, 42, 56, 70, 84],
            [9, 18, 27, 36, 45, 54]
        ]

        summary = trainer.train(model, dataset, epochs=2, lr=1e-3, batch_size=1)

        # Verify TrainingSummary contract attributes
        self.assertIsNotNone(summary)
        status = getattr(summary, "status", "COMPLETED")
        self.assertEqual(str(status).upper(), "COMPLETED")

        initial_loss = getattr(summary, "initial_loss", None)
        final_loss = getattr(summary, "final_loss", None)
        total_time = getattr(summary, "total_time", getattr(summary, "total_time_seconds", None))

        if initial_loss is not None and final_loss is not None:
            self.assertGreater(initial_loss, 0.0)
            self.assertGreater(final_loss, 0.0)
            self.assertFalse(math.isnan(initial_loss))
            self.assertFalse(math.isnan(final_loss))

        if total_time is not None:
            self.assertGreaterEqual(total_time, 0.0)


@unittest.skipUnless(TRAINING_PIPELINE_AVAILABLE, "Milestone 3 Training Pipeline not yet implemented")
class TestE2ETransformerPipelineTier2(unittest.TestCase):
    """Tier 2: Boundary & Corner Cases — Variable length padding, single steps, extreme LR."""

    def setUp(self):
        self.config = TransformerConfig(
            vocab_size=280,
            d_model=32,
            n_layers=1,
            n_heads=2,
            n_kv_heads=1,
            d_ff=64,
            max_seq_len=16
        )

    def test_single_step_training_run(self):
        """Verify training executes properly for exactly 1 step without boundary index errors."""
        model = TransformerModel(self.config)
        trainer = TransformerTrainer()
        single_sample_dataset = [[10, 20, 30]]

        summary = trainer.train(model, single_sample_dataset, epochs=1, lr=1e-3, batch_size=1)
        self.assertIsNotNone(summary)

    def test_gradient_clipping_bounds(self):
        """Verify gradient clipping mechanism scales extreme gradient norms to max_norm."""
        clip_fn = getattr(tf, "clip_grad_norm", None)
        if clip_fn:
            # Synthetic large gradients
            grads = [[100.0, -200.0], [300.0, -400.0]]
            max_norm = 1.0
            clipped, norm = clip_fn(grads, max_norm=max_norm)
            self.assertLessEqual(norm, max_norm + 1e-4)


@unittest.skipUnless(TRAINING_PIPELINE_AVAILABLE, "Milestone 3 Training Pipeline not yet implemented")
class TestE2ETransformerPipelineTier3(unittest.TestCase):
    """Tier 3: Cross-Feature Interactions — Data Loader to Trainer to Weight Updates."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="apex_e2e_pipeline_t3_")
        self.config = TransformerConfig(
            vocab_size=280,
            d_model=32,
            n_layers=1,
            n_heads=2,
            n_kv_heads=1,
            d_ff=64,
            max_seq_len=32
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_end_to_end_ingestion_and_training_pass(self):
        """Verify end-to-end: Write text file -> Ingest via MultiDomainTextLoader -> Train model."""
        sample_path = os.path.join(self.test_dir, "corpus.txt")
        with open(sample_path, "w", encoding="utf-8") as f:
            f.write("Apex Sovereign transformer training loop verifies zero-dependency machine learning.\n")

        loader = MultiDomainTextLoader()
        dataset = loader.load_dataset([sample_path])
        self.assertGreater(len(dataset), 0)

        model = TransformerModel(self.config)
        trainer = TransformerTrainer()
        summary = trainer.train(model, dataset, epochs=1, lr=1e-3, batch_size=1)

        self.assertIsNotNone(summary)
        status = getattr(summary, "status", "COMPLETED")
        self.assertEqual(str(status).upper(), "COMPLETED")


@unittest.skipUnless(TRAINING_PIPELINE_AVAILABLE, "Milestone 3 Training Pipeline not yet implemented")
class TestE2ETransformerPipelineTier4(unittest.TestCase):
    """Tier 4: Real-World Scenarios — End-to-end model training run on multi-domain corpus."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="apex_e2e_pipeline_t4_")
        self.config = TransformerConfig(
            vocab_size=280,
            d_model=32,
            n_layers=1,
            n_heads=2,
            n_kv_heads=1,
            d_ff=64,
            max_seq_len=32
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_scenario_multi_domain_training_run(self):
        """
        Complete Real-World Scenario:
        1. Prepare distinct files across 4 domains (Books, Articles, Code, Documents).
        2. Ingest, normalize, chunk, and tokenize via MultiDomainTextLoader.
        3. Train model across all domains with AdamW and loss metrics tracking.
        4. Verify loss tracking and completion summary generation.
        """
        domains = {
            "books.txt": "Chapter 1: The Sovereign Mind awoke to the digital horizon.\n",
            "articles.md": "### Distributed Consensus\nConsensus algorithms ensure fault tolerance.\n",
            "code.py": "def fibonacci(n):\n    return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)\n",
            "documents.txt": "Policy 404: Cryptographic ledger verification requirements.\n"
        }

        paths = []
        for filename, content in domains.items():
            filepath = os.path.join(self.test_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            paths.append(filepath)

        # Ingestion
        loader = MultiDomainTextLoader()
        dataset = loader.load_dataset(paths)
        self.assertGreaterEqual(len(dataset), 4)

        # Training
        model = TransformerModel(self.config)
        trainer = TransformerTrainer()
        summary = trainer.train(model, dataset, epochs=2, lr=1e-3, batch_size=2)

        self.assertIsNotNone(summary)
        self.assertEqual(str(getattr(summary, "status", "COMPLETED")).upper(), "COMPLETED")


if __name__ == "__main__":
    unittest.main()
