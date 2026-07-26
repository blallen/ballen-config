import hashlib
import stat
from collections.abc import Sequence
from pathlib import Path
from urllib.request import Request

import pytest

from ballen_config.install import (
    HttpsRedirectHandler,
    InstallAction,
    Installer,
    InstallError,
    run_install,
)
from ballen_config.models import Component, Manager
from ballen_config.runner import CommandResult
from ballen_config.runtime import RuntimePaths
from ballen_config.state import StateStore

_OH_MY_ZSH_REVISION = (
    "b37dd49ca5bfe0d99b35607637152cb8cc8b29d7"  # pragma: allowlist secret
)
_FORGIT_REVISION = (
    "15db0016623b87472c0b6ff7488b123a74b82c7e"  # pragma: allowlist secret
)


class FakeRunner:
    def __init__(self, results: list[CommandResult]) -> None:
        self.results = iter(results)
        self.commands: list[tuple[str, ...]] = []

    def run(self, command: Sequence[str]) -> CommandResult:
        self.commands.append(tuple(command))
        return next(self.results)


class StagingGitRunner(FakeRunner):
    """Create the temporary checkout directory when Git initializes it."""

    def run(self, command: Sequence[str]) -> CommandResult:
        completed = super().run(command)
        if tuple(command[:2]) == ("git", "init"):
            Path(command[-1]).mkdir()
        return completed


class FakeDownloader:
    def __init__(self, payloads: dict[str, bytes]) -> None:
        self.payloads = payloads
        self.destinations: list[Path] = []

    def download(self, *, url: str, destination: Path, maximum_bytes: int) -> None:
        payload = self.payloads[url]
        if len(payload) > maximum_bytes:
            raise InstallError("download exceeds declared size")
        self.destinations.append(destination)
        destination.write_bytes(payload)


def result(code: int = 0, stdout: str = "", stderr: str = "") -> CommandResult:
    return {"returncode": code, "stdout": stdout, "stderr": stderr}


def test_present_formula_is_a_no_op(tmp_path: Path) -> None:
    """An installed formula is inspected without issuing an install command."""
    runner = FakeRunner([result(stdout="gh\n")])
    outcome = Installer(runner, tmp_path).install(
        Component(id="gh", manager=Manager.BREW_FORMULA, package="gh")
    )
    assert outcome.state == "present"
    assert runner.commands == [("brew", "list", "--formula", "gh")]


def test_missing_formula_is_installed(tmp_path: Path) -> None:
    """A missing formula produces the expected package-manager invocation."""
    runner = FakeRunner([result(1), result()])
    outcome = Installer(runner, tmp_path).install(
        Component(id="gh", manager=Manager.BREW_FORMULA, package="gh")
    )
    assert outcome.state == "installed"
    assert runner.commands[-1] == ("brew", "install", "gh")


def test_existing_application_bundle_satisfies_cask(tmp_path: Path) -> None:
    """A declared application bundle avoids an unnecessary cask install."""
    runner = FakeRunner([])
    installer = Installer(
        runner,
        tmp_path,
        path_exists=lambda path: path == Path("/Applications/Brave Browser.app"),
    )
    component = Component(
        id="brave-browser",
        manager=Manager.BREW_CASK,
        package="brave-browser",
        application_paths=("/Applications/Brave Browser.app",),
    )
    assert installer.install(component).state == "present"
    assert runner.commands == []


def test_vendor_mactex_satisfies_opt_in_cask(tmp_path: Path) -> None:
    """A vendor-provided TeX installation satisfies the optional cask."""
    runner = FakeRunner(
        [result(stdout="org.tug.mactex.gui2025\norg.tug.texlive2025\n")]
    )
    installer = Installer(
        runner,
        tmp_path,
        path_exists=lambda path: path == Path("/Library/TeX/texbin/latex"),
    )
    component = Component(
        id="mactex",
        manager=Manager.BREW_CASK,
        package="mactex",
        application_paths=("/Library/TeX/texbin/latex",),
        receipt_prefixes=("org.tug.mactex.gui",),
        enabled_by_default=False,
        include_key="mactex",
        required=False,
        large=True,
    )
    assert installer.install(component).state == "present"
    assert runner.commands == [("pkgutil", "--pkgs")]


def test_unmanaged_git_destination_is_preserved(tmp_path: Path) -> None:
    """A pre-existing unowned checkout is never overwritten."""
    destination = tmp_path / ".oh-my-zsh"
    destination.mkdir()
    component = Component(
        id="oh-my-zsh",
        manager=Manager.GIT,
        package="https://github.com/ohmyzsh/ohmyzsh.git",
        destination=".oh-my-zsh",
        revision=_OH_MY_ZSH_REVISION,
    )
    with pytest.raises(InstallError, match="unmanaged git destination"):
        Installer(FakeRunner([]), tmp_path).install(component)
    assert destination.is_dir()


def test_git_destination_rejects_symlinked_parent(tmp_path: Path) -> None:
    """Git installation refuses a destination that escapes through a link."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / ".oh-my-zsh").symlink_to(outside, target_is_directory=True)
    component = Component(
        id="forgit",
        manager=Manager.GIT,
        package="https://github.com/wfxr/forgit.git",
        destination=".oh-my-zsh/custom/plugins/forgit",
        revision=_FORGIT_REVISION,
    )
    with pytest.raises(ValueError, match="symlinked path component"):
        Installer(FakeRunner([]), tmp_path).install(component)
    assert list(outside.iterdir()) == []


def test_git_install_publishes_only_a_verified_pinned_revision(tmp_path: Path) -> None:
    """A new checkout fetches and verifies the configured immutable revision."""
    revision = _OH_MY_ZSH_REVISION
    destination = tmp_path / ".oh-my-zsh"
    runner = StagingGitRunner(
        [result(), result(), result(), result(), result(stdout=f"{revision}\n")]
    )
    component = Component(
        id="oh-my-zsh",
        manager=Manager.GIT,
        package="https://github.com/ohmyzsh/ohmyzsh.git",
        destination=".oh-my-zsh",
        revision=revision,
    )

    assert Installer(runner, tmp_path).install(component).state == "installed"

    stage = destination.with_name(f".{destination.name}.bootstrap-stage")
    assert runner.commands == [
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
            revision,
        ),
        ("git", "-C", str(stage), "checkout", "--detach", "FETCH_HEAD"),
        ("git", "-C", str(stage), "rev-parse", "HEAD"),
    ]
    assert destination.is_dir()
    assert not stage.exists()


def test_git_install_cleans_stage_after_failed_pin_fetch(tmp_path: Path) -> None:
    """A failed pinned fetch leaves neither a destination nor a stage directory."""
    revision = _OH_MY_ZSH_REVISION
    runner = StagingGitRunner([result(), result(), result(1)])
    component = Component(
        id="oh-my-zsh",
        manager=Manager.GIT,
        package="https://github.com/ohmyzsh/ohmyzsh.git",
        destination=".oh-my-zsh",
        revision=revision,
    )

    with pytest.raises(InstallError, match="required install failed"):
        Installer(runner, tmp_path).install(component)

    assert not (tmp_path / ".oh-my-zsh").exists()
    destination = tmp_path / ".oh-my-zsh"
    stage = destination.with_name(f".{destination.name}.bootstrap-stage")
    assert not destination.exists()
    assert not stage.exists()


def test_existing_clean_git_checkout_converges_to_configured_revision(
    tmp_path: Path,
) -> None:
    """A clean checkout with the expected HTTPS origin advances to the pin."""
    revision = _OH_MY_ZSH_REVISION
    destination = tmp_path / ".oh-my-zsh"
    (destination / ".git").mkdir(parents=True)
    runner = FakeRunner(
        [
            result(stdout="https://github.com/ohmyzsh/ohmyzsh\n"),
            result(),
            result(stdout=f"{'0' * 40}\n"),
            result(),
            result(),
            result(stdout=f"{revision}\n"),
        ]
    )
    component = Component(
        id="oh-my-zsh",
        manager=Manager.GIT,
        package="https://github.com/ohmyzsh/ohmyzsh.git",
        destination=".oh-my-zsh",
        revision=revision,
    )

    assert Installer(runner, tmp_path).install(component).state == "installed"
    assert runner.commands == [
        ("git", "-C", str(destination), "remote", "get-url", "origin"),
        ("git", "-C", str(destination), "status", "--porcelain"),
        ("git", "-C", str(destination), "rev-parse", "HEAD"),
        (
            "git",
            "-C",
            str(destination),
            "fetch",
            "--depth=1",
            "--no-tags",
            "origin",
            revision,
        ),
        ("git", "-C", str(destination), "checkout", "--detach", "FETCH_HEAD"),
        ("git", "-C", str(destination), "rev-parse", "HEAD"),
    ]


def test_existing_pinned_git_checkout_is_present_without_fetch(tmp_path: Path) -> None:
    """An already pinned checkout remains usable without network access."""
    revision = _OH_MY_ZSH_REVISION
    destination = tmp_path / ".oh-my-zsh"
    (destination / ".git").mkdir(parents=True)
    runner = FakeRunner(
        [
            result(stdout="https://github.com/ohmyzsh/ohmyzsh.git\n"),
            result(),
            result(stdout=f"{revision}\n"),
        ]
    )
    component = Component(
        id="oh-my-zsh",
        manager=Manager.GIT,
        package="https://github.com/ohmyzsh/ohmyzsh.git",
        destination=".oh-my-zsh",
        revision=revision,
    )

    assert Installer(runner, tmp_path).install(component).state == "present"
    assert runner.commands == [
        ("git", "-C", str(destination), "remote", "get-url", "origin"),
        ("git", "-C", str(destination), "status", "--porcelain"),
        ("git", "-C", str(destination), "rev-parse", "HEAD"),
    ]


@pytest.mark.parametrize(
    ("origin", "status", "expected_commands"),
    [
        pytest.param(
            "https://github.com/other/repository.git\n", "", 1, id="wrong-origin"
        ),
        pytest.param(
            "https://github.com/ohmyzsh/ohmyzsh.git\n",
            " M plugins/example\n",
            2,
            id="dirty-worktree",
        ),
    ],
)
def test_existing_git_checkout_rejects_untrusted_state(
    tmp_path: Path,
    origin: str,
    status: str,
    expected_commands: int,
) -> None:
    """An existing checkout must have the expected origin and no tracked changes."""
    destination = tmp_path / ".oh-my-zsh"
    (destination / ".git").mkdir(parents=True)
    runner = FakeRunner([result(stdout=origin), result(stdout=status)])
    component = Component(
        id="oh-my-zsh",
        manager=Manager.GIT,
        package="https://github.com/ohmyzsh/ohmyzsh.git",
        destination=".oh-my-zsh",
        revision=_OH_MY_ZSH_REVISION,
    )

    with pytest.raises(InstallError, match="git checkout verification failed"):
        Installer(runner, tmp_path).install(component)

    assert len(runner.commands) == expected_commands


def test_optional_failure_is_reported_without_raising(tmp_path: Path) -> None:
    """Optional package failures become reportable outcomes rather than errors."""
    runner = FakeRunner([result(1), result(1, stderr="native failure")])
    component = Component(
        id="signal",
        manager=Manager.BREW_CASK,
        package="signal",
        enabled_by_default=False,
        include_key="signal",
        required=False,
    )
    assert Installer(runner, tmp_path).install(component).state == "optional-failure"


def make_action(
    payload: bytes,
    *,
    required: bool = True,
    size_delta: int = 0,
    digest: str | None = None,
) -> InstallAction:
    return InstallAction(
        component_id="cursor-extension",
        kind="verified-download",
        argv=("cursor", "--install-extension", "{artifact}"),
        required=required,
        url="https://example.test/tool.vsix",
        artifact_name="tool.vsix",
        size_bytes=len(payload) + size_delta,
        sha256=digest or hashlib.sha256(payload).hexdigest(),
    )


def test_verified_download_checks_size_hash_runs_and_cleans(
    fake_home: Path, tmp_path: Path
) -> None:
    """Verified downloads validate payloads, invoke tools, and remove artifacts."""
    payload = b"extension bytes"
    runner = FakeRunner([result()])
    paths = RuntimePaths.from_roots(repo_root=tmp_path, home=fake_home)
    installer = Installer(
        runner,
        fake_home,
        downloader=FakeDownloader({"https://example.test/tool.vsix": payload}),
        private_temp_root=paths.state_root / "tmp",
    )
    assert installer.run_action(make_action(payload)).state == "installed"
    artifact = Path(runner.commands[0][2])
    assert runner.commands[0][:2] == ("cursor", "--install-extension")
    assert not artifact.exists()
    assert (paths.state_root / "tmp").is_dir()


@pytest.mark.parametrize(
    ("size_delta", "digest", "required", "expected_state"),
    [
        pytest.param(1, None, True, None, id="required-size-mismatch"),
        pytest.param(0, "0" * 64, True, None, id="required-hash-mismatch"),
        pytest.param(
            1,
            None,
            False,
            "optional-failure",
            id="optional-size-mismatch",
        ),
        pytest.param(
            0,
            "0" * 64,
            False,
            "optional-failure",
            id="optional-hash-mismatch",
        ),
    ],
)
def test_verified_download_normalizes_verification_failures(
    fake_home: Path,
    tmp_path: Path,
    size_delta: int,
    digest: str | None,
    required: bool,
    expected_state: str | None,
) -> None:
    """Normalize verification failures while preserving temporary-root cleanup."""
    payload = b"extension bytes"
    runner = FakeRunner([])
    paths = RuntimePaths.from_roots(repo_root=tmp_path, home=fake_home)
    installer = Installer(
        runner,
        fake_home,
        downloader=FakeDownloader({"https://example.test/tool.vsix": payload}),
        private_temp_root=paths.state_root / "tmp",
    )
    action = make_action(
        payload,
        required=required,
        size_delta=size_delta,
        digest=digest,
    )
    if required:
        with pytest.raises(InstallError, match="verification failed"):
            installer.run_action(action)
    else:
        assert installer.run_action(action).state == expected_state
    assert runner.commands == []
    assert (paths.state_root / "tmp").is_dir()


def test_verified_download_preserves_reusable_temp_parent(
    fake_home: Path, tmp_path: Path
) -> None:
    """Preserve unrelated private temporary-root content across a download."""
    payload = b"extension bytes"
    paths = RuntimePaths.from_roots(repo_root=tmp_path, home=fake_home)
    temp_root = paths.state_root / "tmp"
    temp_root.mkdir(parents=True)
    stale = temp_root / "unrelated-stale-content"
    stale.write_text("preserve me")
    runner = FakeRunner([result()])
    installer = Installer(
        runner,
        fake_home,
        downloader=FakeDownloader({"https://example.test/tool.vsix": payload}),
        private_temp_root=temp_root,
    )

    assert installer.run_action(make_action(payload)).state == "installed"

    assert stale.read_text() == "preserve me"
    assert stat.S_IMODE(temp_root.stat().st_mode) == 0o700
    assert list(temp_root.iterdir()) == [stale]


def test_verified_download_actions_use_distinct_workspaces(
    fake_home: Path, tmp_path: Path
) -> None:
    """Use and clean an isolated workspace for each verified download."""
    payload = b"extension bytes"
    paths = RuntimePaths.from_roots(repo_root=tmp_path, home=fake_home)
    downloader = FakeDownloader({"https://example.test/tool.vsix": payload})
    installer = Installer(
        FakeRunner([result(), result()]),
        fake_home,
        downloader=downloader,
        private_temp_root=paths.state_root / "tmp",
    )

    installer.run_action(make_action(payload))
    installer.run_action(make_action(payload))

    workspaces = [destination.parent for destination in downloader.destinations]
    assert len(set(workspaces)) == 2
    assert all(not workspace.exists() for workspace in workspaces)
    assert (paths.state_root / "tmp").is_dir()


def test_optional_verified_download_setup_failure_is_normalized(
    fake_home: Path, tmp_path: Path
) -> None:
    """Optional downloads normalize private-workspace setup failures."""
    payload = b"extension bytes"
    paths = RuntimePaths.from_roots(repo_root=tmp_path, home=fake_home)
    blocked_temp_root = paths.state_root / "tmp"
    blocked_temp_root.parent.mkdir(parents=True)
    blocked_temp_root.write_text("not a directory")
    runner = FakeRunner([])
    installer = Installer(
        runner,
        fake_home,
        downloader=FakeDownloader({"https://example.test/tool.vsix": payload}),
        private_temp_root=blocked_temp_root,
    )

    outcome = installer.run_action(make_action(payload, required=False))

    assert outcome.state == "optional-failure"
    assert runner.commands == []
    assert blocked_temp_root.read_text() == "not a directory"


def test_https_redirect_handler_rejects_http_hop_without_url_leakage() -> None:
    """An insecure redirect fails without revealing its sensitive URL."""
    handler = HttpsRedirectHandler()
    request = Request("https://downloads.example.test/tool")

    with pytest.raises(InstallError) as captured:
        handler.redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "http://redirect.example.test/tool?token=secret",
        )

    assert str(captured.value) == "download redirect rejected"
    assert "secret" not in str(captured.value)
    assert "redirect.example.test" not in str(captured.value)


def test_https_redirect_handler_delegates_https_hop() -> None:
    """An HTTPS redirect remains available to the standard redirect flow."""
    handler = HttpsRedirectHandler()
    request = Request("https://downloads.example.test/tool")

    redirected = handler.redirect_request(
        request,
        None,
        302,
        "Found",
        {},
        "https://cdn.example.test/tool",
    )

    assert redirected is not None
    assert redirected.full_url == "https://cdn.example.test/tool"


def test_run_install_records_normalized_outcomes(
    fake_home: Path, tmp_path: Path
) -> None:
    """Install reports and persisted state use the same normalized outcome."""
    paths = RuntimePaths.from_roots(repo_root=tmp_path, home=fake_home)
    store = StateStore(paths)
    report = run_install(
        components=(Component(id="gh", manager=Manager.BREW_FORMULA, package="gh"),),
        actions=(),
        runner=FakeRunner([result(1), result()]),
        paths=paths,
        state_store=store,
        downloader=FakeDownloader({}),
    )
    assert report.exit_code == 0
    assert report.outcomes == ("gh: installed",)
    assert store.load().installs["gh"].state == "installed"


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "kind": "command",
            "url": "https://example.test/x",
            "artifact_name": "x",
            "size_bytes": 1,
            "sha256": "a" * 64,
        },
        {"kind": "command", "argv": ("tool", "{artifact}")},
        {
            "kind": "verified-download",
            "argv": ("tool", "{artifact}"),
            "url": "http://example.test/x",
            "artifact_name": "x",
            "size_bytes": 1,
            "sha256": "a" * 64,
        },
        {
            "kind": "verified-download",
            "argv": ("tool", "{artifact}", "{artifact}"),
            "url": "https://example.test/x",
            "artifact_name": "x",
            "size_bytes": 1,
            "sha256": "a" * 64,
        },
    ],
)
def test_install_action_rejects_invalid_variants(kwargs: dict[str, object]) -> None:
    """Unsupported action-field combinations fail during action construction."""
    with pytest.raises(ValueError):
        InstallAction(component_id="test", **{"argv": ("tool",), **kwargs})
