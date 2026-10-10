"""CLI for GitHub publication preview and guarded execution."""

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from ballen_review_tools.models import ReviewCommentPlan
from ballen_review_tools.plan_cli import read_json, write_json
from ballen_review_tools.providers.base import SubprocessRunner
from ballen_review_tools.providers.github import GitHubProvider, GitHubProviderError
from ballen_review_tools.publication import (
    execute_github_publication,
    preview_github_publication,
)


def _parser() -> argparse.ArgumentParser:
    """Build the bounded publication CLI."""
    parser = argparse.ArgumentParser(prog="publish-github-review")
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
    return ReviewCommentPlan.model_validate(read_json(path))


def main(argv: Sequence[str] | None = None) -> int:
    """Run a read-only preview or separately gated execution."""
    args = _parser().parse_args(argv)
    try:
        for flag, path in (("--output", args.output), ("--receipt", args.receipt)):
            if path is not None and not (
                path.parent.is_dir() and os.access(path.parent, os.W_OK)
            ):
                raise ValueError(
                    f"{flag} directory must exist and be writable: {path.parent}"
                )
        plan = _load_plan(args.plan)
        provider = GitHubProvider(identity=plan.identity, runner=SubprocessRunner())
        if args.command == "preview":
            if args.output is None:
                raise ValueError("preview requires --output")
            preview = preview_github_publication(plan, provider)
            write_json(args.output, preview.model_dump(mode="json"))
            print(preview.status)
            return 0 if preview.status == "ready" else 2
        if args.approved_plan_digest is None or args.expected_head is None:
            raise ValueError("execute requires approved plan digest and expected head")
        if args.receipt is None:
            raise ValueError("execute requires --receipt")
        result = execute_github_publication(
            plan=plan,
            approved_plan_digest=args.approved_plan_digest,
            expected_head=args.expected_head,
            provider=provider,
        )
        if result.receipt is not None:
            write_json(args.receipt, result.receipt.model_dump(mode="json"))
        if result.reason:
            print(f"blocked: {result.reason}", file=sys.stderr)
        return 0 if result.status == "posted" else 2
    except (GitHubProviderError, ValueError, OSError) as error:
        print(f"blocked: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
