"""CLI for GitLab publication preview and guarded execution."""

import argparse
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from ballen_review_tools.gitlab_publication import (
    execute_gitlab_publication,
    plan_digest,
    preview_gitlab_publication,
)
from ballen_review_tools.models import ReviewCommentPlan
from ballen_review_tools.plan_cli import _read_json, _write_json
from ballen_review_tools.providers.base import CompletedCommand
from ballen_review_tools.providers.gitlab import GitLabProvider, GitLabProviderError


class SubprocessRunner:
    """Run fixed provider argument arrays without a shell."""

    def run(
        self,
        argv: Sequence[str],
        *,
        input_text: str | None = None,
    ) -> CompletedCommand:
        """Return bounded subprocess output and status."""
        result = subprocess.run(
            list(argv),
            input=input_text,
            capture_output=True,
            text=True,
            check=False,
            shell=False,
        )
        return CompletedCommand(result.returncode, result.stdout, result.stderr)


def _parser() -> argparse.ArgumentParser:
    """Build the bounded GitLab publication CLI."""
    parser = argparse.ArgumentParser(prog="publish-gitlab-review")
    parser.add_argument(
        "command", nargs="?", choices=("preview", "execute"), default="preview"
    )
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--approved-plan-digest")
    parser.add_argument("--expected-head")
    parser.add_argument("--receipt", type=Path)
    return parser


def _load_plan(path: Path) -> ReviewCommentPlan:
    """Load and strictly validate one logical plan."""
    return ReviewCommentPlan.model_validate(_read_json(path))


def main(argv: Sequence[str] | None = None) -> int:
    """Run a read-only preview or separately gated execution."""
    args = _parser().parse_args(argv)
    try:
        plan = _load_plan(args.plan)
        provider = GitLabProvider(identity=plan.identity, runner=SubprocessRunner())
        if args.command == "preview":
            if args.output is None:
                raise ValueError("preview requires --output")
            preview = preview_gitlab_publication(plan, provider)
            _write_json(args.output, preview.model_dump(mode="json"))
            print(preview.status)
            return 0 if preview.status == "ready" else 2
        if args.approved_plan_digest is None or args.expected_head is None:
            raise ValueError("execute requires approved plan digest and expected head")
        if args.receipt is None:
            raise ValueError("execute requires --receipt")
        if args.approved_plan_digest != plan_digest(plan):
            raise ValueError("approved plan digest does not match current plan")
        result = execute_gitlab_publication(
            plan=plan,
            approved_plan_digest=args.approved_plan_digest,
            expected_head=args.expected_head,
            provider=provider,
        )
        if result.receipt is not None:
            _write_json(args.receipt, result.receipt.model_dump(mode="json"))
        if result.reason:
            print(f"blocked: {result.reason}", file=sys.stderr)
        return 0 if result.status == "posted" else 2
    except (GitLabProviderError, ValueError, OSError) as error:
        print(f"blocked: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
