from importlib import reload
from io import StringIO
from argparse import ArgumentError
from contextlib import redirect_stderr
from fnmatch import translate
import re
import avail_wheels
from runtime_env import RuntimeEnvironment
from collections import defaultdict
import packaging
from wild_requirements import Requirement
import pytest

TEST_STACKS = ["generic", "nix", "gentoo"]
TEST_ARCHS = ["avx2", "generic"]


@pytest.fixture
def wheelhouse(tmp_path):
    _wheelhouse = {
        "generic/generic": [
            "pydicom-1.1.0-1-py2.py3-none-any.whl",
            "pydicom-0.9.9-py3-none-any.whl",
            "shiboken2-5.15.0-5.15.0-cp35.cp36.cp37.cp38-abi3-linux_x86_64.whl",
            "shiboken2-5.15.0-5.15.0-cp27-cp27mu-linux_x86_64.whl",
            "extension_helpers-0.0.0-py3-none-any.whl",
            "path.py-12.5.0-py3-none-any.whl"
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


def test_wheel_ctor_kwargs():
    tags = packaging.tags.parse_tag("cp36-cp36m-linux_x86_64")
    wheel = avail_wheels.Wheel(filename="file", arch='avx',
                               name='torch_cpu', version='1.2.0+computecanada', build="",
                               tags=tags)
    assert wheel.filename == "file"
    assert wheel.arch == "avx"
    assert wheel.name == "torch_cpu"
    assert wheel.version == "1.2.0+computecanada"
    assert wheel.build == ""
    assert wheel.tags == tags
    assert wheel.python == "cp36"
    assert wheel.abi == "cp36m"
    assert wheel.platform == "linux_x86_64"


def test_wheel_parse_tags():
    filenames = [
        ("avx2", "netCDF4-1.3.1-cp36-cp36m-linux_x86_64.whl"),
        ("avx", "tensorflow_cpu-1.6.0+computecanada-cp36-cp36m-linux_x86_64.whl"),
        ("generic", "backports.functools_lru_cache-1.4-py2.py3-none-any.whl"),
        ("sse3", "Shapely-1.6.2.post1-cp35-cp35m-linux_x86_64.whl"),
        ("generic", "shiboken2-5.15.0-5.15.0-cp35.cp36.cp37.cp38-abi3-linux_x86_64.whl"),
    ]
    tags = {
        filenames[0][1]: {'arch': 'avx2', 'name': 'netCDF4', 'version': '1.3.1', 'build': '', 'python': 'cp36', 'abi': 'cp36m', 'platform': 'linux_x86_64'},
        filenames[1][1]: {'arch': 'avx', 'name': 'tensorflow_cpu', 'version': '1.6.0+computecanada', 'build': "", 'python': 'cp36', 'abi': 'cp36m', 'platform': 'linux_x86_64'},
        filenames[2][1]: {'arch': 'generic', 'name': 'backports.functools_lru_cache', 'version': '1.4', 'build': '', 'python': 'py2,py3', 'abi': 'none', 'platform': "any"},
        filenames[3][1]: {'arch': 'sse3', 'name': 'Shapely', 'version': '1.6.2.post1', 'build': '', 'python': 'cp35', 'abi': 'cp35m', 'platform': "linux_x86_64"},
        filenames[4][1]: {'arch': 'generic', 'name': 'shiboken2', 'version': '5.15.0', 'build': '5.15.0', 'python': 'cp35,cp36,cp37,cp38', 'abi': 'abi3', 'platform': "linux_x86_64"},
    }

    for arch, file in filenames:
        wheel = avail_wheels.Wheel.parse_wheel_filename(filename=file, arch=arch)
        assert wheel.filename == file
        assert wheel.arch == tags[file]['arch']
        assert wheel.name == tags[file]['name']
        assert wheel.version == tags[file]['version']
        assert wheel.build == tags[file]['build']
        assert wheel.python == tags[file]['python']
        assert wheel.abi == tags[file]['abi']
        assert wheel.platform == tags[file]['platform']


def test_wheel_loose_version():
    """ Test that the string repr of version is a parsed version. """
    wheel = avail_wheels.Wheel(version='1.2+cc')
    loose_version = wheel.loose_version()

    assert isinstance(loose_version, packaging.version.Version)
    assert loose_version == packaging.version.Version('1.2+cc')


def test_latest_versions_method_all_pythons():
    # TODO : test with build and local version as well
    wheels = {
        'netCDF4': [
            avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="netCDF4-1.3.2-cp36-cp36m-linux_x86_64.whl"),
            avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="netCDF4-1.3.2-cp35-cp35m-linux_x86_64.whl"),
            avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="netCDF4-1.3.2-cp27-cp27mu-linux_x86_64.whl"),
            avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="netCDF4-1.3.1-cp36-cp36m-linux_x86_64.whl"),
            avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="netCDF4-1.3.1-cp36-cp36m-linux_x86_64.whl"),
            avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="netCDF4-1.3.1-cp36-cp36m-linux_x86_64.whl"),
            avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="netCDF4-1.2.0-cp36-cp36m-linux_x86_64.whl"),
            avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="netCDF4-1.3-cp36-cp36m-linux_x86_64.whl")],
        'torch_cpu': [
            avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="torch_cpu-0.4.0-cp36-cp36m-linux_x86_64.whl")
        ]
    }

    wheels['netCDF4'].reverse()

    latest_wheels = {
        'netCDF4': [
            avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="netCDF4-1.3.2-cp27-cp27mu-linux_x86_64.whl"),
            avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="netCDF4-1.3.2-cp35-cp35m-linux_x86_64.whl"),
            avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="netCDF4-1.3.2-cp36-cp36m-linux_x86_64.whl")],
        'torch_cpu': [
            avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="torch_cpu-0.4.0-cp36-cp36m-linux_x86_64.whl")
        ]
    }

    assert avail_wheels.latest_versions(wheels) == latest_wheels


@pytest.fixture
def to_be_sorted_wheels():
    wheels = {
        'netCDF4': [
            avail_wheels.Wheel.parse_wheel_filename(arch="avx", filename="netCDF4-1.3.1-cp27-cp27mu-linux_x86_64.whl"),
            avail_wheels.Wheel.parse_wheel_filename(arch="avx", filename="netCDF4-1.3.1-cp35-cp35m-linux_x86_64.whl"),
            avail_wheels.Wheel.parse_wheel_filename(arch="avx", filename="netCDF4-1.3.1-cp36-cp36m-linux_x86_64.whl"),
            avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="netCDF4-1.3.1-cp27-cp27mu-linux_x86_64.whl"),
            avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="netCDF4-1.3.1-cp35-cp35m-linux_x86_64.whl"),
            avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="netCDF4-1.3.1-cp36-cp36m-linux_x86_64.whl"),
            avail_wheels.Wheel.parse_wheel_filename(arch="sse3", filename="netCDF4-1.3.1-cp27-cp27mu-linux_x86_64.whl"),
            avail_wheels.Wheel.parse_wheel_filename(arch="sse3", filename="netCDF4-1.3.1-cp35-cp35m-linux_x86_64.whl"),
            avail_wheels.Wheel.parse_wheel_filename(arch="sse3", filename="netCDF4-1.3.1-cp36-cp36m-linux_x86_64.whl"),
            avail_wheels.Wheel.parse_wheel_filename(arch="generic", filename="netCDF4-1.4.0-cp27-cp27mu-linux_x86_64.whl"),
            avail_wheels.Wheel.parse_wheel_filename(arch="generic", filename="netCDF4-1.2.8-cp27-cp27mu-linux_x86_64.whl")
        ],
        "botocore": [
            avail_wheels.Wheel.parse_wheel_filename(arch="generic", filename="botocore-1.10.63-py2.py3-none-any.whl"),
            avail_wheels.Wheel.parse_wheel_filename(arch="generic", filename="botocore-1.9.5-py2.py3-none-any.whl"),
            avail_wheels.Wheel.parse_wheel_filename(arch="generic", filename="botocore-1.10.57-py2.py3-none-any.whl"),
            avail_wheels.Wheel.parse_wheel_filename(arch="generic", filename="botocore-1.9.11-py2.py3-none-any.whl")
        ],
        "pydicom": [
            avail_wheels.Wheel.parse_wheel_filename(arch="generic", filename="pydicom-1.1.0-1-py2.py3-none-any.whl"),
            avail_wheels.Wheel.parse_wheel_filename(arch="generic", filename="pydicom-0.9.9-py3-none-any.whl")
        ],
        "torch_cpu": [
            avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="torch_cpu-0.4.0-cp36-cp36m-linux_x86_64.whl"),
            avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="torch_cpu-0.2.0+d8f3c60-cp27-cp27mu-linux_x86_64.whl")
        ]
    }

    wheels['netCDF4'].reverse()
    return wheels


def test_sort_type():
    assert isinstance(avail_wheels.sort({}, None), list)


def test_sort_columns(to_be_sorted_wheels):
    # TODO: Break down the sort tests into columns tests
    # TODO: Add test with a build
    assert avail_wheels.sort(to_be_sorted_wheels, avail_wheels.HEADERS) == [
        ['botocore', '1.10.63', '', 'py2,py3', 'generic'],
        ['botocore', '1.10.57', '', 'py2,py3', 'generic'],
        ['botocore', '1.9.11', '', 'py2,py3', 'generic'],
        ['botocore', '1.9.5', '', 'py2,py3', 'generic'],
        ['netCDF4', '1.4.0', '', 'cp27', 'generic'],
        ['netCDF4', '1.3.1', '', 'cp36', 'sse3'],
        ['netCDF4', '1.3.1', '', 'cp35', 'sse3'],
        ['netCDF4', '1.3.1', '', 'cp27', 'sse3'],
        ['netCDF4', '1.3.1', '', 'cp36', 'avx2'],
        ['netCDF4', '1.3.1', '', 'cp35', 'avx2'],
        ['netCDF4', '1.3.1', '', 'cp27', 'avx2'],
        ['netCDF4', '1.3.1', '', 'cp36', 'avx'],
        ['netCDF4', '1.3.1', '', 'cp35', 'avx'],
        ['netCDF4', '1.3.1', '', 'cp27', 'avx'],
        ['netCDF4', '1.2.8', '', 'cp27', 'generic'],
        ["pydicom", "1.1.0", "1", "py2,py3", "generic"],
        ["pydicom", "0.9.9", "", "py3", "generic"],
        ["torch_cpu", "0.4.0", "", "cp36", "avx2"],
        ["torch_cpu", "0.2.0+d8f3c60", "", "cp27", "avx2"]
    ]


def test_sort_condense(to_be_sorted_wheels):
    assert avail_wheels.sort(to_be_sorted_wheels, avail_wheels.HEADERS, True) == [
        ["botocore", "1.10.63, 1.10.57, 1.9.11, 1.9.5", '', "py2,py3", "generic"],
        ["netCDF4", "1.4.0, 1.3.1, 1.2.8", '', "cp36, cp35, cp27", "sse3, generic, avx2, avx"],
        ["pydicom", "1.1.0, 0.9.9", "1, ", "py3, py2,py3", "generic"],
        ["torch_cpu", "0.4.0, 0.2.0+d8f3c60", "", "cp36, cp27", "avx2"]
    ]


# TODO: Add test for PIP_CONFIG_FILE=""
def test_get_wheels_all_archs_all_pythons(wheelhouse):

    search_paths = [f"{str(wheelhouse)}/gentoo/{arch}" for arch in TEST_ARCHS]
    other = {
        'scipy': [
            avail_wheels.Wheel.parse_wheel_filename("scipy-1.7.0-cp37-cp37m-linux_x86_64.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("scipy-1.7.0-cp36-cp36m-linux_x86_64.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("scipy-1.7.0-cp35-cp35m-linux_x86_64.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("scipy-1.1.0-cp37-cp37m-linux_x86_64.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("scipy-1.1.0-cp36-cp36m-linux_x86_64.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("scipy-1.1.0-cp35-cp35m-linux_x86_64.whl", "generic"),
            avail_wheels.Wheel.parse_wheel_filename("scipy-1.1.0-cp27-cp27mu-linux_x86_64.whl", "generic"),
        ],
        'tensorflow_gpu': [
            avail_wheels.Wheel.parse_wheel_filename("tensorflow_gpu-1.8.0+computecanada-cp36-cp36m-linux_x86_64.whl", "avx2"),
            avail_wheels.Wheel.parse_wheel_filename("tensorflow_gpu-1.8.0+computecanada-cp35-cp35m-linux_x86_64.whl", "avx2"),
            avail_wheels.Wheel.parse_wheel_filename("tensorflow_gpu-1.8.0+computecanada-cp27-cp27mu-linux_x86_64.whl", "avx2"),
        ]
    }

    ret = avail_wheels.get_wheels(
        paths=search_paths,
        pythons=avail_wheels.env.available_pythons,
        reqs=None,
        latest=False
    )
    assert ret == other


def test_get_wheels_arch_all_pythons(wheelhouse):
    arch = 'generic'
    search_paths = [f'{str(wheelhouse)}/gentoo/{arch}']
    other = {'scipy': [
        avail_wheels.Wheel.parse_wheel_filename("scipy-1.7.0-cp37-cp37m-linux_x86_64.whl", arch),
        avail_wheels.Wheel.parse_wheel_filename("scipy-1.7.0-cp36-cp36m-linux_x86_64.whl", arch),
        avail_wheels.Wheel.parse_wheel_filename("scipy-1.7.0-cp35-cp35m-linux_x86_64.whl", arch),
        avail_wheels.Wheel.parse_wheel_filename("scipy-1.1.0-cp37-cp37m-linux_x86_64.whl", arch),
        avail_wheels.Wheel.parse_wheel_filename("scipy-1.1.0-cp36-cp36m-linux_x86_64.whl", arch),
        avail_wheels.Wheel.parse_wheel_filename("scipy-1.1.0-cp35-cp35m-linux_x86_64.whl", arch),
        avail_wheels.Wheel.parse_wheel_filename("scipy-1.1.0-cp27-cp27mu-linux_x86_64.whl", arch),
    ]}

    ret = avail_wheels.get_wheels(
        paths=search_paths,
        pythons=avail_wheels.env.available_pythons,
        reqs=None,
        latest=False,
    )
    assert ret == other


def test_get_wheels_exactname_arch_python(wheelhouse):
    arch = 'generic'
    search_paths = [f"{str(wheelhouse)}/gentoo/{arch}"]
    pythons = ['3.6']
    exactname = "scipy"
    other = {'scipy': [
        avail_wheels.Wheel.parse_wheel_filename("scipy-1.7.0-cp36-cp36m-linux_x86_64.whl", arch),
        avail_wheels.Wheel.parse_wheel_filename("scipy-1.1.0-cp36-cp36m-linux_x86_64.whl", arch),
    ]}

    ret = avail_wheels.get_wheels(
        paths=search_paths,
        pythons=pythons,
        reqs=defaultdict(Requirement, {exactname: Requirement(exactname)}),
        latest=False
    )
    assert ret == other


def test_get_wheels_wildname_arch_python(wheelhouse):
    arch = 'generic'
    search_paths = [f"{str(wheelhouse)}/gentoo/{arch}"]
    pythons = ['3.6']
    wildname = "*scipy*"
    other = {'scipy': [
        avail_wheels.Wheel.parse_wheel_filename("scipy-1.7.0-cp36-cp36m-linux_x86_64.whl", arch),
        avail_wheels.Wheel.parse_wheel_filename("scipy-1.1.0-cp36-cp36m-linux_x86_64.whl", arch),
    ]}

    ret = avail_wheels.get_wheels(
        paths=search_paths,
        pythons=pythons,
        reqs=defaultdict(Requirement, {wildname: Requirement(wildname)}),
        latest=False
    )
    assert ret == other


def test_get_wheels_wildname_arch_python_version(wheelhouse):
    arch = 'generic'
    search_paths = [f"{str(wheelhouse)}/gentoo/{arch}"]
    pythons = ['3.6']
    wildname = "*scipy*"
    version = '1.7.0'
    other = {'scipy': [avail_wheels.Wheel.parse_wheel_filename("scipy-1.7.0-cp36-cp36m-linux_x86_64.whl", arch)]}

    ret = avail_wheels.get_wheels(
        paths=search_paths,
        pythons=pythons,
        reqs=defaultdict(Requirement, {wildname: Requirement(f"{wildname}=={version}")}),
        latest=False
    )
    assert ret == other


def test_get_wheels_wildversion_wildname_arch_python(wheelhouse):
    search_paths = [f"{str(wheelhouse)}/gentoo/generic"]
    pythons = ['3.6']
    wildname = "*scipy*"
    version = '1.1.*'
    other = {'scipy': [avail_wheels.Wheel.parse_wheel_filename("scipy-1.1.0-cp36-cp36m-linux_x86_64.whl", "generic")]}

    ret = avail_wheels.get_wheels(
        paths=search_paths,
        pythons=pythons,
        reqs=defaultdict(Requirement, {wildname: Requirement(f"{wildname}=={version}")}),
        latest=False
    )
    assert ret == other


def test_get_wheels_wrongversion_wildname_arch_python(wheelhouse):
    search_paths = [f"{str(wheelhouse)}/gentoo/avx2"]
    pythons = ['3.6']
    wildname = "*scipy*"
    version = '2.3'
    other = {}

    ret = avail_wheels.get_wheels(
        paths=search_paths,
        pythons=pythons,
        reqs=defaultdict(Requirement, {wildname: Requirement(f"{wildname}=={version}")}),
        latest=False
    )
    assert ret == other


def test_parse_args_default_arch():
    # TODO: monkeypatch
    assert avail_wheels.create_argparser().get_default('arch') is None


def test_parse_args_default_noarch(monkeypatch):
    """ Special case (eg on personnal system). """
    monkeypatch.delenv('RSNT_ARCH', raising=False)
    assert avail_wheels.create_argparser().get_default('arch') is None


def test_parse_args_default_python(monkeypatch):
    # TODO: add test for virtual env.
    monkeypatch.delenv('VIRTUAL_ENV', raising=False)
    monkeypatch.setenv('EBVERSIONPYTHON', '3.6.10')

    avail_wheels.env = RuntimeEnvironment()
    assert avail_wheels.create_argparser().get_default('python') == ['3.6']


def test_parse_args_default_nopython(monkeypatch):
    """ Special case when no modules are loaded or on personnal system. """
    monkeypatch.delenv('VIRTUAL_ENV', raising=False)
    monkeypatch.delenv('EBVERSIONPYTHON', raising=False)

    env = RuntimeEnvironment()
    avail_wheels.env = env
    assert avail_wheels.create_argparser().get_default('python') == env.available_pythons


def test_parse_args_default_name():
    assert avail_wheels.create_argparser().get_default('name') == []


def test_parse_args_default_wheel():
    assert avail_wheels.create_argparser().get_default('wheel') is None


def test_parse_args_default_version():
    assert avail_wheels.create_argparser().get_default('version') is None


def test_parse_args_default_columns():
    assert avail_wheels.create_argparser().get_default('column') == avail_wheels.HEADERS


def test_parse_args_default_all_versions():
    assert not avail_wheels.create_argparser().get_default('all_versions')


def test_parse_args_default_all_pythons():
    assert not avail_wheels.create_argparser().get_default('all_pythons')


def test_parse_args_default_all_archs():
    assert not avail_wheels.create_argparser().get_default('all_archs')


def test_parse_args_default_raw():
    assert not avail_wheels.create_argparser().get_default('raw')


def test_parse_args_default_mediawiki():
    assert not avail_wheels.create_argparser().get_default('mediawiki')


def test_parse_args_version():
    version = '1.2*'
    args = avail_wheels.create_argparser().parse_args(['--version', version])
    assert isinstance(args.specifier, packaging.specifiers.SpecifierSet)
    assert args.specifier == packaging.specifiers.SpecifierSet(f"=={version}")


def test_parse_args_version_noarg():
    temp_stdout = StringIO()
    with redirect_stderr(temp_stdout):
        with pytest.raises(SystemExit):
            with pytest.raises(ArgumentError):
                avail_wheels.create_argparser().parse_args(['--version'])


def test_parse_args_all_versions():
    args = avail_wheels.create_argparser().parse_args(['--all_version'])
    assert isinstance(args.all_versions, bool)
    assert args.all_versions


def test_parse_args_arch():
    args = avail_wheels.create_argparser().parse_args(['--arch', 'avx2'])
    assert isinstance(args.arch, list)
    assert args.arch == ['avx2']


def test_parse_args_all_archs():
    args = avail_wheels.create_argparser().parse_args(['--all_archs'])
    assert isinstance(args.all_archs, bool)
    assert args.all_archs


def test_parse_args_many_arch():
    arch = ['avx2', 'avx']
    args = avail_wheels.create_argparser().parse_args(['--arch', *arch])
    assert isinstance(args.arch, list)
    assert args.arch == arch


def test_parse_args_arch_noarg():
    temp_stdout = StringIO()
    with redirect_stderr(temp_stdout):
        with pytest.raises(SystemExit):
            with pytest.raises(ArgumentError):
                avail_wheels.create_argparser().parse_args(['--arch'])


def test_parse_args_python():
    args = avail_wheels.create_argparser().parse_args(['--python', '3.7'])
    assert isinstance(args.python, list)
    assert args.python == ['3.7']


def test_parse_args_many_python():
    python = ['3.6', '3.7']
    args = avail_wheels.create_argparser().parse_args(['--python', *python])
    assert isinstance(args.python, list)
    assert args.python == python


def test_parse_args_python_noarg():
    temp_stdout = StringIO()
    with redirect_stderr(temp_stdout):
        with pytest.raises(SystemExit):
            with pytest.raises(ArgumentError):
                avail_wheels.create_argparser().parse_args(['--python'])


def test_parse_args_all_pythons():
    args = avail_wheels.create_argparser().parse_args(['--all_pythons'])
    assert isinstance(args.all_pythons, bool)
    assert args.all_pythons


def test_parse_args_name():
    args = avail_wheels.create_argparser().parse_args(['--name', "thename"])
    assert isinstance(args.name, list)
    assert args.name[0].name == "thename"


def test_parse_args_names():
    names = ["thename", "thename2"]
    args = avail_wheels.create_argparser().parse_args(['--name', *names])
    assert isinstance(args.name, list)
    assert [w.name for w in args.name] == names


def test_parse_args_name_noarg():
    temp_stdout = StringIO()
    with redirect_stderr(temp_stdout):
        with pytest.raises(SystemExit):
            with pytest.raises(ArgumentError):
                avail_wheels.create_argparser().parse_args(['--name'])


def test_parse_args_wheel():
    args = avail_wheels.create_argparser().parse_args(["thename"])
    assert isinstance(args.wheel, list)
    assert args.wheel[0].name == "thename"  # No eq op exists for a requirement


def test_parse_args_wheels():
    wheels = ["thename", "thename2"]
    args = avail_wheels.create_argparser().parse_args([*wheels])
    assert isinstance(args.wheel, list)
    assert [w.name for w in args.wheel] == wheels


def test_parse_args_wheel_noarg():
    args = avail_wheels.create_argparser().parse_args([])
    assert isinstance(args.wheel, list)
    assert args.wheel == []


def test_parse_args_requirement_noarg():
    """
    Test no value for the option.
    """
    temp_stdout = StringIO()
    with redirect_stderr(temp_stdout):
        with pytest.raises(SystemExit):
            with pytest.raises(ArgumentError):
                avail_wheels.create_argparser().parse_args(['--requirement'])


def test_parse_args_requirement_file():
    """
    Test one requirement file.
    """
    args = avail_wheels.create_argparser().parse_args(["--requirement", "requirement.txt"])

    assert isinstance(args.requirements, list)
    assert args.requirements == ["requirement.txt"]


def test_parse_args_requirement_files():
    """
    Test multiple requirement files.
    """
    args = avail_wheels.create_argparser().parse_args(["--requirement", "requirement.txt", "reqs.txt"])

    assert isinstance(args.requirements, list)
    assert args.requirements == ["requirement.txt", "reqs.txt"]


@pytest.fixture
def compatible_wheel():
    # TODO : test compressed tag set
    return avail_wheels.Wheel.parse_wheel_filename(arch="avx", filename="netCDF4-1.3.1-cp27-cp27mu-linux_x86_64.whl")


def test_is_compatible_true(compatible_wheel):
    assert avail_wheels.is_compatible(compatible_wheel, ['2.7'])


def test_is_compatible_false(compatible_wheel):
    assert not avail_wheels.is_compatible(compatible_wheel, ['3.5'])


def test_is_compatible_many(compatible_wheel):
    # TODO: add cvmfs test
    # TODO: monkeypatch
    assert avail_wheels.is_compatible(compatible_wheel, avail_wheels.env.available_pythons)


def test_match_file_sensitive_true():
    """ Match file name case sensitevely. """
    assert avail_wheels.match_file("netCDF4-1.3.1-cp27-cp27mu-linux_x86_64.whl", avail_wheels.get_rexes(["netCDF4"]))


def test_match_file_insensitive_true():
    """ Match file name case insensitevely. """
    assert avail_wheels.match_file("netCDF4-1.3.1-cp27-cp27mu-linux_x86_64.whl", avail_wheels.get_rexes(["netcdf4"]))
    assert avail_wheels.match_file("netcdf4-1.3.1-cp27-cp27mu-linux_x86_64.whl", avail_wheels.get_rexes(["netCDF4"]))


def test_match_file_false():
    """ Do not match file name case sensitevely and insensitevely. """
    assert not avail_wheels.match_file("None", avail_wheels.get_rexes(["netcdf4"]))

# TODO : add test match file false default


def test_get_rexes():
    rexes = [re.compile(translate(pattern), re.IGNORECASE) for pattern in ["numpy-*.whl", "Nump*-*.whl"]]
    assert avail_wheels.get_rexes(["numpy", "Nump*"]) == rexes


def test_add_not_available_wheels_empty():
    """ Test that an empty dict of wheels only contains the given wheel names. """
    ret = avail_wheels.add_not_available_wheels(defaultdict(list), ['a', 'b', 'torch*'])

    assert ret == {'a': [avail_wheels.Wheel(filename='a', name='a')],
                   'b': [avail_wheels.Wheel(filename='b', name='b')],
                   'torch*': [avail_wheels.Wheel(filename="torch*", name="torch*")]}


def test_add_not_available_wheels():
    """ Test that wheels patterns are not added if they previously matched. """
    wheels = defaultdict(list, {'torch_cpu': [avail_wheels.Wheel(filename="torch_cpu", name="torch_cpu")],
                                'numpy': [avail_wheels.Wheel(filename="numpy", name="numpy")]})
    ret = avail_wheels.add_not_available_wheels(wheels, ['a', 'b', 'torch*'])

    assert ret == {'a': [avail_wheels.Wheel(filename='a', name='a')],
                   'b': [avail_wheels.Wheel(filename='b', name='b')],
                   'torch_cpu': [avail_wheels.Wheel(filename="torch_cpu", name="torch_cpu")],
                   'numpy': [avail_wheels.Wheel(filename="numpy", name="numpy")]}


def test_normalize_name_type():
    """ Test that return type is list. """
    assert isinstance(avail_wheels.normalize_name(""), str)


def test_normalize_name():
    """ Test that normalize empty list, names with multiple dash are converted to underscores. """
    names = ['', 'torch-cpu', 'torch_cpu', 'torch-cpu.gpu']
    truth = ['', 'torch_cpu', 'torch_cpu', 'torch_cpu.gpu']

    for name, true_name in zip(names, truth):
        ret = avail_wheels.normalize_name(name)
        assert ret == true_name


def test_filter_search_paths_all_search_paths():
    """
    Test that without any filter values all search paths are returned.
    """
    sp = ['path/path']

    assert avail_wheels.filter_search_paths(sp, None) == sp
    assert avail_wheels.filter_search_paths(sp, []) == sp


def test_filter_search_paths_arch():
    """
    Test that arch are correctly filtered
    """
    # TODO : add test for cvmfs

    search_paths = [f'path/{p}' for p in ('avx2', 'generic')]

    assert avail_wheels.filter_search_paths(search_paths, ['avx2']) == ['path/avx2']
    assert avail_wheels.filter_search_paths(search_paths, ['avx2', 'generic']) == ['path/avx2', 'path/generic']


def test_no_pip_config_file(monkeypatch, wheelhouse):
    """
    Test that no PIP_CONFIG_FILE environment variable exists.
    Search paths are all directories from the wheelhouse.
    """
    # TODO : Add test for cvmfs
    monkeypatch.delenv("PIP_CONFIG_FILE", raising=False)
    monkeypatch.setenv("WHEELHOUSE", str(wheelhouse))
    reload(avail_wheels)  # Must reload script for env to be known
    # TODO : get rid of reload, env = RuntimeEnvironment()
    other = sorted([f"{str(wheelhouse)}/{p}" for p in ["generic/generic", "gentoo/avx2", "gentoo/generic", "nix/avx2", "nix/generic"]])
    res = sorted(avail_wheels.get_search_paths())

    assert res == other


def test_pip_config_file_empty(monkeypatch, wheelhouse):
    """
    Test that PIP_CONFIG_FILE environment variable exists but empty, entire wheelhouse is actually searched.
    """
    # TODO : Add test for cvmfs
    monkeypatch.setenv("PIP_CONFIG_FILE", "")
    monkeypatch.setenv("WHEELHOUSE", str(wheelhouse))
    reload(avail_wheels)  # Must reload script for env to be known

    other = sorted([f"{str(wheelhouse)}/{p}" for p in ["generic/generic", "gentoo/avx2", "gentoo/generic", "nix/avx2", "nix/generic"]])
    res = sorted(avail_wheels.get_search_paths())

    assert res == other


def test_pip_config_file_exists(monkeypatch, pip_config_file):
    """
    Test that PIP_CONFIG_FILE environment variable exists and use the configuration file.
    """
    monkeypatch.setenv("PIP_CONFIG_FILE", str(pip_config_file))

    other = [f"{pip_config_file.parent}/wheelhouse/gentoo/avx2", f"{pip_config_file.parent}/wheelhouse/gentoo/generic", f"{pip_config_file.parent}/wheelhouse/generic"]
    res = avail_wheels.get_search_paths()

    assert res == other
