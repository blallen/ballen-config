import hashlib
from collections.abc import Sequence
from pathlib import Path

import pytest

from ballen_config.install import InstallAction, Installer, InstallError, run_install
from ballen_config.models import Component, Manager
from ballen_config.runner import CommandResult
from ballen_config.runtime import RuntimePaths
from ballen_config.state import StateStore


class FakeRunner:
    def __init__(self, results: list[CommandResult]) -> None:
        self.results = iter(results)
        self.commands: list[tuple[str, ...]] = []

    def run(self, command: Sequence[str]) -> CommandResult:
        self.commands.append(tuple(command))
        return next(self.results)


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
    runner = FakeRunner([result(stdout="gh\n")])
    outcome = Installer(runner, tmp_path).install(
        Component(id="gh", manager=Manager.BREW_FORMULA, package="gh")
    )
    assert outcome.state == "present"
    assert runner.commands == [("brew", "list", "--formula", "gh")]


def test_missing_formula_is_installed(tmp_path: Path) -> None:
    runner = FakeRunner([result(1), result()])
    outcome = Installer(runner, tmp_path).install(
        Component(id="gh", manager=Manager.BREW_FORMULA, package="gh")
    )
    assert outcome.state == "installed"
    assert runner.commands[-1] == ("brew", "install", "gh")


def test_existing_application_bundle_satisfies_cask(tmp_path: Path) -> None:
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
    destination = tmp_path / ".oh-my-zsh"
    destination.mkdir()
    component = Component(
        id="oh-my-zsh",
        manager=Manager.GIT,
        package="https://github.com/ohmyzsh/ohmyzsh.git",
        destination=".oh-my-zsh",
    )
    with pytest.raises(InstallError, match="unmanaged git destination"):
        Installer(FakeRunner([]), tmp_path).install(component)
    assert destination.is_dir()


def test_git_destination_rejects_symlinked_parent(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / ".oh-my-zsh").symlink_to(outside, target_is_directory=True)
    component = Component(
        id="forgit",
        manager=Manager.GIT,
        package="https://github.com/wfxr/forgit.git",
        destination=".oh-my-zsh/custom/plugins/forgit",
    )
    with pytest.raises(ValueError, match="symlinked path component"):
        Installer(FakeRunner([]), tmp_path).install(component)
    assert list(outside.iterdir()) == []


def test_optional_failure_is_reported_without_raising(tmp_path: Path) -> None:
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
    assert not (paths.state_root / "tmp").exists()


@pytest.mark.parametrize(("size_delta", "digest"), [(1, None), (0, "0" * 64)])
def test_verified_download_rejects_unverified_payload_and_cleans(
    fake_home: Path,
    tmp_path: Path,
    size_delta: int,
    digest: str | None,
) -> None:
    payload = b"extension bytes"
    runner = FakeRunner([])
    paths = RuntimePaths.from_roots(repo_root=tmp_path, home=fake_home)
    installer = Installer(
        runner,
        fake_home,
        downloader=FakeDownloader({"https://example.test/tool.vsix": payload}),
        private_temp_root=paths.state_root / "tmp",
    )
    with pytest.raises(InstallError, match="verification failed"):
        installer.run_action(make_action(payload, size_delta=size_delta, digest=digest))
    assert runner.commands == []
    assert not (paths.state_root / "tmp").exists()


@pytest.mark.parametrize(("size_delta", "digest"), [(1, None), (0, "0" * 64)])
def test_optional_verified_download_failure_is_nonfatal(
    fake_home: Path,
    tmp_path: Path,
    size_delta: int,
    digest: str | None,
) -> None:
    payload = b"extension bytes"
    runner = FakeRunner([])
    paths = RuntimePaths.from_roots(repo_root=tmp_path, home=fake_home)
    installer = Installer(
        runner,
        fake_home,
        downloader=FakeDownloader({"https://example.test/tool.vsix": payload}),
        private_temp_root=paths.state_root / "tmp",
    )
    assert (
        installer.run_action(
            make_action(payload, required=False, size_delta=size_delta, digest=digest)
        ).state
        == "optional-failure"
    )
    assert runner.commands == []


def test_run_install_records_normalized_outcomes(
    fake_home: Path, tmp_path: Path
) -> None:
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
    with pytest.raises(ValueError):
        InstallAction(component_id="test", **{"argv": ("tool",), **kwargs})
