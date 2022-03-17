import sys
from runtime_env import RuntimeEnvironment
from packaging import tags
import os
import pytest


cvmfs = pytest.mark.skipif(
    not os.path.isdir("/cvmfs"), reason="tests for /cvmfs only"
)
venv = pytest.mark.skipif(
    os.environ.get("VIRTUAL_ENV") is None, reason="No virtual env are activated."
)


def test_wheelhouse_default(monkeypatch):
    """
    Test that the default wheelhouse is /cvmfs/soft.computecanada.ca/custom/python/wheelhouse
    """
    monkeypatch.delenv("WHEELHOUSE", raising=False)
    assert RuntimeEnvironment().wheelhouse == "/cvmfs/soft.computecanada.ca/custom/python/wheelhouse"


def test_wheelhouse_variable(monkeypatch):
    """
    Test that the wheelhouse is read from WHEELHOUSE enviroment variable.
    """
    monkeypatch.setenv("WHEELHOUSE", "potato/house/")
    assert RuntimeEnvironment().wheelhouse == "potato/house/"


def test_pip_config_file_default(monkeypatch):
    """
    Test that the default pip_config_file is None
    """
    monkeypatch.delenv("PIP_CONFIG_FILE", raising=False)
    assert RuntimeEnvironment().pip_config_file is None


def test_pip_config_file_variable(monkeypatch):
    """
    Test that the pip config file is read from PIP_CONFIG_FILE enviroment variable.
    """
    monkeypatch.setenv("PIP_CONFIG_FILE", "pip.conf")
    assert RuntimeEnvironment().pip_config_file == "pip.conf"


def test_current_python_default(monkeypatch):
    """
    Test that the default current_python is None
    """
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.delenv("EBVERSIONPYTHON", raising=False)

    assert RuntimeEnvironment().current_python is None


@pytest.mark.parametrize("input,expected", [
    ("3.8.2", "3.8"),
    ("3.10.2", "3.10"),
])
def test_current_python_variable_module(monkeypatch, input, expected):
    """
    Test that the current python version is read from EBVERSIONPYTHON enviroment variable.
    """
    monkeypatch.setenv("EBVERSIONPYTHON", input)
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)

    assert RuntimeEnvironment().current_python == expected


@venv
def test_current_python_variable_venv(monkeypatch):
    """
    Test that the current python version is read from VIRTUAL_ENV enviroment variable.
    """
    monkeypatch.delenv("EBVERSIONPYTHON", raising=False)
    assert RuntimeEnvironment().current_python == f"{sys.version_info.major}.{sys.version_info.minor}"

    # Ensure virtual env python has priority
    monkeypatch.setenv("EBVERSIONPYTHON", "3.10.2")
    assert RuntimeEnvironment().current_python == f"{sys.version_info.major}.{sys.version_info.minor}"


def test_python_dirs_default(monkeypatch):
    """
    Test that the default python directories is from
        /cvmfs/soft.computecanada.ca/easybuild/software/20*/Core/python:/cvmfs/soft.computecanada.ca/easybuild/software/20*/*/Core/python
    """
    monkeypatch.delenv("PYTHON_DIRS", raising=False)
    assert RuntimeEnvironment().python_directories == ":".join(
        [
            "/cvmfs/soft.computecanada.ca/easybuild/software/20*/Core/python",
            "/cvmfs/soft.computecanada.ca/easybuild/software/20*/*/Core/python",
        ]
    )


def test_python_dirs_variable(monkeypatch):
    """
    Test that the python directories is read from PYTHON_DIRS enviroment variable.
    """
    monkeypatch.setenv("PYTHON_DIRS", "potato/dir/")
    assert RuntimeEnvironment().python_directories == "potato/dir/"


def test_current_architecture_default(monkeypatch):
    """
    Test that the default current architecture is None when RSNT_ARCH is not defined
    """
    monkeypatch.delenv("RSNT_ARCH", raising=False)
    assert RuntimeEnvironment().current_architecture is None


def test_current_architecture_variable(monkeypatch):
    """
    Test that the current architecture is read from RSNT_ARCH enviroment variable.
    """
    arch = "generic"
    monkeypatch.setenv("RSNT_ARCH", arch)
    assert RuntimeEnvironment().current_architecture == arch


def test_available_architectures(monkeypatch):
    """
    Test that the default available_architectures is a frozenset(['avx', 'avx2', 'avx512', 'generic', 'sse3'])
    """
    assert isinstance(RuntimeEnvironment().available_architectures, frozenset)
    assert RuntimeEnvironment().available_architectures == frozenset(
        ["avx", "avx2", "avx512", "generic", "sse3"]
    )


def test_available_pythons(monkeypatch, tmp_path):
    """
    Test that the default available pythons versions are from tmp directory.
    """
    pd = tmp_path / "python/2017"
    for d in ["2.7.18", "3.7.4", "3.8.2"]:
        (pd / d).mkdir(parents=True)

    monkeypatch.setenv("PYTHON_DIRS", f"{str(tmp_path)}/python/2017")
    assert RuntimeEnvironment().available_pythons == ["2.7", "3.7", "3.8"]

    pd = tmp_path / "python/2021"
    (pd / "3.9.6").mkdir(parents=True)

    monkeypatch.setenv("PYTHON_DIRS", f"{str(tmp_path)}/python/2017:{str(tmp_path)}/python/2021")
    assert RuntimeEnvironment().available_pythons == ["2.7", "3.7", "3.8", "3.9"]


@cvmfs
def test_available_pythons_cvmfs(monkeypatch):
    """
    Test that the default available pythons versions are from CVMFS.
    """
    monkeypatch.delenv("PYTHON_DIRS", raising=False)
    assert RuntimeEnvironment().available_pythons == ["2.7", "3.5", "3.6", "3.7", "3.8", "3.9"]


def test_compatible_tags():
    """
    Test the python 3.8 compatible tags.
    """
    python = "3.8"
    platform = list(tags._generic_platforms())[0]
    other = frozenset(
        [
            tags.Tag("cp38", "cp38", platform),
            tags.Tag("cp38", "abi3", platform),
            tags.Tag("cp38", "none", platform),
            tags.Tag("py38", "none", platform),
            tags.Tag("py3", "none", platform),
            tags.Tag("py38", "none", "any"),
            tags.Tag("py3", "none", "any"),
        ]
    )
    env = RuntimeEnvironment()

    assert isinstance(env.compatible_tags, dict)
    assert isinstance(env.compatible_tags[python], frozenset)
    assert env.compatible_tags[python] == other
