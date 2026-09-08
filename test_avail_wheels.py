from io import StringIO
from argparse import ArgumentError
from contextlib import redirect_stderr
from fnmatch import translate
import re
import os
import avail_wheels
from runtime_env import RuntimeEnvironment
from collections import defaultdict
import packaging
from wild_requirements import Requirement
import pytest
from pytest_unordered import unordered

TEST_STACKS = ["generic", "nix", "gentoo"]
TEST_ARCHS = ["avx2", "generic"]

cvmfs = pytest.mark.skipif(
    not os.path.isdir("/cvmfs"), reason="tests for /cvmfs only"
)
venv = pytest.mark.skipif(
    os.environ.get("VIRTUAL_ENV") is None, reason="No virtual env are activated."
)


@pytest.fixture
def wheelhouse(tmp_path):
    _wheelhouse = {
        "generic/generic": [
            "pydicom-1.1.0-1-py2.py3-none-any.whl",
            "pydicom-0.9.9-py3-none-any.whl",
            "shiboken2-5.15.0-5.15.0-cp35.cp36.cp37.cp38-abi3-linux_x86_64.whl",
            "shiboken2-5.15.0-5.15.0-cp27-cp27mu-linux_x86_64.whl",
            "extension_helpers-0.0.0-py3-none-any.whl",
            "path.py-12.5.0-py3-none-any.whl",
        ],
        "nix/avx2": [
            "tensorflow_gpu-1.8.0+computecanada-cp27-cp27mu-linux_x86_64.whl",
            "tensorflow_gpu-1.8.0+computecanada-cp35-cp35m-linux_x86_64.whl",
            "tensorflow_gpu-1.8.0+computecanada-cp36-cp36m-linux_x86_64.whl",
        ],
        "nix/generic": [
            "scipy-1.1.0-cp27-cp27mu-linux_x86_64.whl",
            "scipy-1.1.0-cp35-cp35m-linux_x86_64.whl",
            "scipy-1.1.0-cp36-cp36m-linux_x86_64.whl",
            "scipy-1.1.0-cp37-cp37m-linux_x86_64.whl",
        ],
        "gentoo/avx2": [
            "tensorflow_gpu-1.8.0+computecanada-cp27-cp27mu-linux_x86_64.whl",
            "tensorflow_gpu-1.8.0+computecanada-cp35-cp35m-linux_x86_64.whl",
            "tensorflow_gpu-1.8.0+computecanada-cp36-cp36m-linux_x86_64.whl",
        ],
        "gentoo/generic": [
            "scipy-1.1.0-cp27-cp27mu-linux_x86_64.whl",
            "scipy-1.1.0-cp35-cp35m-linux_x86_64.whl",
            "scipy-1.1.0-cp36-cp36m-linux_x86_64.whl",
            "scipy-1.1.0-cp37-cp37m-linux_x86_64.whl",
            "scipy-1.7.0-cp35-cp35m-linux_x86_64.whl",
            "scipy-1.7.0-cp36-cp36m-linux_x86_64.whl",
            "scipy-1.7.0-cp37-cp37m-linux_x86_64.whl",
        ],
    }

    for directory, filenames in _wheelhouse.items():
        (tmp_path / directory).mkdir(parents=True)
        for file in filenames:
            (tmp_path / directory / file).touch()

    return tmp_path


@pytest.fixture
def pip_config_file(tmp_path):
    content = f"[wheel]\nfind-links = {str(tmp_path)}/wheelhouse/gentoo/avx2 {str(tmp_path)}/wheelhouse/gentoo/generic {str(tmp_path)}/wheelhouse/generic"

    p = tmp_path / "avail_wheels_pip.cfg"
    p.write_text(content)

    return p


@pytest.fixture
def python_dirs(monkeypatch, tmp_path):
    pd = tmp_path / "python/2017"
    for d in ["2.7.18", "3.7.4", "3.8.2"]:
        (pd / d).mkdir(parents=True)

    pd = tmp_path / "python/2021"
    (pd / "3.9.6").mkdir(parents=True)

    monkeypatch.setenv("PYTHON_DIRS", f"{str(tmp_path)}/python/2017:{str(tmp_path)}/python/2021")


def test_wheel_ctor_kwargs():
    """
    Test that Wheel constructor set correctly and exactly all given properties.
    """
    tags = packaging.tags.parse_tag("cp36-cp36m-linux_x86_64")
    wheel = avail_wheels.Wheel(
        filename="torch_cpu-1.2.0+computecanada-cp36-cp36m-linux_x86_64.whl",
        arch="avx",
        name="torch_cpu",
        version="1.2.0+computecanada",
        build="",
        tags=tags,
    )
    assert wheel.filename == "torch_cpu-1.2.0+computecanada-cp36-cp36m-linux_x86_64.whl"
    assert wheel.arch == "avx"
    assert wheel.name == "torch_cpu"
    assert wheel.namelower == "torch_cpu"
    assert wheel.canonical_name == "torch-cpu"
    assert wheel.loose_version == packaging.version.Version("1.2.0+computecanada")
    assert wheel.version == "1.2.0"
    assert wheel.localversion == "computecanada"
    assert wheel.build == ""
    assert wheel.tags == tags
    assert wheel.python == "cp36"
    assert wheel.abi == "cp36m"
    assert wheel.platform == "linux_x86_64"


def test_wheel_parse_tags():
    """
    Test that Wheel parse_wheel_filename correctly parse wheel parts.
    """
    filenames = [
        ("avx2", "netCDF4-1.3.1-cp36-cp36m-linux_x86_64.whl"),
        ("avx", "tensorflow_cpu-1.6.0+computecanada-cp36-cp36m-linux_x86_64.whl"),
        ("generic", "backports.functools_lru_cache-1.4-py2.py3-none-any.whl"),
        ("sse3", "Shapely-1.6.2.post1-cp35-cp35m-linux_x86_64.whl"),
        ("generic", "shiboken2-5.15.0-5.15.0-cp35.cp36.cp37.cp38-abi3-linux_x86_64.whl"),
        ("avx2", "torch_scatter-2.1.2+torch210.computecanada-cp311-cp311-linux_x86_64.whl"),
    ]
    tags = {
        filenames[0][1]: {
            "arch": "avx2",
            "name": "netCDF4",
            "namelower": "netcdf4",
            "canonical_name": "netcdf4",
            "version": "1.3.1",
            "localversion": None,
            "build": "",
            "python": "cp36",
            "abi": "cp36m",
            "platform": "linux_x86_64",
        },
        filenames[1][1]: {
            "arch": "avx",
            "name": "tensorflow_cpu",
            "namelower": "tensorflow_cpu",
            "canonical_name": "tensorflow-cpu",
            "version": "1.6.0",
            "localversion": "computecanada",
            "build": "",
            "python": "cp36",
            "abi": "cp36m",
            "platform": "linux_x86_64",
        },
        filenames[2][1]: {
            "arch": "generic",
            "name": "backports.functools_lru_cache",
            "namelower": "backports.functools_lru_cache",
            "canonical_name": "backports-functools-lru-cache",
            "version": "1.4",
            "localversion": None,
            "build": "",
            "python": "py2,py3",
            "abi": "none",
            "platform": "any",
        },
        filenames[3][1]: {
            "arch": "sse3",
            "name": "Shapely",
            "namelower": "shapely",
            "canonical_name": "shapely",
            "version": "1.6.2.post1",
            "localversion": None,
            "build": "",
            "python": "cp35",
            "abi": "cp35m",
            "platform": "linux_x86_64",
        },
        filenames[4][1]: {
            "arch": "generic",
            "name": "shiboken2",
            "namelower": "shiboken2",
            "canonical_name": "shiboken2",
            "version": "5.15.0",
            "localversion": None,
            "build": "5.15.0",
            "python": "cp35,cp36,cp37,cp38",
            "abi": "abi3",
            "platform": "linux_x86_64",
        },
        filenames[5][1]: {
            "arch": "avx2",
            "name": "torch_scatter",
            "namelower": "torch_scatter",
            "canonical_name": "torch-scatter",
            "version": "2.1.2",
            "localversion": "torch210.computecanada",
            "build": "",
            "python": "cp311",
            "abi": "cp311",
            "platform": "linux_x86_64",
        },
    }

    for arch, file in filenames:
        wheel = avail_wheels.Wheel.parse_wheel_filename(filename=file, arch=arch)
        assert wheel.filename == file
        assert wheel.arch == tags[file]["arch"]
        assert wheel.name == tags[file]["name"]
        assert wheel.namelower == tags[file]["namelower"]
        assert wheel.canonical_name == tags[file]["canonical_name"]
        assert wheel.version == tags[file]["version"]
        assert wheel.localversion == tags[file]["localversion"]
        assert wheel.build == tags[file]["build"]
        assert wheel.python == tags[file]["python"]
        assert wheel.abi == tags[file]["abi"]
        assert wheel.platform == tags[file]["platform"]


def test_wheel_loose_version():
    """Test that the string repr of version is a parsed version."""
    wheel = avail_wheels.Wheel(version="1.2+cc")
    loose_version = wheel.loose_version

    assert isinstance(loose_version, packaging.version.Version)
    assert loose_version == packaging.version.Version("1.2+cc")


def test_latest_versions_method_all_pythons():
    """
    Test that the latest version are returned.
    """
    wheels = {
        "netCDF4": [
            avail_wheels.Wheel.parse_wheel_filename("netCDF4-1.3.2-cp36-cp36m-linux_x86_64.whl", "avx2"),
            avail_wheels.Wheel.parse_wheel_filename("netCDF4-1.3.2-cp35-cp35m-linux_x86_64.whl", "avx2"),
            avail_wheels.Wheel.parse_wheel_filename("netCDF4-1.3.2-cp27-cp27mu-linux_x86_64.whl", "avx2"),
            avail_wheels.Wheel.parse_wheel_filename("netCDF4-1.3.1-cp36-cp36m-linux_x86_64.whl", "avx2"),
            avail_wheels.Wheel.parse_wheel_filename("netCDF4-1.3.1-cp36-cp36m-linux_x86_64.whl", "avx2"),
            avail_wheels.Wheel.parse_wheel_filename("netCDF4-1.3.1-cp36-cp36m-linux_x86_64.whl", "avx2"),
            avail_wheels.Wheel.parse_wheel_filename("netCDF4-1.2.0-cp36-cp36m-linux_x86_64.whl", "avx2"),
            avail_wheels.Wheel.parse_wheel_filename("netCDF4-1.3-cp36-cp36m-linux_x86_64.whl", "avx2"),
        ],
        "torch_cpu": [
            avail_wheels.Wheel.parse_wheel_filename("torch_cpu-0.4.0-cp36-cp36m-linux_x86_64.whl", "avx2")
        ],
        "pydicom": [
            avail_wheels.Wheel.parse_wheel_filename("pydicom-1.1.0-1-py3-none-any.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("pydicom-1.1.0-1-py2-none-any.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("pydicom-0.9.9-py3-none-any.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("pydicom-0.9.9-py2-none-any.whl", "generic"),
        ],
        "tensorflow_gpu": [
            avail_wheels.Wheel.parse_wheel_filename("tensorflow_gpu-1.8.0+computecanada-cp36-cp36m-linux_x86_64.whl", "avx2"),
            avail_wheels.Wheel.parse_wheel_filename("tensorflow_gpu-1.8.0+computecanada-cp35-cp35m-linux_x86_64.whl", "avx2"),
            avail_wheels.Wheel.parse_wheel_filename("tensorflow_gpu-1.8.0+computecanada-cp27-cp27mu-linux_x86_64.whl", "avx2"),
            avail_wheels.Wheel.parse_wheel_filename("tensorflow_gpu-1.8.0-cp36-cp36m-linux_x86_64.whl", "avx2"),
            avail_wheels.Wheel.parse_wheel_filename("tensorflow_gpu-1.7.0+computecanada-cp36-cp36m-linux_x86_64.whl", "avx2"),
        ],
    }

    wheels["netCDF4"].reverse()
    wheels["pydicom"].reverse()
    wheels["tensorflow_gpu"].reverse()

    latest_wheels = {
        "netCDF4": [
            avail_wheels.Wheel.parse_wheel_filename("netCDF4-1.3.2-cp27-cp27mu-linux_x86_64.whl", "avx2"),
            avail_wheels.Wheel.parse_wheel_filename("netCDF4-1.3.2-cp35-cp35m-linux_x86_64.whl", "avx2"),
            avail_wheels.Wheel.parse_wheel_filename("netCDF4-1.3.2-cp36-cp36m-linux_x86_64.whl", "avx2"),
        ],
        "torch_cpu": [
            avail_wheels.Wheel.parse_wheel_filename("torch_cpu-0.4.0-cp36-cp36m-linux_x86_64.whl", "avx2")
        ],
        "pydicom": [
            avail_wheels.Wheel.parse_wheel_filename("pydicom-1.1.0-1-py2-none-any.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("pydicom-1.1.0-1-py3-none-any.whl", "generic"),
        ],
        "tensorflow_gpu": [
            avail_wheels.Wheel.parse_wheel_filename("tensorflow_gpu-1.8.0+computecanada-cp27-cp27mu-linux_x86_64.whl", "avx2"),
            avail_wheels.Wheel.parse_wheel_filename("tensorflow_gpu-1.8.0+computecanada-cp35-cp35m-linux_x86_64.whl", "avx2"),
            avail_wheels.Wheel.parse_wheel_filename("tensorflow_gpu-1.8.0+computecanada-cp36-cp36m-linux_x86_64.whl", "avx2"),
        ],
    }

    assert avail_wheels.latest_versions(wheels) == latest_wheels


def test_latest_versions_type():
    """ Test that latest_versions method return type is a defaultdict. """
    assert isinstance(avail_wheels.latest_versions({}), defaultdict)


def test_latest_versions_semantic_versioning():
    """
    Test that latest_versions uses PEP 440 semantic version comparison rather than
    alphabetical string sorting when version numbers cross decimal / digit boundaries:
      - cf_xarray: 0.10.11 > 0.9.5  (string comparison incorrectly picks 0.9.5)
      - botocore:  1.42.49 > 1.9.5   (string comparison incorrectly picks 1.9.5)
      - boto3:     1.42.30 > 1.9.86  (string comparison incorrectly picks 1.9.86)
    """
    wheels = {
        "cf_xarray": [
            avail_wheels.Wheel.parse_wheel_filename("cf_xarray-0.9.5+computecanada-py3-none-any.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("cf_xarray-0.10.11+computecanada-py3-none-any.whl", "generic"),
        ],
        "botocore": [
            avail_wheels.Wheel.parse_wheel_filename("botocore-1.9.5+computecanada-py2.py3-none-any.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("botocore-1.10.63+computecanada-py2.py3-none-any.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("botocore-1.42.49+computecanada-py3-none-any.whl", "generic"),
        ],
        "boto3": [
            avail_wheels.Wheel.parse_wheel_filename("boto3-1.9.86+computecanada-py2.py3-none-any.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("boto3-1.9.235+computecanada-py2.py3-none-any.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("boto3-1.42.30+computecanada-py3-none-any.whl", "generic"),
        ],
    }

    expected = {
        "cf_xarray": [
            avail_wheels.Wheel.parse_wheel_filename("cf_xarray-0.10.11+computecanada-py3-none-any.whl", "generic"),
        ],
        "botocore": [
            avail_wheels.Wheel.parse_wheel_filename("botocore-1.42.49+computecanada-py3-none-any.whl", "generic"),
        ],
        "boto3": [
            avail_wheels.Wheel.parse_wheel_filename("boto3-1.42.30+computecanada-py3-none-any.whl", "generic"),
        ],
    }

    assert avail_wheels.latest_versions(wheels) == expected


def test_latest_versions_preserves_multiple_wheels_at_latest_version():
    """
    Test that when the latest semantic version has builds for multiple Python tags
    or architectures, all matching wheels are preserved.
    """
    wheels = {
        "botocore": [
            avail_wheels.Wheel.parse_wheel_filename("botocore-1.9.5+computecanada-py2.py3-none-any.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("botocore-1.42.49+computecanada-cp38-cp38-linux_x86_64.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("botocore-1.42.49+computecanada-cp39-cp39-linux_x86_64.whl", "generic"),
        ]
    }
    latests = avail_wheels.latest_versions(wheels)

    assert len(latests["botocore"]) == 2
    assert {w.python for w in latests["botocore"]} == {"cp38", "cp39"}
    assert all(w.version == "1.42.49" for w in latests["botocore"])


def test_sort_type():
    """ Test that sort method return type is a list. """
    assert isinstance(avail_wheels.sort({}, None), list)


def test_sort_build_tag():
    """Test that wheels with build tags sort descending by build tag."""
    wheels = {
        "pydicom": [
            avail_wheels.Wheel.parse_wheel_filename("pydicom-1.1.0-1-py2.py3-none-any.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("pydicom-1.1.0-2-py2.py3-none-any.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("pydicom-1.1.0-py2.py3-none-any.whl", "generic"),
        ],
        "name": [
            avail_wheels.Wheel.parse_wheel_filename("name-1.1-10-py2.py3-none-any.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("name-1.1-9-py2.py3-none-any.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("name-1.1-8-py2.py3-none-any.whl", "generic"),
        ],
    }
    # Row-by-row sort
    assert avail_wheels.sort(wheels, ["name", "version", "build"]) == [
        ["name", "1.1", "10"],
        ["name", "1.1", "9"],
        ["name", "1.1", "8"],
        ["pydicom", "1.1.0", "2"],
        ["pydicom", "1.1.0", "1"],
        ["pydicom", "1.1.0", ""],
    ]

    # Condensed view
    assert avail_wheels.sort(wheels, ["name", "version", "build"], condense=True) == [
        ["name", "1.1", "10, 9, 8"],
        ["pydicom", "1.1.0", "2, 1, "],
    ]


def test_sort_version_semantic_not_alphabetical():
    """
    Test that versions are sorted by PEP 440 semantic order
    (1.10.0 > 1.9.0 > 1.2.0 > 1.2.0a1) rather than lexicographical order (1.9.0 > 1.2.0 > 1.10.0).
    """
    wheels = {
        "demo": [
            avail_wheels.Wheel.parse_wheel_filename("demo-1.2.0-py3-none-any.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("demo-1.10.0-py3-none-any.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("demo-1.9.0-py3-none-any.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("demo-1.2.0a1-py3-none-any.whl", "generic"),
        ]
    }

    # Columns view
    assert avail_wheels.sort(wheels, ["name", "version"], condense=False) == [
        ["demo", "1.10.0"],
        ["demo", "1.9.0"],
        ["demo", "1.2.0"],
        ["demo", "1.2.0a1"],
    ]

    # Condensed view
    assert avail_wheels.sort(wheels, ["name", "version"], condense=True) == [
        ["demo", "1.10.0, 1.9.0, 1.2.0, 1.2.0a1"]
    ]


def test_sort_case_insensitive_name_order():
    """Test that package names sort case-insensitively ascending (str.casefold)."""
    wheels = {
        "scipy": [avail_wheels.Wheel.parse_wheel_filename("scipy-1.0.0-py3-none-any.whl", "generic")],
        "NetCDF4": [avail_wheels.Wheel.parse_wheel_filename("NetCDF4-1.0.0-py3-none-any.whl", "generic")],
        "arrow": [avail_wheels.Wheel.parse_wheel_filename("arrow-1.0.0-py3-none-any.whl", "generic")],
        "PyDICOM": [avail_wheels.Wheel.parse_wheel_filename("PyDICOM-1.0.0-py3-none-any.whl", "generic")],
    }
    result = avail_wheels.sort(wheels, ["name"], condense=True)
    assert result == [
        ["arrow"],
        ["NetCDF4"],
        ["PyDICOM"],
        ["scipy"],
    ]


def test_sort_multi_key_precedence():
    """
    Test tie-breaking precedence:
    1. Version descending
    2. Architecture descending
    3. Python version descending
    """
    wheels = {
        "pkg": [
            # Same version (1.0), different arch
            avail_wheels.Wheel.parse_wheel_filename("pkg-1.0-cp38-cp38-linux_x86_64.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("pkg-1.0-cp38-cp38-linux_x86_64.whl", "sse3"),
            avail_wheels.Wheel.parse_wheel_filename("pkg-1.0-cp38-cp38-linux_x86_64.whl", "avx2"),
            # Same version (1.0), same arch (avx2), different pythons
            avail_wheels.Wheel.parse_wheel_filename("pkg-1.0-cp311-cp311-linux_x86_64.whl", "avx2"),
            avail_wheels.Wheel.parse_wheel_filename("pkg-1.0-cp39-cp39-linux_x86_64.whl", "avx2"),
            # Higher version (2.0) should be first regardless of arch
            avail_wheels.Wheel.parse_wheel_filename("pkg-2.0-cp38-cp38-linux_x86_64.whl", "generic"),
        ]
    }

    assert avail_wheels.sort(wheels, ["name", "version", "arch", "python"]) == [
        ["pkg", "2.0", "generic", "cp38"],
        ["pkg", "1.0", "sse3", "cp38"],
        ["pkg", "1.0", "generic", "cp38"],
        ["pkg", "1.0", "avx2", "cp311"],
        ["pkg", "1.0", "avx2", "cp39"],
        ["pkg", "1.0", "avx2", "cp38"],
    ]


def test_sort_removes_duplicate_rows():
    """
    Test that selecting a column subset deduplicates rows that become identical.
    """
    wheels = {
        "numpy": [
            avail_wheels.Wheel.parse_wheel_filename("numpy-1.25.0-cp39-cp39-linux_x86_64.whl", "avx2"),
            avail_wheels.Wheel.parse_wheel_filename("numpy-1.25.0-cp39-cp39-linux_x86_64.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("numpy-1.25.0-cp310-cp310-linux_x86_64.whl", "avx2"),
            avail_wheels.Wheel.parse_wheel_filename("numpy-1.24.0-cp39-cp39-linux_x86_64.whl", "generic"),
        ]
    }
    # When only requesting ['name', 'version'], multiple 1.25.0 wheels collapse into one row
    assert avail_wheels.sort(wheels, ["name", "version"]) == [
        ["numpy", "1.25.0"],
        ["numpy", "1.24.0"],
    ]


@pytest.mark.parametrize(
    "columns, expected_row",
    [
        (["name", "version"], ["pkg", "1.0.0"]),
        (["version", "name"], ["1.0.0", "pkg"]),
        (["arch", "python", "version", "name"], ["generic", "cp39", "1.0.0", "pkg"]),
        (["platform", "abi", "build"], ["linux_x86_64", "cp39", ""]),
    ],
)
def test_sort_arbitrary_column_order(columns, expected_row):
    """Test that output columns strictly follow the requested column ordering."""
    wheels = {"pkg": [avail_wheels.Wheel.parse_wheel_filename("pkg-1.0.0-cp39-cp39-linux_x86_64.whl", "generic")]}
    assert avail_wheels.sort(wheels, columns) == [expected_row]


def test_sort_condense_all_columns():
    """
    Test that sort with condense=True works across all AVAILABLE_HEADERS:
    ['name', 'version', 'localversion', 'build', 'python', 'abi', 'platform', 'arch']
    """
    wheels = {
        "netCDF4": [
            avail_wheels.Wheel.parse_wheel_filename("netCDF4-1.3.1-cp27-cp27mu-linux_x86_64.whl", "avx"),
            avail_wheels.Wheel.parse_wheel_filename("netCDF4-1.3.1-cp35-cp35m-linux_x86_64.whl", "avx"),
            avail_wheels.Wheel.parse_wheel_filename("netCDF4-1.3.1-cp36-cp36m-linux_x86_64.whl", "avx"),
            avail_wheels.Wheel.parse_wheel_filename("netCDF4-1.3.1-cp27-cp27mu-linux_x86_64.whl", "avx2"),
            avail_wheels.Wheel.parse_wheel_filename("netCDF4-1.3.1-cp35-cp35m-linux_x86_64.whl", "avx2"),
            avail_wheels.Wheel.parse_wheel_filename("netCDF4-1.3.1-cp36-cp36m-linux_x86_64.whl", "avx2"),
            avail_wheels.Wheel.parse_wheel_filename("netCDF4-1.3.1-cp27-cp27mu-linux_x86_64.whl", "sse3"),
            avail_wheels.Wheel.parse_wheel_filename("netCDF4-1.3.1-cp35-cp35m-linux_x86_64.whl", "sse3"),
            avail_wheels.Wheel.parse_wheel_filename("netCDF4-1.3.1-cp36-cp36m-linux_x86_64.whl", "sse3"),
            avail_wheels.Wheel.parse_wheel_filename("netCDF4-1.4.0-cp27-cp27mu-linux_x86_64.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("netCDF4-1.2.8-cp27-cp27mu-linux_x86_64.whl", "generic"),
        ],
        "botocore": [
            avail_wheels.Wheel.parse_wheel_filename("botocore-1.10.63-py2.py3-none-any.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("botocore-1.9.5-py2.py3-none-any.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("botocore-1.10.57-py2.py3-none-any.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("botocore-1.9.11-py2.py3-none-any.whl", "generic"),
        ],
        "pydicom": [
            avail_wheels.Wheel.parse_wheel_filename("pydicom-1.1.0-1-py2.py3-none-any.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("pydicom-0.9.9-py3-none-any.whl", "generic"),
        ],
        "torch_cpu": [
            avail_wheels.Wheel.parse_wheel_filename("torch_cpu-0.4.0-cp36-cp36m-linux_x86_64.whl", "avx2"),
            avail_wheels.Wheel.parse_wheel_filename("torch_cpu-0.2.0+d8f3c60-cp27-cp27mu-linux_x86_64.whl", "avx2"),
        ],
    }

    assert avail_wheels.sort(wheels, avail_wheels.AVAILABLE_HEADERS, condense=True) == [
        ["botocore", "1.10.63, 1.10.57, 1.9.11, 1.9.5", "", "", "py2,py3", "none", "any", "generic"],
        ["netCDF4", "1.4.0, 1.3.1, 1.2.8", "", "", "cp36, cp35, cp27", "cp36m, cp35m, cp27mu", "linux_x86_64", "sse3, generic, avx2, avx"],
        ["pydicom", "1.1.0, 0.9.9", "", "1, ", "py3, py2,py3", "none", "any", "generic"],
        ["torch_cpu", "0.4.0, 0.2.0", "d8f3c60, ", "", "cp36, cp27", "cp36m, cp27mu", "linux_x86_64", "avx2"],
    ]


def test_sort_empty():
    """Test sort with empty dict and empty wheel list."""
    assert avail_wheels.sort({}, ["name", "version"]) == []
    assert avail_wheels.sort({"pkg": []}, ["name", "version"]) == []


def test_sort_unavailable_wheels_with_empty_fields():
    """
    Test sorting wheels that have empty attributes (such as not-available wheels).
    Should not raise AttributeError or InvalidVersion.
    """
    unavail_wheel = avail_wheels.Wheel(filename="missing_pkg", name="missing_pkg")
    wheels = {
        "missing_pkg": [unavail_wheel],
        "available_pkg": [
            avail_wheels.Wheel.parse_wheel_filename("available_pkg-2.0.0-py3-none-any.whl", "generic")
        ],
    }

    result = avail_wheels.sort(wheels, ["name", "version", "arch", "python"], condense=False)
    assert result == [
        ["available_pkg", "2.0.0", "generic", "py3"],
        ["missing_pkg", "", "", ""],
    ]


def test_sort_cpython_versions():
    """
    Test that Python versions >= 3.10 sort numerically descending in condensed view
    (cp311 > cp310 > cp39 > cp38) rather than alphabetically (cp39 > cp38 > cp311 > cp310).
    """
    wheels = {
        "xprec": [
            avail_wheels.Wheel.parse_wheel_filename("xprec-1.3.8-cp38-cp38-linux_x86_64.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("xprec-1.3.8-cp39-cp39-linux_x86_64.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("xprec-1.3.8-cp310-cp310-linux_x86_64.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("xprec-1.3.8-cp311-cp311-linux_x86_64.whl", "generic"),
        ]
    }

    assert avail_wheels.sort(wheels, ["name", "version", "python", "arch"], condense=True) == [
        ["xprec", "1.3.8", "cp311, cp310, cp39, cp38", "generic"]
    ]

    assert avail_wheels.sort(wheels, ["name", "version", "python", "arch"], condense=False) == [
        ["xprec", "1.3.8", "cp311", "generic"],
        ["xprec", "1.3.8", "cp310", "generic"],
        ["xprec", "1.3.8", "cp39", "generic"],
        ["xprec", "1.3.8", "cp38", "generic"],
    ]


def test_sort_multiple_localversion():
    """
    Test sorting wheels of the same package and version with multiple localversions,
    verifying both row-by-row and condensed sorting.
    """
    wheels = {
        "torch_scatter": [
            avail_wheels.Wheel.parse_wheel_filename(
                "torch_scatter-2.1.2+torch210.computecanada-cp311-cp311-linux_x86_64.whl", "generic"
            ),
            avail_wheels.Wheel.parse_wheel_filename(
                "torch_scatter-2.1.2+torch212.computecanada-cp311-cp311-linux_x86_64.whl", "generic"
            ),
            avail_wheels.Wheel.parse_wheel_filename(
                "torch_scatter-2.1.2+torch200.computecanada-cp311-cp311-linux_x86_64.whl", "generic"
            ),
        ]
    }

    # Row-by-row sort: local versions sort descending
    assert avail_wheels.sort(wheels, ["name", "version", "localversion", "python", "arch"], condense=False) == [
        ["torch_scatter", "2.1.2", "torch212.computecanada", "cp311", "generic"],
        ["torch_scatter", "2.1.2", "torch210.computecanada", "cp311", "generic"],
        ["torch_scatter", "2.1.2", "torch200.computecanada", "cp311", "generic"],
    ]

    # Condensed view: local versions joined and sorted descending
    assert avail_wheels.sort(wheels, ["name", "version", "localversion", "python", "arch"], condense=True) == [
        ["torch_scatter", "2.1.2", "torch212.computecanada, torch210.computecanada, torch200.computecanada", "cp311", "generic"],
    ]


# TODO: Add test for PIP_CONFIG_FILE=""
def test_get_wheels_all_archs_all_pythons(wheelhouse):
    """ Test that get wheels returns wheels for all arch and all pythons. """
    search_paths = [f"{str(wheelhouse)}/gentoo/{arch}" for arch in TEST_ARCHS]
    other = {
        "scipy": unordered([
            avail_wheels.Wheel.parse_wheel_filename("scipy-1.7.0-cp37-cp37m-linux_x86_64.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("scipy-1.7.0-cp36-cp36m-linux_x86_64.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("scipy-1.7.0-cp35-cp35m-linux_x86_64.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("scipy-1.1.0-cp37-cp37m-linux_x86_64.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("scipy-1.1.0-cp36-cp36m-linux_x86_64.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("scipy-1.1.0-cp35-cp35m-linux_x86_64.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("scipy-1.1.0-cp27-cp27mu-linux_x86_64.whl", "generic"),
        ]),
        "tensorflow-gpu": unordered([
            avail_wheels.Wheel.parse_wheel_filename("tensorflow_gpu-1.8.0+computecanada-cp36-cp36m-linux_x86_64.whl", "avx2"),
            avail_wheels.Wheel.parse_wheel_filename("tensorflow_gpu-1.8.0+computecanada-cp35-cp35m-linux_x86_64.whl", "avx2"),
            avail_wheels.Wheel.parse_wheel_filename("tensorflow_gpu-1.8.0+computecanada-cp27-cp27mu-linux_x86_64.whl", "avx2"),
        ]),
    }

    ret = avail_wheels.get_wheels(
        paths=search_paths,
        pythons=avail_wheels.env.available_pythons,
        reqs=None,
        latest=False,
    )
    assert ret == other


def test_get_wheels_arch_all_pythons(wheelhouse):
    """ Test that get wheels returns wheel for a given arch and all pythons. """
    arch = "generic"
    search_paths = [f"{str(wheelhouse)}/gentoo/{arch}"]
    other = {
        "scipy": unordered([
            avail_wheels.Wheel.parse_wheel_filename("scipy-1.7.0-cp37-cp37m-linux_x86_64.whl", arch),
            avail_wheels.Wheel.parse_wheel_filename("scipy-1.7.0-cp36-cp36m-linux_x86_64.whl", arch),
            avail_wheels.Wheel.parse_wheel_filename("scipy-1.7.0-cp35-cp35m-linux_x86_64.whl", arch),
            avail_wheels.Wheel.parse_wheel_filename("scipy-1.1.0-cp37-cp37m-linux_x86_64.whl", arch),
            avail_wheels.Wheel.parse_wheel_filename("scipy-1.1.0-cp36-cp36m-linux_x86_64.whl", arch),
            avail_wheels.Wheel.parse_wheel_filename("scipy-1.1.0-cp35-cp35m-linux_x86_64.whl", arch),
            avail_wheels.Wheel.parse_wheel_filename("scipy-1.1.0-cp27-cp27mu-linux_x86_64.whl", arch),
        ])
    }

    ret = avail_wheels.get_wheels(
        paths=search_paths,
        pythons=avail_wheels.env.available_pythons,
        reqs=None,
        latest=False,
    )
    assert ret == other


def test_get_wheels_exactname_arch_python(wheelhouse):
    """ Test that get wheels returns wheels for the exact requirements and python """
    arch = "generic"
    search_paths = [f"{str(wheelhouse)}/gentoo/{arch}"]
    pythons = ["3.6"]
    exactname = "scipy"
    other = {
        "scipy": unordered([
            avail_wheels.Wheel.parse_wheel_filename("scipy-1.7.0-cp36-cp36m-linux_x86_64.whl", arch),
            avail_wheels.Wheel.parse_wheel_filename("scipy-1.1.0-cp36-cp36m-linux_x86_64.whl", arch),
        ])
    }

    ret = avail_wheels.get_wheels(
        paths=search_paths,
        pythons=pythons,
        reqs=defaultdict(Requirement, {exactname: Requirement(exactname)}),
        latest=False,
    )
    assert ret == other


def test_get_wheels_wildname_arch_python(wheelhouse):
    """ Test that get wheels returns wheel for a wildcard named requirement. """
    arch = "generic"
    search_paths = [f"{str(wheelhouse)}/gentoo/{arch}"]
    pythons = ["3.6"]
    wildname = "*scipy*"
    other = {
        "scipy": unordered([
            avail_wheels.Wheel.parse_wheel_filename("scipy-1.7.0-cp36-cp36m-linux_x86_64.whl", arch),
            avail_wheels.Wheel.parse_wheel_filename("scipy-1.1.0-cp36-cp36m-linux_x86_64.whl", arch),
        ])
    }

    ret = avail_wheels.get_wheels(
        paths=search_paths,
        pythons=pythons,
        reqs=defaultdict(Requirement, {wildname: Requirement(wildname)}),
        latest=False,
    )
    assert ret == other


def test_get_wheels_wildname_arch_python_version(wheelhouse):
    """ Test that get wheels returns wheel for a wildcard named and specifier requirement. """
    arch = "generic"
    search_paths = [f"{str(wheelhouse)}/gentoo/{arch}"]
    pythons = ["3.6"]
    wildname = "*scipy*"
    version = "1.7.0"
    other = {
        "scipy": [
            avail_wheels.Wheel.parse_wheel_filename("scipy-1.7.0-cp36-cp36m-linux_x86_64.whl", arch)
        ]
    }

    ret = avail_wheels.get_wheels(
        paths=search_paths,
        pythons=pythons,
        reqs=defaultdict(Requirement, {wildname: Requirement(f"{wildname}=={version}")}),
        latest=False,
    )
    assert ret == other


def test_get_wheels_wildversion_wildname_arch_python(wheelhouse):
    """ Test that get wheels returns wheel for a wildcard name and wildcard specifier requirement. """
    search_paths = [f"{str(wheelhouse)}/gentoo/generic"]
    pythons = ["3.6"]
    wildname = "*scipy*"
    version = "1.1.*"
    other = {
        "scipy": [
            avail_wheels.Wheel.parse_wheel_filename("scipy-1.1.0-cp36-cp36m-linux_x86_64.whl", "generic")
        ]
    }

    ret = avail_wheels.get_wheels(
        paths=search_paths,
        pythons=pythons,
        reqs=defaultdict(Requirement, {wildname: Requirement(f"{wildname}=={version}")}),
        latest=False,
    )
    assert ret == other


def test_get_wheels_wrongversion_wildname_arch_python(wheelhouse):
    """ Test that get wheels do not returns wheel for a wildcard named requirement. """
    search_paths = [f"{str(wheelhouse)}/gentoo/avx2"]
    pythons = ["3.6"]
    wildname = "*scipy*"
    version = "2.3"
    other = {}

    ret = avail_wheels.get_wheels(
        paths=search_paths,
        pythons=pythons,
        reqs=defaultdict(Requirement, {wildname: Requirement(f"{wildname}=={version}")}),
        latest=False,
    )
    assert ret == other


def test_parse_args_default_arch():
    """ Test that default argument parser value for --arch is None """
    # TODO: monkeypatch
    assert avail_wheels.create_argparser().get_default("arch") is None


def test_parse_args_default_noarch(monkeypatch):
    """ Test that default argument parser value for --arch is None when RSNT_ARCH do not exists."""
    monkeypatch.delenv("RSNT_ARCH", raising=False)
    assert avail_wheels.create_argparser().get_default("arch") is None


def test_parse_args_default_python_venv(monkeypatch, tmp_path):
    """
    Test that default argument parser value for --python is provided by VIRTUAL_ENV.
    Uses a fake virtual environment with a pyvenv.cfg file.
    """
    fake_venv = tmp_path / "venv"
    fake_venv.mkdir()
    (fake_venv / "pyvenv.cfg").write_text("home = /fake/bin\nversion = 3.11.4\n")

    monkeypatch.setenv("VIRTUAL_ENV", str(fake_venv))
    monkeypatch.delenv("EBVERSIONPYTHON", raising=False)

    avail_wheels.env = RuntimeEnvironment()
    assert avail_wheels.create_argparser().get_default("python") == ["3.11"]


def test_parse_args_default_python_module(monkeypatch):
    """ Test that default argument parser value for --python is provided by EBVERSIONPYTHON. """
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.setenv("EBVERSIONPYTHON", "3.6.10")

    avail_wheels.env = RuntimeEnvironment()
    assert avail_wheels.create_argparser().get_default("python") == ["3.6"]


def test_parse_args_default_python_venv_precedence_over_module(monkeypatch, tmp_path):
    """
    Test that VIRTUAL_ENV has precedence over EBVERSIONPYTHON when a virtualenv
    is activated and a module with a different Python version is loaded.
    """
    fake_venv = tmp_path / "venv"
    fake_venv.mkdir()
    (fake_venv / "pyvenv.cfg").write_text("home = /fake/bin\nversion = 3.11.4\n")

    monkeypatch.setenv("VIRTUAL_ENV", str(fake_venv))
    monkeypatch.setenv("EBVERSIONPYTHON", "3.8.2")

    avail_wheels.env = RuntimeEnvironment()
    assert avail_wheels.env.current_python == "3.11"
    assert avail_wheels.create_argparser().get_default("python") == ["3.11"]


@cvmfs
def test_parse_args_default_nopython_cvmfs(monkeypatch):
    """ Test that default argument parser value for --python is from available pythons version."""
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.delenv("EBVERSIONPYTHON", raising=False)

    avail_wheels.env = RuntimeEnvironment()
    assert avail_wheels.create_argparser().get_default("python") == avail_wheels.env.available_pythons


def test_parse_args_default_nopython(monkeypatch, tmp_path):
    """ Test that default argument parser value for --python is from available pythons version."""
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.delenv("EBVERSIONPYTHON", raising=False)
    monkeypatch.setenv("PYTHON_DIRS", f"{str(tmp_path)}/python/2017")

    pd = tmp_path / "python/2017"
    for d in ["2.7.18", "3.7.4", "3.8.2"]:
        (pd / d).mkdir(parents=True)

    avail_wheels.env = RuntimeEnvironment()
    assert avail_wheels.create_argparser().get_default("python") == ["2.7", "3.7", "3.8"]


def test_parse_args_default_name():
    """ Test that default argument parser value for --name is an empty list."""
    assert avail_wheels.create_argparser().get_default("name") == []


def test_parse_args_default_wheel():
    """ Test that default argument parser value for positional wheel is None."""
    assert avail_wheels.create_argparser().get_default("wheel") is None


def test_parse_args_default_version():
    """ Test that default argument parser value for --version is None."""
    assert avail_wheels.create_argparser().get_default("version") is None


def test_parse_args_default_columns():
    """ Test that default argument parser value for --column are the available headers. """
    assert avail_wheels.create_argparser().get_default("column") == avail_wheels.HEADERS


def test_parse_args_default_all_versions():
    """ Test that default argument parser value for --all_version is False. """
    assert not avail_wheels.create_argparser().get_default("all_versions")


def test_parse_args_default_all_pythons():
    """ Test that default argument parser value for --all_python is False. """
    assert not avail_wheels.create_argparser().get_default("all_pythons")


def test_parse_args_default_all_archs():
    """ Test that default argument parser value for --all_archs is False. """
    assert not avail_wheels.create_argparser().get_default("all_archs")


def test_parse_args_default_raw():
    """ Test that default argument parser value for --raw is False. """
    assert not avail_wheels.create_argparser().get_default("raw")


def test_parse_args_default_mediawiki():
    """ Test that default argument parser value for --mediawiki is False. """
    assert not avail_wheels.create_argparser().get_default("mediawiki")


def test_parse_args_version():
    """ Test that --version is and support the wildcard version. """
    version = "1.2.*"
    args = avail_wheels.create_argparser().parse_args(["--version", version])
    assert isinstance(args.specifier, packaging.specifiers.SpecifierSet)
    assert args.specifier == packaging.specifiers.SpecifierSet(f"=={version}")


def test_parse_args_version_noarg():
    """ Test that --version raises when no argument are provided. """
    temp_stdout = StringIO()
    with redirect_stderr(temp_stdout):
        with pytest.raises(SystemExit):
            with pytest.raises(ArgumentError):
                avail_wheels.create_argparser().parse_args(["--version"])


def test_parse_args_all_versions():
    """ Test that --all_version is True when given. """
    args = avail_wheels.create_argparser().parse_args(["--all_version"])
    assert isinstance(args.all_versions, bool)
    assert args.all_versions


def test_parse_args_all_archs():
    """ Test that --all_arch is True when given. """
    args = avail_wheels.create_argparser().parse_args(["--all_archs"])
    assert isinstance(args.all_archs, bool)
    assert args.all_archs


@pytest.mark.skipif(int(os.environ.get('EBVERSIONGENTOO', -1)) != 2020, reason="StdEnv 2020 test")
def test_parse_args_many_arch():
    """ Test that --arch is a list of given values. """
    arch = ["avx2", "avx"]
    args = avail_wheels.create_argparser().parse_args(["--arch", *arch])
    assert isinstance(args.arch, list)
    assert args.arch == arch


def test_parse_args_arch_noarg():
    """ Test that --arch raises when no value is given. """
    temp_stdout = StringIO()
    with redirect_stderr(temp_stdout):
        with pytest.raises(SystemExit):
            with pytest.raises(ArgumentError):
                avail_wheels.create_argparser().parse_args(["--arch"])


def test_parse_args_many_python(python_dirs):
    """ Test that --python is a list of given values. """
    python = ["3.7", "3.8"]
    args = avail_wheels.create_argparser().parse_args(["--python", *python])
    assert isinstance(args.python, list)
    assert args.python == python


def test_parse_args_python_noarg():
    """ Test that --python raises when no value is given. """
    temp_stdout = StringIO()
    with redirect_stderr(temp_stdout):
        with pytest.raises(SystemExit):
            with pytest.raises(ArgumentError):
                avail_wheels.create_argparser().parse_args(["--python"])


def test_parse_args_all_pythons():
    """ Test that --all_python is True when given. """
    args = avail_wheels.create_argparser().parse_args(["--all_pythons"])
    assert isinstance(args.all_pythons, bool)
    assert args.all_pythons


def test_parse_args_names():
    """ Test that --name is a list of given values. """
    names = ["thename", "thename2"]
    args = avail_wheels.create_argparser().parse_args(["--name", *names])
    assert isinstance(args.name, list)
    assert [w.name for w in args.name] == names


def test_parse_args_name_noarg():
    """ Test that --name raises when no value is given. """
    temp_stdout = StringIO()
    with redirect_stderr(temp_stdout):
        with pytest.raises(SystemExit):
            with pytest.raises(ArgumentError):
                avail_wheels.create_argparser().parse_args(["--name"])


def test_parse_args_wheels():
    """ Test that positional wheel is a list of given values. """
    wheels = ["thename", "thename2"]
    args = avail_wheels.create_argparser().parse_args([*wheels])
    assert isinstance(args.wheel, list)
    assert [w.name for w in args.wheel] == wheels


def test_parse_args_wheel_noarg():
    """ Test that positional wheel is an empty list by default. """
    args = avail_wheels.create_argparser().parse_args([])
    assert isinstance(args.wheel, list)
    assert args.wheel == []


def test_parse_args_requirement_noarg():
    """ Test that --requirements raises when no value is given. """
    temp_stdout = StringIO()
    with redirect_stderr(temp_stdout):
        with pytest.raises(SystemExit):
            with pytest.raises(ArgumentError):
                avail_wheels.create_argparser().parse_args(["--requirement"])


def test_parse_args_requirement_files():
    """
    Test that --requirement is a list of given values..
    """
    args = avail_wheels.create_argparser().parse_args(["--requirement", "requirement.txt", "reqs.txt"])

    assert isinstance(args.requirements, list)
    assert args.requirements == ["requirement.txt", "reqs.txt"]


def test_parse_args_default_condense():
    """Test that default argument parser value for --condense is False."""
    assert not avail_wheels.create_argparser().get_default("condense")


def test_parse_args_condense():
    """Test that --condense sets condense to True."""
    args = avail_wheels.create_argparser().parse_args(["--condense"])
    assert isinstance(args.condense, bool)
    assert args.condense


def test_is_compatible_true(python_dirs):
    """ Test that wheel is compatible. """
    avail_wheels.env = RuntimeEnvironment()
    wheel = avail_wheels.Wheel.parse_wheel_filename("netCDF4-1.3.1-cp27-cp27mu-linux_x86_64.whl")
    python_tags = avail_wheels.env.compatible_tags["2.7"]
    assert avail_wheels.is_compatible(wheel, python_tags)


def test_is_compatible_compressed_tags_true(python_dirs):
    """ Test that compressed tags set are supported. """
    avail_wheels.env = RuntimeEnvironment()

    wheel = avail_wheels.Wheel.parse_wheel_filename("shiboken2-5.15.0-5.15.0-cp35.cp36.cp37.cp38-abi3-linux_x86_64.whl")
    python_tags = avail_wheels.env.compatible_tags["3.8"]
    assert avail_wheels.is_compatible(wheel, python_tags)

    wheel = avail_wheels.Wheel.parse_wheel_filename("pydicom-1.1.0-1-py2.py3-none-any.whl")
    python_tags = avail_wheels.env.compatible_tags["3.9"]
    assert avail_wheels.is_compatible(wheel, python_tags)


def test_is_compatible_false(python_dirs):
    """ Test that wheel is not compatible for a given python. """
    avail_wheels.env = RuntimeEnvironment()
    wheel = avail_wheels.Wheel.parse_wheel_filename("netCDF4-1.3.1-cp39-cp39-linux_x86_64.whl")
    python_tags = avail_wheels.env.compatible_tags["2.7"]
    assert not avail_wheels.is_compatible(wheel, python_tags)


def test_is_compatible_many(python_dirs):
    """ Test that wheel is compatible for many given python. """
    avail_wheels.env = RuntimeEnvironment()
    wheel = avail_wheels.Wheel.parse_wheel_filename("netCDF4-1.3.1-cp27-cp27mu-linux_x86_64.whl")
    python_tags = frozenset().union(*(avail_wheels.env.compatible_tags[p] for p in ["2.7", "3.8"]))
    assert avail_wheels.is_compatible(wheel, python_tags)


def test_match_file_sensitive_true():
    """ Test that match file name case sensitevely."""
    assert avail_wheels.match_file(
        "netCDF4-1.3.1-cp27-cp27mu-linux_x86_64.whl",
        avail_wheels.get_rexes(["netCDF4"]),
    )


def test_match_file_insensitive_true():
    """Test that match file name case insensitevely."""
    assert avail_wheels.match_file(
        "netCDF4-1.3.1-cp27-cp27mu-linux_x86_64.whl",
        avail_wheels.get_rexes(["netcdf4"]),
    )
    assert avail_wheels.match_file(
        "netcdf4-1.3.1-cp27-cp27mu-linux_x86_64.whl",
        avail_wheels.get_rexes(["netCDF4"]),
    )


def test_match_file_false():
    """Test that do not match file name case sensitevely and insensitevely."""
    assert not avail_wheels.match_file("None", avail_wheels.get_rexes(["netcdf4"]))

# TODO : add test match file false default


def test_get_rexes():
    """
    Test that rexes are compiled for given patterns.

    The fnmatch.translate implementation has changed in Python 3.9.
    The group created from a star is unique and this results in a false equality when you compare two identical patterns.
    https://github.com/python/cpython/blob/e8f2fe355b82a3eb3c64ee6e1c44f31c020cf97d/Lib/fnmatch.py#L159

    E         - [re.compile('(?s:Nump(?=(?P<g1>.*?\\-))(?P=g1).*\\.whl)\\Z', re.IGNORECASE)]
    E         ?                              ^              ^
    E         + [re.compile('(?s:Nump(?=(?P<g0>.*?\\-))(?P=g0).*\\.whl)\\Z', re.IGNORECASE)]

    Hence we can't test for Nump*-*.whl patterns
    """

    rexes = [
        re.compile(translate(f"{re.sub(r'[-_.]+', '[-_.]', name)}-*.whl"), re.IGNORECASE)
        for name in ["numpy", "Scikit-learn"]
    ]
    assert avail_wheels.get_rexes(["numpy", "Scikit-learn"]) == rexes


def test_add_not_available_wheels_empty():
    """Test that an empty dict of wheels only contains the given wheel names."""
    ret = avail_wheels.add_not_available_wheels(defaultdict(list), ["a", "b", "torch*"])

    assert ret == {
        "a": [avail_wheels.Wheel(filename="a", name="a")],
        "b": [avail_wheels.Wheel(filename="b", name="b")],
        "torch*": [avail_wheels.Wheel(filename="torch*", name="torch*")],
    }


def test_add_not_available_wheels():
    """Test that wheels patterns are not added if they previously matched."""
    wheels = defaultdict(
        list,
        {
            "torch_cpu": [avail_wheels.Wheel(filename="torch_cpu", name="torch_cpu")],
            "numpy": [avail_wheels.Wheel(filename="numpy", name="numpy")],
        },
    )
    ret = avail_wheels.add_not_available_wheels(wheels, ["a", "b", "torch*"])

    assert ret == {
        "a": [avail_wheels.Wheel(filename="a", name="a")],
        "b": [avail_wheels.Wheel(filename="b", name="b")],
        "torch_cpu": [avail_wheels.Wheel(filename="torch_cpu", name="torch_cpu")],
        "numpy": [avail_wheels.Wheel(filename="numpy", name="numpy")],
    }


def test_add_not_available_wheels_only():
    """Test that wheels patterns not available are only present."""
    wheels = defaultdict(
        list,
        {
            "numpy": [avail_wheels.Wheel(filename="numpy", name="numpy")],
        },
    )
    ret = avail_wheels.add_not_available_wheels(wheels, ["potato", "patata", "numpy"], True)

    assert ret == {
        "potato": [avail_wheels.Wheel(filename="potato", name="potato")],
        "patata": [avail_wheels.Wheel(filename="patata", name="patata")],
    }


def test_filter_search_paths_all_search_paths():
    """
    Test that without any filter values all search paths are returned.
    """
    sp = ["path/path"]

    assert avail_wheels.filter_search_paths(sp, None) == sp
    assert avail_wheels.filter_search_paths(sp, []) == sp


def test_filter_search_paths_arch():
    """
    Test that arch are correctly filtered
    """
    # TODO : add test for cvmfs

    search_paths = [f"path/{p}" for p in ("avx2", "generic")]

    assert avail_wheels.filter_search_paths(search_paths, ["avx2"]) == ["path/avx2"]
    assert avail_wheels.filter_search_paths(search_paths, ["avx2", "generic"]) == [
        "path/avx2",
        "path/generic",
    ]


def test_filter_search_paths_no_match():
    """Test that an empty list is returned when no paths match the filter."""

    search_paths = [f"path/{p}" for p in ("avx2", "generic")]
    assert avail_wheels.filter_search_paths(search_paths, ["avx512"]) == []


def test_search_paths_no_pip_config_file(monkeypatch, wheelhouse):
    """
    Test that no PIP_CONFIG_FILE environment variable exists.
    Search paths are all directories from the wheelhouse.
    """
    # TODO : Add test for cvmfs
    monkeypatch.delenv("PIP_CONFIG_FILE", raising=False)
    monkeypatch.setenv("WHEELHOUSE", str(wheelhouse))
    avail_wheels.env = RuntimeEnvironment()

    other = sorted(
        [
            f"{str(wheelhouse)}/{p}"
            for p in [
                "generic/generic",
                "gentoo/avx2",
                "gentoo/generic",
                "nix/avx2",
                "nix/generic",
            ]
        ]
    )
    res = sorted(avail_wheels.get_search_paths())

    assert res == other


def test_search_paths_pip_config_file_empty(monkeypatch, wheelhouse):
    """
    Test that PIP_CONFIG_FILE environment variable exists but empty, entire wheelhouse is actually searched.
    """
    # TODO : Add test for cvmfs
    monkeypatch.setenv("PIP_CONFIG_FILE", "")
    monkeypatch.setenv("WHEELHOUSE", str(wheelhouse))
    avail_wheels.env = RuntimeEnvironment()

    other = sorted(
        [
            f"{str(wheelhouse)}/{p}"
            for p in [
                "generic/generic",
                "gentoo/avx2",
                "gentoo/generic",
                "nix/avx2",
                "nix/generic",
            ]
        ]
    )
    res = sorted(avail_wheels.get_search_paths())

    assert res == other


def test_search_paths_pip_config_file_exists(monkeypatch, pip_config_file):
    """
    Test that PIP_CONFIG_FILE environment variable exists and use the configuration file.
    """
    monkeypatch.setenv("PIP_CONFIG_FILE", str(pip_config_file))
    avail_wheels.env = RuntimeEnvironment()

    other = [
        f"{pip_config_file.parent}/wheelhouse/gentoo/avx2",
        f"{pip_config_file.parent}/wheelhouse/gentoo/generic",
        f"{pip_config_file.parent}/wheelhouse/generic",
    ]
    res = avail_wheels.get_search_paths()

    assert res == other


def test_make_requirement_name():
    """ Test that named requirement is valid and normalized. """
    assert avail_wheels.make_requirement("name") == Requirement("name")
    assert avail_wheels.make_requirement("name.name-cpu") == Requirement("name.name_cpu")


def test_make_requirement_wildname_suffix():
    """
    Test that named requirement with an ending wildcard (*) is valid.
    Test that named requirement with an starting wildcard (*) is valid.
    Test that named requirement with an ending and starting wildcard (*) is valid.
    """
    assert avail_wheels.make_requirement("name*") == Requirement("name*")
    assert avail_wheels.make_requirement("*name") == Requirement("*name")
    assert avail_wheels.make_requirement("*name*") == Requirement("*name*")


def test_make_requirement_wildname_version():
    """ Test that requirement with wildcard in name and version is valid. """
    # Exact version
    assert avail_wheels.make_requirement("*name*==1.2") == Requirement("*name*==1.2")
    assert avail_wheels.make_requirement("name*==1.2.3") == Requirement("name*==1.2.3")
    assert avail_wheels.make_requirement("name*-*==1.2.3") == Requirement("name*-*==1.2.3")

    # Wildcard versions (with dot)
    assert avail_wheels.make_requirement("*name*==1.2.*") == Requirement("*name*==1.2.*")
    assert avail_wheels.make_requirement("*name*==1.*") == Requirement("*name*==1.*")
    assert avail_wheels.make_requirement("name*-*==1.2.3.*") == Requirement("name*-*==1.2.3.*")


def test_make_requirement_wildname_version_ranges():
    """ Test that requirement with wildcard in name and version ranges is valid. """
    # Single inequality and compatibility ranges
    assert avail_wheels.make_requirement("*name*>=1.2") == Requirement("*name*>=1.2")
    assert avail_wheels.make_requirement("*name*>1.2") == Requirement("*name*>1.2")
    assert avail_wheels.make_requirement("*name*<=2.0") == Requirement("*name*<=2.0")
    assert avail_wheels.make_requirement("*name*<2.0") == Requirement("*name*<2.0")
    assert avail_wheels.make_requirement("*name*~=1.2.0") == Requirement("*name*~=1.2.0")
    assert avail_wheels.make_requirement("*name*!=1.2.3") == Requirement("*name*!=1.2.3")

    # Exclusion with wildcards
    assert avail_wheels.make_requirement("*name*!=1.2.*") == Requirement("*name*!=1.2.*")

    # Compound ranges (intervals)
    assert avail_wheels.make_requirement("*name*>=1.2,<2.0") == Requirement("*name*>=1.2,<2.0")
    assert avail_wheels.make_requirement("*name*>1.0,<=2.5.0") == Requirement("*name*>1.0,<=2.5.0")
    assert avail_wheels.make_requirement("*name*>=1.0,<2.0,!=1.5") == Requirement("*name*>=1.0,<2.0,!=1.5")
    assert avail_wheels.make_requirement("*name*>=1.0,!=1.2.*") == Requirement("*name*>=1.0,!=1.2.*")

    # Parenthesized range with spaces
    assert avail_wheels.make_requirement("*name*(>=1.2, <2.0)") == Requirement("*name*(>=1.2, <2.0)")


def test_make_requirement_invalid():
    """ Test that an exception is raise when an invalid requirement is given """
    with pytest.raises(Exception):
        avail_wheels.make_requirement("pennylane-*-")
        avail_wheels.make_requirement("climlab--radiation")
        avail_wheels.make_requirement("--")
        avail_wheels.make_requirement("*")


def test_make_requirement_localversion():
    """ Test that named requirement is valid and its local version is stripped. """
    assert avail_wheels.make_requirement("name") == Requirement("name")
    assert avail_wheels.make_requirement("name+local") == Requirement("name")
    assert avail_wheels.make_requirement("name+a.b.c") == Requirement("name")


def test_make_requirement_named_vcs():
    """ Test that named VCS requirements (e.g. 'gwcs @ git+...') are accepted and name extracted. """
    req_git = "gwcs @ git+https://github.com/spacetelescope/gwcs.git@master"
    assert avail_wheels.make_requirement(req_git) == Requirement("gwcs")

    req_main = "stcal @ git+https://github.com/spacetelescope/stcal.git@main"
    assert avail_wheels.make_requirement(req_main) == Requirement("stcal")


def test_make_requirement_bare_url_skipped():
    """ Test that bare URLs without package name are warned and skipped (return None). """
    with pytest.warns(UserWarning, match="Skipping unsupported URL requirement format"):
        assert avail_wheels.make_requirement("git+https://github.com/spacetelescope/gwcs.git") is None

    with pytest.warns(UserWarning, match="Skipping unsupported URL requirement format"):
        assert avail_wheels.make_requirement("git+https://github.com/spacetelescope/gwcs.git@master") is None

    with pytest.warns(UserWarning, match="Skipping unsupported URL requirement format"):
        assert avail_wheels.make_requirement("https://github.com/spacetelescope/gwcs.git@master") is None


def test_make_eq_specifier():
    """ Test that SpecifierSet is valid. """
    # assert avail_wheels.make_eq_specifier("*") == packaging.specifiers.SpecifierSet("==*")
    assert avail_wheels.make_eq_specifier("1.2") == packaging.specifiers.SpecifierSet("==1.2")
    # assert avail_wheels.make_eq_specifier("1.2*") == packaging.specifiers.SpecifierSet("==1.2*")
    assert avail_wheels.make_eq_specifier("1.2.*") == packaging.specifiers.SpecifierSet("==1.2.*")


def test_get_requirements_set_requirements_file(tmp_path):
    """
    Test that requirements set comes from command line.
    Names should also be normalized : dgl-cpu -> dgl_cpu
    """
    p = tmp_path / "r1.txt"
    p.write_text("\n".join(["numpy", "dgl-cpu", "ab.py==1.9"]))
    p = tmp_path / "r2.txt"
    p.write_text("\n".join(["scipy", "dummy~=4.0.0+computecanada"]))

    args = avail_wheels.create_argparser().parse_args(["--requirement", f"{str(tmp_path)}/r1.txt", f"{str(tmp_path)}/r2.txt"])

    assert avail_wheels.get_requirements_set(args) == {
        "numpy": Requirement("numpy"),
        "dgl-cpu": Requirement("dgl_cpu"),
        "ab-py": Requirement("ab.py==1.9"),
        "scipy": Requirement("scipy"),
        "dummy": Requirement("dummy~=4.0.0"),
    }


def test_get_requirements_set_requirements_file_and_names(tmp_path):
    """
    Test that requirements set comes from command line.
    Names should also be normalized : dgl-cpu -> dgl_cpu.
    Duplicates should not exists.
    Names from the command line are prioritize over duplicates entry from requirements files.
    """
    p = tmp_path / "requirements.txt"
    p.write_text("\n".join(["numpy", "dgl-cpu", "ab.py==1.9"]))

    args = avail_wheels.create_argparser().parse_args(["torch", "dgl-cpu==1.0", "--requirement", f"{str(tmp_path)}/requirements.txt"])

    assert avail_wheels.get_requirements_set(args) == {
        "torch": Requirement("torch"),
        "dgl-cpu": Requirement("dgl_cpu==1.0"),
        "numpy": Requirement("numpy"),
        "ab-py": Requirement("ab.py==1.9"),
    }


def test_get_requirements_set_from_names():
    """
    Test that requirements set comes from command line.
    Names should also be normalized : dgl-cpu -> dgl_cpu.
    Duplicates should not exists.
    """
    args = avail_wheels.create_argparser().parse_args(["torch", "dgl-cpu", "ab.py==1.9", "dummy==4+localversion"])

    assert avail_wheels.get_requirements_set(args) == {
        "torch": Requirement("torch"),
        "dgl-cpu": Requirement("dgl_cpu"),
        "ab-py": Requirement("ab.py==1.9"),
        "dummy": Requirement("dummy==4")
    }


def test_get_requirements_set_pyproject_toml(tmp_path):
    """
    Test that requirements set can be parsed from a local pyproject.toml file.
    """
    p = tmp_path / "pyproject.toml"
    p.write_text("""
[project]
name = "myproject"
version = "0.1.0"
dependencies = [
    "numpy>=1.20",
    "scipy",
    "dgl-cpu==1.0",
]
""")
    args = avail_wheels.create_argparser().parse_args(["--requirement", str(p)])
    assert avail_wheels.get_requirements_set(args) == {
        "numpy": Requirement("numpy>=1.20"),
        "scipy": Requirement("scipy"),
        "dgl-cpu": Requirement("dgl_cpu==1.0"),
    }


def test_get_requirements_set_pyproject_toml_url(monkeypatch):
    """
    Test that requirements set can be parsed from a pyproject.toml URL.
    """
    toml_content = b"""
[project]
name = "remote-project"
dependencies = [
    "numpy",
    "torch>=2.0",
]
"""
    class MockResponse:
        content = toml_content
        text = toml_content.decode("utf-8")
        def raise_for_status(self):
            pass

    from pip._internal.network.session import PipSession
    monkeypatch.setattr(PipSession, "get", lambda self, url: MockResponse())

    url = "https://raw.githubusercontent.com/example/repo/main/pyproject.toml"
    args = avail_wheels.create_argparser().parse_args(["--requirement", url])

    assert avail_wheels.get_requirements_set(args) == {
        "numpy": Requirement("numpy"),
        "torch": Requirement("torch>=2.0"),
    }


def test_remove_duplicates_wheel_filenames_no_duplicates():
    """Test that a list of distinct wheel filenames is preserved as-is."""
    wheels = [
        "numpy-1.25.0-cp39-cp39-linux_x86_64.whl",
        "scipy-1.11.0-cp39-cp39-linux_x86_64.whl",
        "torch-2.1.0-cp310-cp310-linux_x86_64.whl",
    ]
    assert avail_wheels.remove_duplicates(wheels) == wheels


def test_remove_duplicates_wheel_filenames_consecutive():
    """Test removing adjacent duplicate wheel filenames (e.g. from multiple search paths)."""
    wheels = [
        "numpy-1.25.0-cp39-cp39-linux_x86_64.whl",
        "numpy-1.25.0-cp39-cp39-linux_x86_64.whl",
        "scipy-1.11.0-cp310-cp310-linux_x86_64.whl",
    ]
    expected = [
        "numpy-1.25.0-cp39-cp39-linux_x86_64.whl",
        "scipy-1.11.0-cp310-cp310-linux_x86_64.whl",
    ]
    assert avail_wheels.remove_duplicates(wheels) == expected


def test_remove_duplicates_wheel_filenames_non_consecutive_preserves_order():
    """Test that order of first appearance is preserved when duplicates are scattered."""
    wheels = [
        "mmcv-2.1.0+torch211.computecanada-cp312-cp312-linux_x86_64.whl",
        "mmcv-2.1.0+computecanada-cp310-cp310-linux_x86_64.whl",
        "mmcv-2.1.0+torch211.computecanada-cp311-cp311-linux_x86_64.whl",
        "mmcv-2.1.0+torch211.computecanada-cp312-cp312-linux_x86_64.whl",  # duplicate of index 0
        "mmcv-2.1.0+computecanada-cp310-cp310-linux_x86_64.whl",          # duplicate of index 1
    ]
    expected = [
        "mmcv-2.1.0+torch211.computecanada-cp312-cp312-linux_x86_64.whl",
        "mmcv-2.1.0+computecanada-cp310-cp310-linux_x86_64.whl",
        "mmcv-2.1.0+torch211.computecanada-cp311-cp311-linux_x86_64.whl",
    ]
    assert avail_wheels.remove_duplicates(wheels) == expected


def test_remove_duplicates_wheel_filenames_all_identical():
    """Test that a list where all filenames are identical reduces to a single entry."""
    wheels = [
        "causal_conv1d-1.1.3.post1+computecanada-cp310-cp310-linux_x86_64.whl",
        "causal_conv1d-1.1.3.post1+computecanada-cp310-cp310-linux_x86_64.whl",
        "causal_conv1d-1.1.3.post1+computecanada-cp310-cp310-linux_x86_64.whl",
    ]
    expected = [
        "causal_conv1d-1.1.3.post1+computecanada-cp310-cp310-linux_x86_64.whl"
    ]
    assert avail_wheels.remove_duplicates(wheels) == expected


def test_remove_duplicates_empty():
    """Test empty input returns empty list."""
    assert avail_wheels.remove_duplicates([]) == []


def test_remove_duplicates_wheel_table_rows_default_columns():
    """
    Test deduplicating display rows when multiple wheels differ only by
    local version (e.g. +torch211 vs +computecanada), which is not in the columns.
    """
    # Columns: [name, version, python, arch]
    rows = [
        ["mmcv", "2.1.0", "cp312", "generic"],
        ["mmcv", "2.1.0", "cp311", "generic"],  # From mmcv-2.1.0+torch211...
        ["mmcv", "2.1.0", "cp311", "generic"],  # From mmcv-2.1.0+computecanada... (DUPLICATE)
        ["mmcv", "2.1.0", "cp310", "generic"],
    ]
    expected = [
        ["mmcv", "2.1.0", "cp312", "generic"],
        ["mmcv", "2.1.0", "cp311", "generic"],
        ["mmcv", "2.1.0", "cp310", "generic"],
    ]
    assert avail_wheels.remove_duplicates(rows) == expected


def test_remove_duplicates_wheel_table_rows_with_localversion():
    """
    Test that when localversion is present in columns, rows with different
    local versions are NOT treated as duplicates and are both preserved.
    """
    # Columns: [name, version, localversion, python, arch]
    rows = [
        ["mmcv", "2.1.0", "torch211.computecanada", "cp312", "generic"],
        ["mmcv", "2.1.0", "torch211.computecanada", "cp311", "generic"],
        ["mmcv", "2.1.0", "computecanada",          "cp311", "generic"],  # Distinct localversion
        ["mmcv", "2.1.0", "computecanada",          "cp310", "generic"],
    ]
    # All 4 rows are unique
    assert avail_wheels.remove_duplicates(rows) == rows
