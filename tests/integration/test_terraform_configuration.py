import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

TERRAFORM_DIRECTORIES = [
    REPOSITORY_ROOT / "infrastructure" / "terraform",
    REPOSITORY_ROOT / "infrastructure" / "bootstrap" / "state-backend",
]


def run_terraform(directory: Path, *arguments: str) -> subprocess.CompletedProcess:
    if shutil.which("terraform") is None:
        pytest.skip("Terraform is not installed or is not available on PATH")

    return subprocess.run(
        ["terraform", *arguments],
        cwd=directory,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("terraform_directory", TERRAFORM_DIRECTORIES)
def test_terraform_directory_exists(terraform_directory: Path):
    assert (
        terraform_directory.is_dir()
    ), f"Terraform directory does not exist: {terraform_directory}"


@pytest.mark.parametrize("terraform_directory", TERRAFORM_DIRECTORIES)
def test_terraform_formatting(terraform_directory: Path):
    result = run_terraform(
        terraform_directory,
        "fmt",
        "-check",
        "-diff",
        "-no-color",
    )

    assert result.returncode == 0, (
        f"Terraform formatting failed in {terraform_directory}\n\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )


@pytest.mark.parametrize("terraform_directory", TERRAFORM_DIRECTORIES)
def test_terraform_configuration_is_valid(terraform_directory: Path):
    result = run_terraform(
        terraform_directory,
        "validate",
        "-no-color",
    )

    assert result.returncode == 0, (
        f"Terraform validation failed in {terraform_directory}\n\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )
