#!/usr/bin/env python3
"""
Apex-Sovereign: Viral Engineering & Sovereign Frontier Suite Tests
Comprehensive Unit Tests for:
- GBrain Persistent Memory (garrytan/gbrain)
- Scrapling Resilient Web Scraping & DOM (D4Vinci/Scrapling)
- Floci AWS Local Cloud Emulator (floci-io/floci)
- VibeVoice Frontier Acoustic Synthesizer (microsoft/VibeVoice)
- Garden Skills Agent Skills Registry (ConardLi/garden-skills & google/skills)
- Guava Resilient Utilities (google/guava)
- Agent Browser Automation (vercel-labs/agent-browser)
- Electron Native Desktop Shell Bridge (electron/electron)
"""

import os
import shutil
import tempfile
import unittest
import wave

from apex_council.gbrain.brain import GBrainEngine
from apex_council.scrapling.scraper import ScraplingEngine, DOMElement
from apex_council.cloud.floci_emulator import FlociCloudEmulator
from apex_council.voice.vibe_voice import VibeVoiceSynthesizer, COUNCIL_VOICE_PROFILES
from apex_council.skills.garden_registry import GardenSkillsRegistry, GardenSkill
from apex_council.enterprise.guava_utils import (
    Preconditions,
    GuavaCache,
    RateLimiter,
    BiMap,
    Multimap,
)
from apex_council.browser.agent_browser import AgentBrowserSession
from apex_council.ui.electron_bridge import ElectronBridgeServer, generate_electron_scaffold


class TestViralSovereignSuite(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # =========================================================================
    # 1. GBrain Tests
    # =========================================================================
    def test_gbrain_lifecycle_and_locks(self):
        db_path = os.path.join(self.test_dir, "gbrain_test.db")
        brain = GBrainEngine(db_path=db_path)

        # Store facts
        f1 = brain.store_fact("arch.pattern", "Use CEGIS for invariant synthesis", source="session_1", tags="arch,formal")
        f2 = brain.store_fact("cache.policy", "Use Guava LRU cache with 60s TTL", source="session_1", tags="perf,cache")

        self.assertGreater(f1, 0)
        self.assertGreater(f2, 0)

        # Recall facts
        recalled = brain.recall_facts("CEGIS")
        self.assertEqual(len(recalled), 1)
        self.assertEqual(recalled[0].key, "arch.pattern")
        self.assertIn("CEGIS", recalled[0].text)

        # Correct fact
        ok = brain.correct_fact(f1, "Use CEGIS + MCTS for unified synthesis")
        self.assertTrue(ok)
        updated = brain.recall_facts("unified")[0]
        self.assertEqual(updated.text, "Use CEGIS + MCTS for unified synthesis")

        # Memory Locking
        lock_ok = brain.acquire_lock("global_arch", "agent_falcon")
        self.assertTrue(lock_ok)
        # Second acquire by another agent should fail
        lock_fail = brain.acquire_lock("global_arch", "agent_guardian")
        self.assertFalse(lock_fail)
        # Release lock
        brain.release_lock("global_arch", "agent_falcon")
        lock_ok2 = brain.acquire_lock("global_arch", "agent_guardian")
        self.assertTrue(lock_ok2)

        # Prompt context export
        ctx = brain.export_context_for_prompt("cache")
        self.assertIn("cache.policy", ctx)

    # =========================================================================
    # 2. Scrapling Resilient Web Scraper Tests
    # =========================================================================
    def test_scrapling_html_parsing_and_tables(self):
        sample_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Apex Test Page</title></head>
        <body>
            <h1>Apex Sovereign Launch</h1>
            <p>Welcome to the <strong>Multi-Agent</strong> Council.</p>
            <a href="https://github.com/apex-council">Apex Repo</a>
            <table>
                <tr><th>Component</th><th>Status</th></tr>
                <tr><td>MCTS Consensus</td><td>Active</td></tr>
                <tr><td>CEGIS Prover</td><td>Verified</td></tr>
            </table>
        </body>
        </html>
        """
        engine = ScraplingEngine()
        res = engine.scrape(sample_html)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.title, "Apex Test Page")
        self.assertIn("Multi-Agent Council", res.text)

        # Markdown synthesis
        md = res.html_to_markdown()
        self.assertIn("# Apex Sovereign Launch", md)
        self.assertIn("[Apex Repo](https://github.com/apex-council)", md)

        # Table extraction
        tables = res.extract_tables()
        self.assertEqual(len(tables), 1)
        self.assertEqual(len(tables[0]), 2)
        self.assertEqual(tables[0][0]["Component"], "MCTS Consensus")
        self.assertEqual(tables[0][0]["Status"], "Active")

    # =========================================================================
    # 3. Floci AWS Local Cloud Emulator Tests
    # =========================================================================
    def test_floci_s3_sqs_dynamo_emulation(self):
        floci = FlociCloudEmulator()

        # S3 Test
        floci.s3_create_bucket("sovereign-artifacts")
        obj = floci.s3_put_object("sovereign-artifacts", "models/falcon.bin", b"VECTOR_WEIGHTS_42", "application/octet-stream")
        self.assertEqual(obj.size, 17)
        retrieved = floci.s3_get_object("sovereign-artifacts", "models/falcon.bin")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.data, b"VECTOR_WEIGHTS_42")

        listing = floci.s3_list_objects("sovereign-artifacts", prefix="models/")
        self.assertEqual(len(listing), 1)

        # SQS Test
        floci.sqs_create_queue("agent-tasks")
        msg_id = floci.sqs_send_message("agent-tasks", '{"task": "audit_secrets"}')
        self.assertTrue(msg_id.startswith("msg-"))
        msgs = floci.sqs_receive_messages("agent-tasks", max_messages=1, visibility_timeout=10.0)
        self.assertEqual(len(msgs), 1)
        self.assertIn("audit_secrets", msgs[0].body)
        del_ok = floci.sqs_delete_message("agent-tasks", msgs[0].receipt_handle)
        self.assertTrue(del_ok)

        # DynamoDB Test
        floci.dynamo_create_table("UserLedger", primary_key="user_id")
        floci.dynamo_put_item("UserLedger", {"user_id": "usr_99", "tier": "sovereign", "credits": 5000})
        item = floci.dynamo_get_item("UserLedger", "usr_99")
        self.assertIsNotNone(item)
        self.assertEqual(item["credits"], 5000)

        # Stats
        stats = floci.get_cloud_stats()
        self.assertEqual(stats["s3_buckets_count"], 1)
        self.assertEqual(stats["dynamodb_tables_count"], 1)

    # =========================================================================
    # 4. VibeVoice Acoustic Audio Tests
    # =========================================================================
    def test_vibevoice_synthesis_and_wav_generation(self):
        synth = VibeVoiceSynthesizer(sample_rate=22050)
        wav_path = os.path.join(self.test_dir, "falcon_speech.wav")

        raw_bytes, path = synth.synthesize_speech(
            text="Council consensus achieved. Deploying sovereign wave.",
            profile_name="falcon",
            output_wav_path=wav_path,
        )
        self.assertTrue(os.path.isfile(path))
        self.assertGreater(len(raw_bytes), 1000)

        # Verify WAV headers
        with wave.open(path, "rb") as wf:
            self.assertEqual(wf.getnchannels(), 1)
            self.assertEqual(wf.getsampwidth(), 2)  # 16-bit
            self.assertEqual(wf.getframerate(), 22050)
            frames = wf.getnframes()
            self.assertGreater(frames, 5000)

        # ASCII Waveform
        ascii_wave = synth.render_ascii_waveform([0, 1000, 15000, 32000, 5000], width=10)
        self.assertGreater(len(ascii_wave), 0)

    # =========================================================================
    # 5. Garden Skills Registry Tests
    # =========================================================================
    def test_garden_skills_registry_and_parsing(self):
        reg = GardenSkillsRegistry()
        skills = reg.list_skills()
        self.assertGreaterEqual(len(skills), 5)

        # Test SKILL.md parsing
        skill_md = """---
name: custom-verifier
description: Verify invariant boundaries against hostile fuzzing.
author: Security Team
version: 2.1.0
tags: [fuzz, verifier, safety]
---
# Invariant Verifier Agent
Please execute rigorous property-based checking against target model.
"""
        parsed = reg.parse_skill_md(skill_md)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.name, "custom-verifier")
        self.assertIn("fuzz", parsed.tags)

        # Register and execute
        reg.register(parsed)
        exec_res = reg.execute_skill("custom-verifier", target_model="KVStore", trials=500)
        self.assertTrue(exec_res["success"])
        self.assertIn("target_model", exec_res["compiled_prompt"])

    # =========================================================================
    # 6. Guava Resilient Utilities Tests
    # =========================================================================
    def test_guava_cache_preconditions_and_structures(self):
        # Preconditions
        Preconditions.check_argument(10 > 5, "Should not raise")
        with self.assertRaises(ValueError):
            Preconditions.check_argument(2 > 5, "Math failed")

        with self.assertRaises(ValueError):
            Preconditions.check_not_null(None, "Cannot be null")

        # GuavaCache (LRU + TTL)
        cache = GuavaCache(max_size=3, expire_after_write_s=10.0)
        cache.put("k1", "v1")
        cache.put("k2", "v2")
        cache.put("k3", "v3")
        self.assertEqual(cache.get("k1"), "v1")

        # Insert 4th element -> LRU eviction of least recently accessed (k2)
        cache.put("k4", "v4")
        self.assertIsNone(cache.get("k2"))
        self.assertEqual(cache.get("k4"), "v4")
        self.assertEqual(cache.stats().eviction_count, 1)

        # RateLimiter
        limiter = RateLimiter(permits_per_second=100.0)
        self.assertTrue(limiter.try_acquire(1))

        # BiMap
        bimap = BiMap[str, int]()
        bimap.put("one", 1)
        bimap.put("two", 2)
        self.assertEqual(bimap.get("one"), 1)
        self.assertEqual(bimap.get_by_value(2), "two")
        with self.assertRaises(ValueError):
            bimap.put("uno", 1)  # Value 1 already bound

        bimap.force_put("uno", 1)
        self.assertEqual(bimap.get_by_value(1), "uno")

        # Multimap
        mmap = Multimap[str, str]()
        mmap.put("agent", "falcon")
        mmap.put("agent", "guardian")
        mmap.put("agent", "aegis")
        self.assertEqual(len(mmap.get("agent")), 3)
        self.assertEqual(mmap.size(), 3)

    # =========================================================================
    # 7. Agent Browser Automation Tests
    # =========================================================================
    def test_agent_browser_snapshot_and_interaction(self):
        html = """
        <html>
        <head><title>Apex Portal</title></head>
        <body>
            <h1>Sovereign Dashboard</h1>
            <p>Welcome to the agent command terminal.</p>
            <input type="text" name="query" value="" placeholder="Enter agent goal" />
            <button id="btn-submit">Dispatch Wave</button>
            <a href="https://apex.ai/docs">Documentation</a>
        </body>
        </html>
        """
        browser = AgentBrowserSession()
        res = browser.goto("https://apex.local", mock_html=html)
        self.assertEqual(res["status"], 200)

        # Snapshot with [@ref:ID]
        snapshot = browser.snapshot()
        self.assertIn("[@ref:", snapshot)
        self.assertIn("<button>", snapshot)
        self.assertIn("<input>", snapshot)

        # Find input ref and type
        input_ref = None
        button_ref = None
        for ref_id, node in browser.nodes_by_ref.items():
            if node.tag == "input":
                input_ref = ref_id
            elif node.tag == "button":
                button_ref = ref_id

        self.assertIsNotNone(input_ref)
        self.assertIsNotNone(button_ref)

        # Type text into element
        type_res = browser.type_text(input_ref, "Autonomous Task 42")
        self.assertTrue(type_res["success"])
        self.assertEqual(browser.nodes_by_ref[input_ref].attrs["value"], "Autonomous Task 42")

        # Click button
        click_res = browser.click(button_ref)
        self.assertTrue(click_res["success"])

        # Viewport rendering
        viewport = browser.render_ascii_viewport(width=50)
        self.assertIn("Apex Agent Browser", viewport)

    # =========================================================================
    # 8. Electron Bridge & Scaffold Tests
    # =========================================================================
    def test_electron_scaffold_and_bridge_rpc(self):
        scaffold_dir = os.path.join(self.test_dir, "electron_app")
        files = generate_electron_scaffold(scaffold_dir)
        self.assertEqual(len(files), 4)
        for f in files:
            self.assertTrue(os.path.isfile(f))

        # Test Bridge Server RPC dispatch
        server = ElectronBridgeServer(port=4399)
        ping_res = server.dispatch("ping", {})
        self.assertTrue(ping_res["pong"])
        self.assertEqual(ping_res["version"], "3.0.0-SOVEREIGN")

        mascot_res = server.dispatch("get_mascot", {"style": "falcon"})
        self.assertEqual(mascot_res["mascot"], "Apex Sovereign Cyber-Falcon")


if __name__ == "__main__":
    unittest.main()
