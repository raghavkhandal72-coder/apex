#!/usr/bin/env python3
"""
Apex-Sovereign: MLflow Native File-Store Experiment Tracker
100% Pure Python Standard Library | Zero Dependencies | Compatible with `mlflow ui`

Writes experiment runs, metrics, parameters, tags, and artifacts directly into the
standard `mlruns/` directory layout so any standard MLflow Server or Databricks workspace
can visualize Apex-Sovereign agent telemetry out-of-the-box.
"""

from __future__ import annotations

import dataclasses
import os
import pathlib
import secrets
import time
from typing import Any, Dict, List, Optional


@dataclasses.dataclass(frozen=True)
class RunMetadata:
    run_id: str
    experiment_id: str
    run_name: str
    status: str
    start_time: int
    end_time: Optional[int] = None
    artifact_uri: str = ""


class MLflowExperimentTracker:
    """
    Manages local MLflow tracking file-store under `mlruns/`.
    Generates standard YAML and metric files readable by `mlflow ui`.
    """

    def __init__(self, tracking_dir: str | pathlib.Path = "mlruns") -> None:
        self.tracking_dir = pathlib.Path(tracking_dir).resolve()
        self.tracking_dir.mkdir(parents=True, exist_ok=True)
        self.active_run: Optional[RunMetadata] = None

    def start_run(
        self,
        experiment_id: str = "0",
        run_name: str = "apex_swarm_run",
    ) -> RunMetadata:
        """Initializes a new MLflow tracking run directory."""
        run_id = secrets.token_hex(16)
        exp_dir = self.tracking_dir / experiment_id
        exp_dir.mkdir(parents=True, exist_ok=True)

        # Create experiment meta.yaml if missing
        exp_meta = exp_dir / "meta.yaml"
        if not exp_meta.exists():
            exp_meta.write_text(
                f"artifact_location: {exp_dir.as_uri()}\n"
                f"creation_time: {int(time.time() * 1000)}\n"
                f"experiment_id: '{experiment_id}'\n"
                f"last_update_time: {int(time.time() * 1000)}\n"
                f"lifecycle_stage: active\n"
                f"name: Default\n",
                encoding="utf-8",
            )

        run_dir = exp_dir / run_id
        (run_dir / "metrics").mkdir(parents=True, exist_ok=True)
        (run_dir / "params").mkdir(parents=True, exist_ok=True)
        (run_dir / "tags").mkdir(parents=True, exist_ok=True)
        (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)

        now_ms = int(time.time() * 1000)
        meta_yaml = (
            f"artifact_uri: {(run_dir / 'artifacts').as_uri()}\n"
            f"end_time: null\n"
            f"entry_point_name: ''\n"
            f"experiment_id: '{experiment_id}'\n"
            f"lifecycle_stage: active\n"
            f"run_id: {run_id}\n"
            f"run_name: {run_name}\n"
            f"run_uuid: {run_id}\n"
            f"source_name: ''\n"
            f"source_type: 4\n"
            f"source_version: ''\n"
            f"start_time: {now_ms}\n"
            f"status: 1\n"
            f"user_id: apex_sovereign\n"
        )
        (run_dir / "meta.yaml").write_text(meta_yaml, encoding="utf-8")

        self.active_run = RunMetadata(
            run_id=run_id,
            experiment_id=experiment_id,
            run_name=run_name,
            status="RUNNING",
            start_time=now_ms,
            artifact_uri=str(run_dir / "artifacts"),
        )
        return self.active_run

    def log_param(self, key: str, value: Any) -> None:
        """Logs a single parameter to the active run."""
        if not self.active_run:
            raise RuntimeError("No active MLflow run. Call start_run() first.")
        run_dir = self.tracking_dir / self.active_run.experiment_id / self.active_run.run_id
        param_file = run_dir / "params" / key
        param_file.write_text(str(value), encoding="utf-8")

    def log_metric(self, key: str, value: float, step: int = 0) -> None:
        """Logs a numeric metric point (timestamp, value, step) to the active run."""
        if not self.active_run:
            raise RuntimeError("No active MLflow run. Call start_run() first.")
        run_dir = self.tracking_dir / self.active_run.experiment_id / self.active_run.run_id
        metric_file = run_dir / "metrics" / key
        now_ms = int(time.time() * 1000)
        with open(metric_file, "a", encoding="utf-8") as f:
            f.write(f"{now_ms} {value} {step}\n")

    def log_tag(self, key: str, value: str) -> None:
        """Logs a string tag to the active run."""
        if not self.active_run:
            raise RuntimeError("No active MLflow run. Call start_run() first.")
        run_dir = self.tracking_dir / self.active_run.experiment_id / self.active_run.run_id
        tag_file = run_dir / "tags" / key
        tag_file.write_text(value, encoding="utf-8")

    def log_artifact(self, file_path: str | pathlib.Path, artifact_path: Optional[str] = None) -> None:
        """Copies an artifact (trace, code diff, report) to the run's artifact directory."""
        if not self.active_run:
            raise RuntimeError("No active MLflow run. Call start_run() first.")
        src = pathlib.Path(file_path).resolve()
        if not src.exists():
            return
        dest_dir = pathlib.Path(self.active_run.artifact_uri)
        if artifact_path:
            dest_dir = dest_dir / artifact_path
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / src.name
        dest_file.write_bytes(src.read_bytes())

    def end_run(self, status: str = "FINISHED") -> None:
        """Marks the active run as FINISHED or FAILED and records end timestamp."""
        if not self.active_run:
            return
        run_dir = self.tracking_dir / self.active_run.experiment_id / self.active_run.run_id
        meta_file = run_dir / "meta.yaml"
        if meta_file.exists():
            now_ms = int(time.time() * 1000)
            content = meta_file.read_text(encoding="utf-8")
            content = content.replace("end_time: null", f"end_time: {now_ms}")
            code = 3 if status == "FINISHED" else 4
            content = content.replace("status: 1", f"status: {code}")
            meta_file.write_text(content, encoding="utf-8")
        self.active_run = None
