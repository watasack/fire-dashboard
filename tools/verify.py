# -*- coding: utf-8 -*-
"""
FIRE Dashboard - Verification Pipeline
=======================================
ビルド・ユニットテスト・UIテスト・スクリーンショットを順次実行し、
構造化レポートを .plans/harness/verification-report.md に出力する。

Usage:
    # 全ステージ実行（pnpm dev 起動済み前提）
    python -X utf8 tools/verify.py

    # 特定ステージのみ
    python -X utf8 tools/verify.py --stages build,unit

    # UIテスト含む全ステージ
    python -X utf8 tools/verify.py --stages build,unit,ui,screenshot
"""

import sys
import os
import subprocess
import time
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Optional

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = PROJECT_ROOT / ".plans" / "harness"
REPORT_PATH = REPORT_DIR / "verification-report.md"
DEV_SERVER_URL = os.environ.get("FIRE_URL", "http://localhost:3000")

ALL_STAGES = ["build", "unit", "ui", "screenshot"]


# ─────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────

@dataclass
class StageResult:
    name: str
    status: str  # PASS, FAIL, SKIP
    duration: float = 0.0
    details: str = ""
    failures: List[str] = field(default_factory=list)


# ─────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────

def is_dev_server_running() -> bool:
    """dev server が起動しているか HTTP プローブで確認"""
    try:
        req = urllib.request.Request(DEV_SERVER_URL, method="HEAD")
        urllib.request.urlopen(req, timeout=3)
        return True
    except (urllib.error.URLError, OSError):
        return False


def strip_ansi(text: str) -> str:
    """ANSI エスケープコードを除去"""
    import re
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def run_command(cmd: List[str], cwd: Path, timeout: int = 300) -> tuple:
    """コマンドを実行し (returncode, stdout, stderr, duration) を返す"""
    start = time.time()
    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    env["FORCE_COLOR"] = "0"
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
            shell=(sys.platform == "win32"),
            env=env,
        )
        duration = time.time() - start
        stdout = strip_ansi(result.stdout)
        stderr = strip_ansi(result.stderr)
        return result.returncode, stdout, stderr, duration
    except subprocess.TimeoutExpired:
        duration = time.time() - start
        return -1, "", f"Timeout after {timeout}s", duration


def print_stage(name: str, status: str, duration: float, details: str = ""):
    icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️"}.get(status, "❓")
    dur_str = f" ({duration:.1f}s)" if duration > 0 else ""
    detail_str = f" — {details}" if details else ""
    print(f"  {icon} {name}{dur_str}{detail_str}")


# ─────────────────────────────────────────
# Stage runners
# ─────────────────────────────────────────

def stage_build() -> StageResult:
    """Stage 1: npx next build"""
    print("\n  Building...")
    code, stdout, stderr, dur = run_command(
        ["npx", "next", "build"], PROJECT_ROOT, timeout=120
    )
    output = stdout + stderr
    if code == 0:
        return StageResult("Build", "PASS", dur)
    else:
        # Extract error lines
        errors = [
            line.strip()
            for line in output.splitlines()
            if "error" in line.lower() or "Error" in line
        ][:10]
        return StageResult("Build", "FAIL", dur, f"Exit code {code}", errors)


def stage_unit() -> StageResult:
    """Stage 2: npx vitest run"""
    print("  Running unit tests...")
    code, stdout, stderr, dur = run_command(
        ["npx", "vitest", "run"], PROJECT_ROOT, timeout=60
    )
    output = stdout + stderr

    # Parse test count from vitest output
    details = ""
    for line in output.splitlines():
        if "Tests" in line and ("passed" in line or "failed" in line):
            details = line.strip()
            break

    if code == 0:
        return StageResult("Unit Tests", "PASS", dur, details)
    else:
        failures = [
            line.strip()
            for line in output.splitlines()
            if "FAIL" in line or "AssertionError" in line or "expected" in line.lower()
        ][:10]
        return StageResult("Unit Tests", "FAIL", dur, details, failures)


def stage_ui() -> StageResult:
    """Stage 3: python -X utf8 tools/ui_test.py"""
    if not is_dev_server_running():
        return StageResult(
            "UI Tests", "SKIP", 0.0,
            f"Dev server not running at {DEV_SERVER_URL}"
        )

    print("  Running UI tests (this may take a while)...")
    code, stdout, stderr, dur = run_command(
        [sys.executable, "-X", "utf8", str(PROJECT_ROOT / "tools" / "ui_test.py")],
        PROJECT_ROOT,
        timeout=300,
    )
    output = stdout + stderr

    # Parse summary line
    details = ""
    for line in output.splitlines():
        if "テスト結果:" in line:
            details = line.strip()
            break

    if code == 0:
        return StageResult("UI Tests", "PASS", dur, details)
    else:
        # Extract failed test names
        failures = []
        in_failures = False
        for line in output.splitlines():
            if "失敗したテスト:" in line:
                in_failures = True
                continue
            if in_failures and line.strip().startswith("❌"):
                failures.append(line.strip())
        return StageResult("UI Tests", "FAIL", dur, details, failures[:10])


def stage_screenshot() -> StageResult:
    """Stage 4: python tools/take_screenshot.py"""
    if not is_dev_server_running():
        return StageResult(
            "Screenshots", "SKIP", 0.0,
            f"Dev server not running at {DEV_SERVER_URL}"
        )

    print("  Taking screenshots...")
    code, stdout, stderr, dur = run_command(
        [sys.executable, str(PROJECT_ROOT / "tools" / "take_screenshot.py")],
        PROJECT_ROOT,
        timeout=120,
    )

    if code == 0:
        return StageResult("Screenshots", "PASS", dur, "docs/screenshots/")
    else:
        return StageResult(
            "Screenshots", "FAIL", dur, f"Exit code {code}",
            [(stdout + stderr).strip()[:200]]
        )


STAGE_RUNNERS = {
    "build": stage_build,
    "unit": stage_unit,
    "ui": stage_ui,
    "screenshot": stage_screenshot,
}


# ─────────────────────────────────────────
# Report generation
# ─────────────────────────────────────────

def generate_report(results: List[StageResult]) -> str:
    """構造化 Markdown レポートを生成"""
    overall = "PASS" if all(r.status in ("PASS", "SKIP") for r in results) else "FAIL"
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    lines = [
        "# Verification Report",
        f"- **Timestamp**: {timestamp}",
        f"- **Overall**: {overall}",
        "",
        "## Stage Results",
        "| Stage | Status | Duration | Details |",
        "|-------|--------|----------|---------|",
    ]

    for r in results:
        dur_str = f"{r.duration:.1f}s" if r.duration > 0 else "—"
        detail_str = r.details if r.details else "—"
        lines.append(f"| {r.name} | {r.status} | {dur_str} | {detail_str} |")

    # Failures section
    has_failures = any(r.failures for r in results)
    if has_failures:
        lines.append("")
        lines.append("## Failures")
        for r in results:
            if r.failures:
                for f in r.failures:
                    lines.append(f"- **{r.name}**: {f}")

    lines.append("")
    return "\n".join(lines)


# ─────────────────────────────────────────
# Main
# ─────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="FIRE Dashboard verification pipeline")
    parser.add_argument(
        "--stages",
        type=str,
        default=",".join(ALL_STAGES),
        help=f"Comma-separated stages to run (default: {','.join(ALL_STAGES)})",
    )
    args = parser.parse_args()

    stages = [s.strip() for s in args.stages.split(",") if s.strip()]
    invalid = [s for s in stages if s not in STAGE_RUNNERS]
    if invalid:
        print(f"Unknown stages: {', '.join(invalid)}")
        print(f"Valid stages: {', '.join(ALL_STAGES)}")
        sys.exit(2)

    print(f"\n{'═'*60}")
    print(f"  FIRE Dashboard Verification Pipeline")
    print(f"  Stages: {', '.join(stages)}")
    print(f"{'═'*60}")

    results: List[StageResult] = []
    stop_on_fail = True

    for stage_name in stages:
        result = STAGE_RUNNERS[stage_name]()
        results.append(result)
        print_stage(result.name, result.status, result.duration, result.details)

        if result.status == "FAIL" and stop_on_fail:
            # Skip remaining stages
            remaining = stages[stages.index(stage_name) + 1 :]
            for skip_name in remaining:
                skip_result = StageResult(
                    STAGE_RUNNERS[skip_name].__doc__.split(":")[0].strip()
                    if STAGE_RUNNERS[skip_name].__doc__
                    else skip_name,
                    "SKIP",
                    details=f"Skipped (previous stage failed)",
                )
                results.append(skip_result)
                print_stage(skip_result.name, "SKIP", 0, skip_result.details)
            break

    # Summary
    overall = "PASS" if all(r.status in ("PASS", "SKIP") for r in results) else "FAIL"
    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")
    skipped = sum(1 for r in results if r.status == "SKIP")

    print(f"\n{'═'*60}")
    print(f"  Overall: {overall}  (PASS={passed}, FAIL={failed}, SKIP={skipped})")
    print(f"{'═'*60}\n")

    # Write report
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = generate_report(results)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"  Report: {REPORT_PATH}")

    sys.exit(0 if overall == "PASS" else 1)


if __name__ == "__main__":
    main()
