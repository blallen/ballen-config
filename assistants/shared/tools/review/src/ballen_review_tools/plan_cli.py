"""Command-line entry point for local review planning."""

import argparse
import json
import os
import subprocess
import tempfile
from collections.abc import Sequence
from pathlib import Path

from ballen_review_tools.canonical import canonical_digest, source_digest
from ballen_review_tools.markdown import parse_review_markdown
from ballen_review_tools.models import ReviewCommentPlan, ReviewIdentity
from ballen_review_tools.workspace import validate_workspace


class GitWorkspaceProbe:
    """Use read-only Git commands to prove workspace state."""

    def __init__(self, repo_root: Path) -> None:
        """Store the approved repository root."""
        self._repo_root = repo_root

    def _run(self, *arguments: str) -> bool:
        """Return whether a fixed Git query succeeds."""
        result = subprocess.run(
            ["git", "-C", str(self._repo_root), *arguments],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return result.returncode == 0

    def is_ignored(self, relative: Path) -> bool:
        """Return whether Git ignores a path."""
        return self._run("check-ignore", "--quiet", "--", relative.as_posix())

    def is_tracked(self, relative: Path) -> bool:
        """Return whether Git tracks a path."""
        return self._run("ls-files", "--error-unmatch", "--", relative.as_posix())

    def is_staged(self, relative: Path) -> bool:
        """Return whether a path has staged changes."""
        return not self._run("diff", "--cached", "--quiet", "--", relative.as_posix())

    def is_conflicted(self, relative: Path) -> bool:
        """Return whether a path has unmerged index entries."""
        result = subprocess.run(
            [
                "git",
                "-C",
                str(self._repo_root),
                "ls-files",
                "--unmerged",
                "--",
                relative.as_posix(),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            text=True,
        )
        return bool(result.stdout)


def _parser() -> argparse.ArgumentParser:
    """Build the bounded review-plan argument parser."""
    parser = argparse.ArgumentParser(prog="review-plan")
    commands = parser.add_subparsers(dest="command", required=True)
    digest = commands.add_parser("digest")
    digest.add_argument("--artifact", type=Path, required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("--artifact", type=Path, required=True)
    workspace = commands.add_parser("workspace-check")
    workspace.add_argument("--repo-root", type=Path, required=True)
    workspace.add_argument("--destination", type=Path, required=True)
    workspace.add_argument("--proposed-file", type=Path, required=True)
    compile_review = commands.add_parser("compile-review")
    compile_review.add_argument("--draft", type=Path, required=True)
    compile_review.add_argument("--identity", type=Path, required=True)
    compile_review.add_argument("--output", type=Path, required=True)
    compile_review.add_argument("--repo-root", type=Path, required=True)
    return parser


def _read_json(path: Path) -> object:
    """Read one UTF-8 JSON artifact without exposing its contents."""
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> None:
    """Atomically write one UTF-8 JSON artifact."""
    path.parent.mkdir(parents=False, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as stream:
        temporary = Path(stream.name)
        json.dump(payload, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")
    os.replace(temporary, path)


def _compile_review(args: argparse.Namespace) -> int:
    """Compile a Markdown draft after safe-workspace preflight."""
    identity = ReviewIdentity.model_validate(_read_json(args.identity))
    draft_text = args.draft.read_text(encoding="utf-8")
    check = validate_workspace(
        repo_root=args.repo_root,
        destination=args.output.parent,
        proposed_file=args.output,
        probe=GitWorkspaceProbe(args.repo_root),
    )
    if not check.safe:
        raise ValueError(check.reason)
    plan = ReviewCommentPlan(
        contract_version="review-comment-plan/v1",
        identity=identity,
        source_draft_digest=source_digest(args.draft),
        actions=parse_review_markdown(draft_text, identity=identity),
    )
    _write_json(args.output, plan.model_dump(mode="json"))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run one read-only planning or validation command."""
    args = _parser().parse_args(argv)
    if args.command == "digest":
        print(canonical_digest(_read_json(args.artifact)))
        return 0
    if args.command == "validate":
        ReviewCommentPlan.model_validate(_read_json(args.artifact))
        print("valid")
        return 0
    if args.command == "workspace-check":
        result = validate_workspace(
            repo_root=args.repo_root,
            destination=args.destination,
            proposed_file=args.proposed_file,
            probe=GitWorkspaceProbe(args.repo_root),
        )
        print("safe" if result.safe else f"blocked: {result.reason}")
        return 0 if result.safe else 2
    return _compile_review(args)


if __name__ == "__main__":
    raise SystemExit(main())
