from __future__ import annotations

import sys
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Run explicit small-LLM evaluation without changing the production Groq provider."

    def add_arguments(self, parser):
        parser.add_argument("--provider", choices=["local", "groq"], default="local")
        parser.add_argument("--model", default="Qwen/Qwen3-1.7B")
        parser.add_argument("--limit", type=int, default=10)
        parser.add_argument("--task-type", default="")
        parser.add_argument("--language", default="")

    def handle(self, *args, **options):
        project_root = Path(__file__).resolve().parents[5]
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        try:
            from ml.eval.runner import main as run_eval
        except ImportError as exc:
            raise CommandError("Model lab evaluation package could not be imported") from exc

        argv = [
            "evaluate_small_llm",
            "--provider",
            options["provider"],
            "--model",
            options["model"],
            "--limit",
            str(options["limit"]),
        ]
        if options["task_type"]:
            argv.extend(["--task-type", options["task_type"]])
        if options["language"]:
            argv.extend(["--language", options["language"]])
        previous_argv = sys.argv
        try:
            sys.argv = argv
            result = run_eval()
        finally:
            sys.argv = previous_argv
        if result != 0:
            raise CommandError("Small LLM evaluation failed")
