"""Command-line entry point for local review planning."""

import argparse
import json
import os
import subprocess
import tempfile
from collections.abc import Sequence
from pathlib import Path
from urllib.parse import urlsplit

from ballen_review_tools.canonical import (
    canonical_digest,
    source_digest_bytes,
)
from ballen_review_tools.markdown import parse_review_markdown
from ballen_review_tools.models import (
    PublicationPreview,
    PublicationReceipt,
    ReviewCommentPlan,
    ReviewIdentity,
)
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

    def _capture(self, *arguments: str) -> str | None:
        """Return one bounded Git value without exposing command output."""
        result = subprocess.run(
            ["git", "-C", str(self._repo_root), *arguments],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            text=True,
        )
        if result.returncode != 0:
            return None
        value = result.stdout.strip()
        return value or None

    def current_head(self) -> str | None:
        """Return the exact checked-out commit when Git can prove it."""
        return self._capture("rev-parse", "--verify", "HEAD")

    def remote_identity(self) -> tuple[str, str] | None:
        """Return the origin host and repository path when available."""
        remote = self._capture("remote", "get-url", "origin")
        if remote is None:
            return None
        if remote.startswith("git@") and ":" in remote:
            host, path = remote[4:].split(":", 1)
        else:
            parsed = urlsplit(remote)
            remote_host = parsed.hostname
            path = parsed.path
            if remote_host is None:
                return None
            host = remote_host
        return host, path.strip("/").removesuffix(".git")

    def identity_matches(self, identity: ReviewIdentity) -> tuple[bool, str]:
        """Bind provider identity and expected head to this checkout."""
        remote = self.remote_identity()
        if remote is None:
            return False, "repository origin identity cannot be verified"
        host, repository = remote
        expected_repository = identity.repository.removesuffix(".git")
        if host != identity.host or not (
            repository == expected_repository
            or repository.endswith(f"/{expected_repository}")
        ):
            return False, "repository origin does not match review identity"
        if self.current_head() != identity.head_revision:
            return False, "checked-out head does not match review identity"
        return True, ""

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
    draft_bytes = args.draft.read_bytes()
    draft_text = draft_bytes.decode("utf-8")
    probe = GitWorkspaceProbe(args.repo_root)
    identity_safe, identity_reason = probe.identity_matches(identity)
    if not identity_safe:
        raise ValueError(identity_reason)
    check = validate_workspace(
        repo_root=args.repo_root,
        destination=args.output.parent,
        proposed_file=args.output,
        probe=probe,
    )
    if not check.safe:
        raise ValueError(check.reason)
    parsed = parse_review_markdown(draft_text, identity=identity)
    plan = ReviewCommentPlan(
        contract_version="review-comment-plan/v1",
        identity=identity,
        source_draft_digest=source_digest_bytes(draft_bytes),
        actions=parsed.actions,
        diagnostics=parsed.diagnostics,
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
        payload = _read_json(args.artifact)
        if not isinstance(payload, dict):
            raise ValueError("artifact must be a JSON object")
        contract_version = payload.get("contract_version")
        if contract_version == "review-comment-plan/v1":
            ReviewCommentPlan.model_validate(payload)
        elif contract_version == "publication-preview/v1":
            PublicationPreview.model_validate(payload)
        elif contract_version == "publication-receipt/v1":
            PublicationReceipt.model_validate(payload)
        else:
            raise ValueError("unsupported artifact contract")
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
