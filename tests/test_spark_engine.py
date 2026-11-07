#!/usr/bin/env python3
"""
Unit tests for Apex Sovereign Spark Engine.
Validates RDD Lineage DAG, Wide/Narrow dependencies, Catalyst Optimizer, DataFrame API, and SparkGuard AppSec/OOM auditor.
"""

import os
import tempfile
import unittest
from pathlib import Path

from apex_council.spark.engine import (
    CatalystOptimizer,
    DataFrame,
    DependencyType,
    RDD,
    SparkContext,
    SparkGuard,
    SparkSession,
    StructField,
    StructType,
    handle_spark_cli,
)


class TestSparkEngine(unittest.TestCase):
    def setUp(self):
        self.sc = SparkContext(appName="TestSparkApp", master="local[2]")
        self.spark = SparkSession("TestSparkSession")

    def test_rdd_narrow_transformations(self):
        data = [1, 2, 3, 4, 5]
        rdd = self.sc.parallelize(data, numSlices=2)

        # map
        doubled = rdd.map(lambda x: x * 2).collect()
        self.assertEqual(doubled, [2, 4, 6, 8, 10])

        # filter
        evens = rdd.filter(lambda x: x % 2 == 0).collect()
        self.assertEqual(evens, [2, 4])

        # flatMap
        words_rdd = self.sc.parallelize(["hello world", "apex spark"])
        words = words_rdd.flatMap(lambda s: s.split()).collect()
        self.assertEqual(words, ["hello", "world", "apex", "spark"])

    def test_rdd_actions(self):
        data = [10, 20, 30, 40]
        rdd = self.sc.parallelize(data, numSlices=2)

        self.assertEqual(rdd.count(), 4)
        self.assertEqual(rdd.first(), 10)
        self.assertEqual(rdd.take(2), [10, 20])
        self.assertEqual(rdd.reduce(lambda a, b: a + b), 100)

        # Empty reduce raises ValueError
        empty_rdd = self.sc.parallelize([])
        with self.assertRaises(ValueError):
            empty_rdd.reduce(lambda a, b: a + b)

    def test_rdd_wide_pair_transformations(self):
        # Word count via reduceByKey
        text = ["spark", "apex", "spark", "rdd", "apex", "spark"]
        pairs = self.sc.parallelize(text).map(lambda w: (w, 1))
        counts = dict(pairs.reduceByKey(lambda a, b: a + b).collect())

        self.assertEqual(counts["spark"], 3)
        self.assertEqual(counts["apex"], 2)
        self.assertEqual(counts["rdd"], 1)

        # groupByKey
        grouped = dict(pairs.groupByKey().collect())
        self.assertEqual(len(grouped["spark"]), 3)

        # distinct
        distinct_words = sorted(self.sc.parallelize(text).distinct().collect())
        self.assertEqual(distinct_words, ["apex", "rdd", "spark"])

        # sortBy
        nums = self.sc.parallelize([5, 1, 9, 3])
        sorted_asc = nums.sortBy(lambda x: x, ascending=True).collect()
        self.assertEqual(sorted_asc, [1, 3, 5, 9])
        sorted_desc = nums.sortBy(lambda x: x, ascending=False).collect()
        self.assertEqual(sorted_desc, [9, 5, 3, 1])

        # join
        users = self.sc.parallelize([(1, "Alice"), (2, "Bob")])
        orders = self.sc.parallelize([(1, "Laptop"), (2, "Phone"), (1, "Mouse")])
        joined = users.join(orders).collect()
        self.assertEqual(len(joined), 3)

    def test_rdd_lineage_dag(self):
        rdd = self.sc.parallelize([1, 2, 3]).map(lambda x: x + 1).filter(lambda x: x > 2)
        debug_str = rdd.toDebugString()
        self.assertIn("FilteredRDD", debug_str)
        self.assertIn("MapPartitionsRDD", debug_str)
        self.assertIn(DependencyType.NARROW, debug_str)

    def test_catalyst_optimizer_and_dataframe(self):
        records = [
            {"id": 1, "name": "Aditi", "age": 28, "salary": 90000},
            {"id": 2, "name": "Raghav", "age": 24, "salary": 85000},
            {"id": 3, "name": "Kabir", "age": 19, "salary": 45000},
        ]
        df = self.spark.createDataFrame(records)
        self.assertEqual(df.count(), 3)

        # Filter and select
        filtered = df.filter("age >= 21").select("name", "salary")
        self.assertEqual(filtered.count(), 2)
        rows = filtered.rows
        names = [r["name"] for r in rows]
        self.assertIn("Aditi", names)
        self.assertIn("Raghav", names)
        self.assertNotIn("Kabir", names)

        # Explain output validation
        plan_str = filtered.explain()
        self.assertIn("== Parsed Logical Plan ==", plan_str)
        self.assertIn("== Optimized Logical Plan (Catalyst) ==", plan_str)
        self.assertIn("== Physical Execution Plan ==", plan_str)

    def test_sparkguard_auditor(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_code = """
import pyspark.sql.functions as F

def run_job(spark, df):
    # Driver OOM anti-pattern
    records = df.collect()

    # Shuffle explosion anti-pattern
    rdd = df.rdd.map(lambda r: (r.dept, r.salary)).groupByKey()

    # SQL Injection risk
    user_input = "1 OR 1=1"
    spark.sql(f"SELECT * FROM users WHERE id = {user_input}")
"""
            test_file = Path(tmpdir) / "pipeline.py"
            test_file.write_text(bad_code, encoding="utf-8")

            guard = SparkGuard(tmpdir)
            findings = guard.audit()

            rule_ids = {f.rule_id for f in findings}
            self.assertIn("SPARK001", rule_ids)  # Driver OOM
            self.assertIn("SPARK002", rule_ids)  # Shuffle explosion
            self.assertIn("SPARK003", rule_ids)  # SQL Injection

            report = guard.render_terminal()
            self.assertIn("APEX SOVEREIGN APACHE SPARK DEFENSIVE PERFORMANCE", report)
            self.assertIn("SPARK001", report)

    def test_handle_spark_cli(self):
        # Demo execution
        ret = handle_spark_cli(["demo"])
        self.assertEqual(ret, 0)

        # Audit execution on empty directory
        with tempfile.TemporaryDirectory() as tmpdir:
            ret = handle_spark_cli(["audit", tmpdir])
            self.assertEqual(ret, 0)


if __name__ == "__main__":
    unittest.main()
