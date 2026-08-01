"""Intentional, idempotent component installation."""

import hashlib
import os
import shutil
import stat
import tempfile
import urllib.request
from collections.abc import Callable, Sequence
from http.client import HTTPMessage
from pathlib import Path
from typing import IO, Literal, Protocol, Self, cast
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ballen_config.models import Component, Manager, ResolvedSetup
from ballen_config.paths import assert_contained, assert_no_symlink_components
from ballen_config.probes import (
    application_paths_present,
    receipts_match,
    uv_tool_listed,
)
from ballen_config.runner import CommandResult, Runner
from ballen_config.runtime import RuntimePaths
from ballen_config.state import InstallRecord, StateStore


class InstallOutcome(BaseModel):
    """Normalized installation result without native output."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    component_id: str
    state: Literal["present", "installed", "optional-failure"]


class InstallAction(BaseModel):
    """One command or verified-download installation action."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    component_id: str
    kind: Literal["command", "verified-download"] = "command"
    argv: tuple[str, ...]
    required: bool = True
    url: str | None = None
    artifact_name: str | None = None
    size_bytes: int | None = Field(default=None, gt=0)
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_variant(self) -> Self:
        """Require complete, internally consistent action fields.

        Returns:
            The validated action.

        Raises:
            ValueError: If command and download action fields are mixed.
        """
        metadata = (self.url, self.artifact_name, self.size_bytes, self.sha256)
        if self.kind == "command":
            if any(value is not None for value in metadata):
                raise ValueError("command action cannot contain download metadata")
            if "{artifact}" in self.argv:
                raise ValueError("command action cannot use {artifact}")
            return self
        if any(value is None for value in metadata):
            raise ValueError("verified-download action requires all metadata")
        if not self.url or not self.url.startswith("https://"):
            raise ValueError("verified download requires HTTPS")
        if (
            not self.artifact_name
            or Path(self.artifact_name).name != self.artifact_name
        ):
            raise ValueError("artifact_name must be one filename")
        if self.argv.count("{artifact}") != 1:
            raise ValueError("verified argv requires one {artifact}")
        return self


class Downloader(Protocol):
    """Bounded downloader boundary for verified actions."""

    def download(self, *, url: str, destination: Path, maximum_bytes: int) -> None:
        """Download one HTTPS resource without exceeding a byte bound."""


class InstallError(RuntimeError):
    """A generic normalized installation failure."""


def _same_git_origin(expected: str, actual: str) -> bool:
    """Return whether two origins match, ignoring HTTPS-only trailing .git.

    Args:
        expected: Manifest-declared repository URL.
        actual: Repository origin reported by Git.

    Returns:
        Whether the normalized URLs identify the same origin.
    """
    expected_url = urlsplit(expected.strip())
    actual_url = urlsplit(actual.strip())
    if expected_url.scheme == actual_url.scheme == "https":
        return (
            expected_url._replace(path=expected_url.path.removesuffix(".git")).geturl()
            == actual_url._replace(path=actual_url.path.removesuffix(".git")).geturl()
        )
    return expected.strip() == actual.strip()


class HttpsRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject every redirect hop whose target is not HTTPS."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: HTTPMessage,
        newurl: str,
    ) -> urllib.request.Request | None:
        """Validate a redirect target before delegating to urllib.

        Args:
            req: Original request.
            fp: Response stream from the original request.
            code: HTTP redirect status.
            msg: HTTP status message.
            headers: Redirect response headers.
            newurl: Proposed redirect target.

        Returns:
            The delegated redirect request.

        Raises:
            InstallError: If the redirect target is not HTTPS.
        """
        if urlsplit(newurl).scheme != "https":
            raise InstallError("download redirect rejected")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class DownloadResponse(Protocol):
    """Minimal response surface consumed by the HTTPS downloader."""

    def __enter__(self) -> Self:
        """Enter the response context."""

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> object:
        """Exit the response context."""

    def geturl(self) -> str:
        """Return the final response URL."""

    def read(self, amount: int = -1) -> bytes:
        """Read at most ``amount`` response bytes."""


class UrlOpener(Protocol):
    """Injectable urllib-compatible response opener."""

    def open(self, fullurl: str, *, timeout: float) -> DownloadResponse:
        """Open a URL with a bounded timeout."""


class HttpsDownloader:
    """Production streaming HTTPS downloader."""

    def __init__(self, opener: UrlOpener | None = None) -> None:
        """Initialize with an HTTPS-hop-validating opener.

        Args:
            opener: Injectable opener for tests and controlled transports.
        """
        self.opener = opener or cast(
            UrlOpener,
            urllib.request.build_opener(HttpsRedirectHandler()),
        )

    def download(self, *, url: str, destination: Path, maximum_bytes: int) -> None:
        """Stream an HTTPS resource to an exclusive private artifact.

        Args:
            url: HTTPS source URL.
            destination: Artifact path that does not yet exist.
            maximum_bytes: Maximum allowed response body length.

        Raises:
            InstallError: If the URL or redirect is not HTTPS, or bound fails.
        """
        if urlsplit(url).scheme != "https":
            raise InstallError("verified download requires HTTPS")
        try:
            with self.opener.open(url, timeout=60) as response:
                if urlsplit(response.geturl()).scheme != "https":
                    raise InstallError("download redirected away from HTTPS")
                with destination.open("xb") as stream:
                    total = 0
                    while chunk := response.read(64 * 1024):
                        total += len(chunk)
                        if total > maximum_bytes:
                            raise InstallError("download exceeds declared size")
                        stream.write(chunk)
                    stream.flush()
                    os.fsync(stream.fileno())
        except Exception:
            destination.unlink(missing_ok=True)
            raise


class Installer:
    """Install missing intentional components without deleting user paths."""

    def __init__(
        self,
        runner: Runner,
        home: Path,
        path_exists: Callable[[Path], bool] = Path.exists,
        *,
        downloader: Downloader | None = None,
        private_temp_root: Path | None = None,
    ) -> None:
        """Initialize installer dependencies.

        Args:
            runner: Command execution boundary.
            home: Approved home root for git and download paths.
            path_exists: Injectable application-bundle predicate.
            downloader: Injectable HTTPS download boundary.
            private_temp_root: Private action workspace parent.
        """
        self.runner = runner
        self.home = home
        self.path_exists = path_exists
        self.downloader = downloader or HttpsDownloader()
        self.private_temp_root = (
            private_temp_root or home / ".local/state/ballen-config/tmp"
        )

    def install(self, component: Component) -> InstallOutcome:
        """Install one component, returning only its normalized outcome."""
        if component.manager in {Manager.BREW_FORMULA, Manager.BREW_CASK}:
            return self._brew(component)
        if component.manager is Manager.UV_TOOL:
            return self._uv_tool(component)
        return self._git(component)

    def run_action(self, action: InstallAction) -> InstallOutcome:
        """Run a prevalidated extension action without leaking native output."""
        if action.kind == "verified-download":
            try:
                completed = self._run_verified_download(action)
            except InstallError as error:
                if action.required:
                    raise InstallError(f"{error}: {action.component_id}") from error
                return InstallOutcome(
                    component_id=action.component_id, state="optional-failure"
                )
        else:
            completed = self.runner.run(action.argv)
        if completed["returncode"] == 0:
            return InstallOutcome(component_id=action.component_id, state="installed")
        if action.required:
            raise InstallError(f"required install failed: {action.component_id}")
        return InstallOutcome(
            component_id=action.component_id, state="optional-failure"
        )

    def _run_verified_download(self, action: InstallAction) -> CommandResult:
        """Download, verify, invoke, and remove a private artifact."""
        if (
            action.url is None
            or action.artifact_name is None
            or action.size_bytes is None
            or action.sha256 is None
        ):
            raise InstallError("verified-download action metadata is incomplete")
        workspace: Path | None = None
        try:
            try:
                temp_root = assert_contained(self.private_temp_root, self.home)
                assert_no_symlink_components(
                    temp_root, stop=self.home, include_leaf=True
                )
                temp_root.mkdir(parents=True, mode=0o700, exist_ok=True)
                assert_no_symlink_components(
                    temp_root, stop=self.home, include_leaf=True
                )
                os.chmod(temp_root, 0o700)
                workspace = Path(tempfile.mkdtemp(prefix="action-", dir=temp_root))
                os.chmod(workspace, 0o700)
            except (OSError, ValueError) as error:
                raise InstallError("download workspace failed") from error
            artifact = workspace / action.artifact_name
            try:
                self.downloader.download(
                    url=action.url,
                    destination=artifact,
                    maximum_bytes=action.size_bytes,
                )
            except InstallError:
                raise
            except Exception as error:
                raise InstallError("download failed") from error
            metadata = os.lstat(artifact)
            if not stat.S_ISREG(metadata.st_mode):
                raise InstallError("download verification failed")
            payload = artifact.read_bytes()
            if (
                len(payload) != action.size_bytes
                or hashlib.sha256(payload).hexdigest() != action.sha256
            ):
                raise InstallError("download verification failed")
            os.chmod(artifact, 0o600)
            argv = tuple(
                str(artifact) if value == "{artifact}" else value
                for value in action.argv
            )
            return self.runner.run(argv)
        finally:
            if workspace is not None:
                shutil.rmtree(workspace, ignore_errors=True)

    def _brew(self, component: Component) -> InstallOutcome:
        """Return present or install a Homebrew formula or cask."""
        if application_paths_present(component.application_paths, self.path_exists):
            if not component.receipt_prefixes:
                return InstallOutcome(component_id=component.id, state="present")
            receipts = self.runner.run(("pkgutil", "--pkgs"))
            if receipts["returncode"] == 0 and receipts_match(
                receipts["stdout"], component.receipt_prefixes
            ):
                return InstallOutcome(component_id=component.id, state="present")
        type_flag = (
            "--formula" if component.manager is Manager.BREW_FORMULA else "--cask"
        )
        present = self.runner.run(("brew", "list", type_flag, component.package))
        if present["returncode"] == 0:
            return InstallOutcome(component_id=component.id, state="present")
        command = ["brew", "install"]
        if component.manager is Manager.BREW_CASK:
            command.append("--cask")
        command.append(component.package)
        installed = self.runner.run(command)
        if installed["returncode"] == 0:
            return InstallOutcome(component_id=component.id, state="installed")
        if component.required:
            raise InstallError(f"required install failed: {component.id}")
        return InstallOutcome(component_id=component.id, state="optional-failure")

    def _uv_tool(self, component: Component) -> InstallOutcome:
        """Return present or install a uv-managed tool."""
        listed = self.runner.run(("uv", "tool", "list"))
        if listed["returncode"] == 0 and uv_tool_listed(
            listed["stdout"], component.package
        ):
            return InstallOutcome(component_id=component.id, state="present")
        installed = self.runner.run(("uv", "tool", "install", component.package))
        if installed["returncode"] == 0:
            return InstallOutcome(component_id=component.id, state="installed")
        if component.required:
            raise InstallError(f"required install failed: {component.id}")
        return InstallOutcome(component_id=component.id, state="optional-failure")

    def _git(self, component: Component) -> InstallOutcome:
        """Install and verify a pinned Git revision in a sibling stage directory."""
        if component.destination is None or component.revision is None:
            raise InstallError(f"git component metadata is incomplete: {component.id}")
        destination = assert_contained(self.home / component.destination, self.home)
        assert_no_symlink_components(destination, stop=self.home)
        if destination.is_symlink():
            raise InstallError(f"git destination is a symlink: {component.id}")
        if (destination / ".git").is_dir():
            try:
                origin = self.runner.run(
                    ("git", "-C", str(destination), "remote", "get-url", "origin")
                )
                if origin["returncode"] != 0 or not _same_git_origin(
                    component.package, origin["stdout"]
                ):
                    raise InstallError("git origin verification failed")
                status = self.runner.run(
                    ("git", "-C", str(destination), "status", "--porcelain")
                )
                if status["returncode"] != 0 or status["stdout"]:
                    raise InstallError("git worktree is not clean")
                current = self.runner.run(
                    ("git", "-C", str(destination), "rev-parse", "HEAD")
                )
                if current["returncode"] != 0:
                    raise InstallError("git revision inspection failed")
                if current["stdout"].strip() == component.revision:
                    return InstallOutcome(component_id=component.id, state="present")
                update_commands = (
                    (
                        "git",
                        "-C",
                        str(destination),
                        "fetch",
                        "--depth=1",
                        "--no-tags",
                        "origin",
                        component.revision,
                    ),
                    (
                        "git",
                        "-C",
                        str(destination),
                        "checkout",
                        "--detach",
                        "FETCH_HEAD",
                    ),
                )
                for command in update_commands:
                    if self.runner.run(command)["returncode"] != 0:
                        raise InstallError("git pin update failed")
                verified = self.runner.run(
                    ("git", "-C", str(destination), "rev-parse", "HEAD")
                )
                if (
                    verified["returncode"] != 0
                    or verified["stdout"].strip() != component.revision
                ):
                    raise InstallError("git revision verification failed")
            except InstallError as error:
                if component.required:
                    raise InstallError(
                        f"git checkout verification failed: {component.id}"
                    ) from error
                return InstallOutcome(
                    component_id=component.id, state="optional-failure"
                )
            return InstallOutcome(component_id=component.id, state="installed")
        if destination.exists():
            raise InstallError(f"unmanaged git destination exists: {component.id}")
        destination.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        stage = destination.with_name(f".{destination.name}.bootstrap-stage")
        if stage.exists() or stage.is_symlink():
            raise InstallError(f"stale git stage exists: {component.id}")
        stage_commands = (
            ("git", "init", str(stage)),
            ("git", "-C", str(stage), "remote", "add", "origin", component.package),
            (
                "git",
                "-C",
                str(stage),
                "fetch",
                "--depth=1",
                "--no-tags",
                "origin",
                component.revision,
            ),
            ("git", "-C", str(stage), "checkout", "--detach", "FETCH_HEAD"),
        )
        try:
            for stage_command in stage_commands:
                if self.runner.run(stage_command)["returncode"] != 0:
                    raise InstallError(f"git install failed: {component.id}")
            verified = self.runner.run(("git", "-C", str(stage), "rev-parse", "HEAD"))
            if (
                verified["returncode"] != 0
                or verified["stdout"].strip() != component.revision
            ):
                raise InstallError(f"git revision verification failed: {component.id}")
            os.replace(stage, destination)
            return InstallOutcome(component_id=component.id, state="installed")
        except (InstallError, OSError) as error:
            if stage.is_dir() and not stage.is_symlink():
                shutil.rmtree(stage)
            if component.required:
                raise InstallError(
                    f"required install failed: {component.id}"
                ) from error
            return InstallOutcome(component_id=component.id, state="optional-failure")


class InstallStageReport(BaseModel):
    """Normalized install stage result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    exit_code: Literal[0, 1]
    outcomes: tuple[str, ...]


type InstallActionSupplier = Callable[
    [ResolvedSetup, RuntimePaths, Runner], Sequence[InstallAction]
]
type InstallActionCandidateSupplier = Callable[
    [ResolvedSetup, RuntimePaths], Sequence[InstallAction]
]


def run_install(
    *,
    components: Sequence[Component],
    actions: Sequence[InstallAction],
    runner: Runner,
    paths: RuntimePaths,
    state_store: StateStore,
    downloader: Downloader,
) -> InstallStageReport:
    """Install stable components and actions while recording normalized state."""
    installer = Installer(
        runner,
        paths.home,
        downloader=downloader,
        private_temp_root=paths.state_root / "tmp",
    )
    outcomes: list[str] = []
    try:
        for component in components:
            outcome = installer.install(component)
            state_store.record_install(
                InstallRecord(resource_id=outcome.component_id, state=outcome.state)
            )
            outcomes.append(f"{outcome.component_id}: {outcome.state}")
        for action in actions:
            outcome = installer.run_action(action)
            state_store.record_install(
                InstallRecord(resource_id=outcome.component_id, state=outcome.state)
            )
            outcomes.append(f"{outcome.component_id}: {outcome.state}")
    except InstallError as error:
        component_id = str(error).rsplit(": ", maxsplit=1)[-1]
        outcomes.append(f"{component_id}: required-failure")
        return InstallStageReport(exit_code=1, outcomes=tuple(outcomes))
    return InstallStageReport(exit_code=0, outcomes=tuple(outcomes))
