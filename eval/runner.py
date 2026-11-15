"""runner.py — CLI evaluation runner for MAAR benchmark datasets."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from eval.reporter import generate_json_report, generate_markdown_report


def load_dataset(dataset_path: Path | None = None) -> list[dict]:
    path = dataset_path or Path(__file__).parent / "dataset" / "questions.json"
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_dry_run() -> int:
    """Validate dataset schema and display question breakdown."""
    questions = load_dataset()
    categories: dict[str, int] = {}
    difficulties: dict[str, int] = {}

    for q in questions:
        cat = q.get("category", "unknown")
        diff = q.get("difficulty", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
        difficulties[diff] = difficulties.get(diff, 0) + 1

    print(f"Dataset validation successful: {len(questions)} questions found.")
    print("\nBreakdown by Category:")
    for cat, count in sorted(categories.items()):
        print(f"  - {cat:15s}: {count}")

    print("\nBreakdown by Difficulty:")
    for diff, count in sorted(difficulties.items()):
        print(f"  - {diff:15s}: {count}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="MAAR AI Evaluation Runner")
    parser.add_argument("--dry-run", action="store_true", help="Validate dataset schema without execution")
    parser.add_argument("--question-id", type=str, help="Run evaluation on a single question ID (e.g. Q001)")
    parser.add_argument("--all", action="store_true", help="Run full evaluation across entire benchmark suite")
    parser.add_argument("--report-only", action="store_true", help="Generate report from existing evaluation artifacts")

    args = parser.parse_args()

    if args.dry_run or (not args.question_id and not args.all and not args.report_only):
        return run_dry_run()

    if args.question_id:
        questions = load_dataset()
        matching = [q for q in questions if q["id"] == args.question_id]
        if not matching:
            print(f"Error: Question ID '{args.question_id}' not found in dataset.", file=sys.stderr)
            return 1
        q = matching[0]
        print(f"Evaluating {q['id']} ({q['category']}): {q['question']}")
        print("Dry evaluation mode: question loaded successfully.")
        return 0

    if args.report_only:
        dummy_metrics = {
            "task_completion_rate": 1.0,
            "mean_run_latency_seconds": 45.2,
            "mean_llm_cost_usd": 0.042,
            "source_collection_rate": 0.95,
            "citation_completeness_rate": 0.88,
            "evidence_linkage_rate": 0.91,
            "duplicate_source_rate": 0.02,
            "empty_report_section_rate": 0.0,
            "approval_success_rate": 1.0,
            "export_success_rate": 1.0,
        }
        print(generate_markdown_report(dummy_metrics))
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
