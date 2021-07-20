import unittest
from pathlib import Path
from importlib import reload
from io import StringIO
from argparse import ArgumentError
from contextlib import redirect_stderr
from fnmatch import translate
import os
import re
import avail_wheels
from pytest import MonkeyPatch
import shutil
from runtime_env import RuntimeEnvironment
from collections import defaultdict
import packaging
import wild_requirements as requirements


TEST_STACKS = ["generic", "nix", "gentoo"]
TEST_ARCHS = ["avx2", "generic"]


class MonkeyTest(unittest.TestCase):
    def setUp(self):
        self.monkeypatch = MonkeyPatch()
        self.env = RuntimeEnvironment()

    def tearDown(self):
        self.monkeypatch.undo()


class DummyWheelhouse(object):
    path = "/tmp/wheelhouse"
    wheelhouse = {
        "generic/generic": [
            "torch-1.0.1.post2-cp27-cp27m-linux_x86_64.whl",
            "torch-1.0.1.post2-cp35-cp35m-linux_x86_64.whl",
            "torch-1.0.1.post2-cp36-cp36m-linux_x86_64.whl",
            "torch-1.0.1.post2-cp37-cp37m-linux_x86_64.whl",
            "torch-1.1.0-cp36-cp36m-linux_x86_64.whl",
            "torch-1.1.0-cp37-cp37m-linux_x86_64.whl",
            "torch-1.1.0-cp38-cp38-linux_x86_64.whl",
            "pydicom-1.1.0-1-py2.py3-none-any.whl",
            "pydicom-0.9.9-py3-none-any.whl",
            "pydicom-0.8.9-py2-none-any.whl",
            # "shiboken2-5.15.0-5.15.0-cp35.cp36.cp37.cp38-abi3-linux_x86_64.whl",
            # "shiboken2-5.15.0-5.15.0-cp27-cp27mu-linux_x86_64.whl",
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
        ],
    }

    def create(self):
        for directory, filenames in self.wheelhouse.items():
            os.makedirs(f"{self.path}/{directory}", exist_ok=True)
            for file in filenames:
                Path(f"{self.path}/{directory}/{file}").touch()

    def remove(self):
        shutil.rmtree(self.path)


class DummyPipConfigFile(object):
    filename = "/tmp/avail_wheels_pip.cfg"
    content = "[wheel]\nfind-links = /tmp/wheelhouse/gentoo/avx2 /tmp/wheelhouse/gentoo/generic /tmp/wheelhouse/generic"

    def create(self):
        with open(self.filename, 'w') as f:
            f.write(self.content)

    def remove(self):
        os.remove(self.filename)


class Test_wheel_class(unittest.TestCase):
    def test_ctor_kwargs(self):
        tags = packaging.tags.parse_tag("cp36-cp36m-linux_x86_64")
        wheel = avail_wheels.Wheel(filename="file", arch='avx',
                                   name='torch_cpu', version='1.2.0+computecanada', build="",
                                   tags=tags)
        self.assertEqual(wheel.filename, "file")
        self.assertEqual(wheel.arch, "avx")
        self.assertEqual(wheel.name, "torch_cpu")
        self.assertEqual(wheel.version, "1.2.0+computecanada")
        self.assertEqual(wheel.build, "")
        self.assertEqual(wheel.tags, tags)
        self.assertEqual(wheel.python, "cp36")
        self.assertEqual(wheel.abi, "cp36m")
        self.assertEqual(wheel.platform, "linux_x86_64")

    def test_parse_tags(self):
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
            self.assertEqual(wheel.filename, file)
            self.assertEqual(wheel.arch, tags[file]['arch'])
            self.assertEqual(wheel.name, tags[file]['name'])
            self.assertEqual(wheel.version, tags[file]['version'])
            self.assertEqual(wheel.build, tags[file]['build'])
            self.assertEqual(wheel.python, tags[file]['python'])
            self.assertEqual(wheel.abi, tags[file]['abi'])
            self.assertEqual(wheel.platform, tags[file]['platform'])

    def test_loose_version(self):
        """ Test that the string repr of version is a parsed version. """
        wheel = avail_wheels.Wheel(version='1.2+cc')
        loose_version = wheel.loose_version()

        self.assertIsInstance(loose_version, packaging.version.Version)
        self.assertEqual(loose_version, packaging.version.Version('1.2+cc'))


class Test_latest_versions_method(unittest.TestCase):
    def setUp(self):
        self.wheels = {'netCDF4': [avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="netCDF4-1.3.2-cp36-cp36m-linux_x86_64.whl"),
                                   avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="netCDF4-1.3.2-cp35-cp35m-linux_x86_64.whl"),
                                   avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="netCDF4-1.3.2-cp27-cp27mu-linux_x86_64.whl"),
                                   avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="netCDF4-1.3.1-cp36-cp36m-linux_x86_64.whl"),
                                   avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="netCDF4-1.3.1-cp36-cp36m-linux_x86_64.whl"),
                                   avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="netCDF4-1.3.1-cp36-cp36m-linux_x86_64.whl"),
                                   avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="netCDF4-1.2.0-cp36-cp36m-linux_x86_64.whl"),
                                   avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="netCDF4-1.3-cp36-cp36m-linux_x86_64.whl")],
                       'torch_cpu': [avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="torch_cpu-0.4.0-cp36-cp36m-linux_x86_64.whl")]}

        self.wheels['netCDF4'].reverse()

        self.latest_wheels = {'netCDF4': [avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="netCDF4-1.3.2-cp27-cp27mu-linux_x86_64.whl"),
                                          avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="netCDF4-1.3.2-cp35-cp35m-linux_x86_64.whl"),
                                          avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="netCDF4-1.3.2-cp36-cp36m-linux_x86_64.whl")],
                              'torch_cpu': [avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="torch_cpu-0.4.0-cp36-cp36m-linux_x86_64.whl")]}

    def test_latest_versions_method_all_pythons(self):
        ret = avail_wheels.latest_versions(self.wheels)
        self.assertEqual(ret, self.latest_wheels)


class Test_sort_method(unittest.TestCase):
    def setUp(self):
        self.wheels = {'netCDF4': [avail_wheels.Wheel.parse_wheel_filename(arch="avx", filename="netCDF4-1.3.1-cp27-cp27mu-linux_x86_64.whl"),
                                   avail_wheels.Wheel.parse_wheel_filename(arch="avx", filename="netCDF4-1.3.1-cp35-cp35m-linux_x86_64.whl"),
                                   avail_wheels.Wheel.parse_wheel_filename(arch="avx", filename="netCDF4-1.3.1-cp36-cp36m-linux_x86_64.whl"),
                                   avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="netCDF4-1.3.1-cp27-cp27mu-linux_x86_64.whl"),
                                   avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="netCDF4-1.3.1-cp35-cp35m-linux_x86_64.whl"),
                                   avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="netCDF4-1.3.1-cp36-cp36m-linux_x86_64.whl"),
                                   avail_wheels.Wheel.parse_wheel_filename(arch="sse3", filename="netCDF4-1.3.1-cp27-cp27mu-linux_x86_64.whl"),
                                   avail_wheels.Wheel.parse_wheel_filename(arch="sse3", filename="netCDF4-1.3.1-cp35-cp35m-linux_x86_64.whl"),
                                   avail_wheels.Wheel.parse_wheel_filename(arch="sse3", filename="netCDF4-1.3.1-cp36-cp36m-linux_x86_64.whl"),
                                   avail_wheels.Wheel.parse_wheel_filename(arch="generic", filename="netCDF4-1.4.0-cp27-cp27mu-linux_x86_64.whl"),
                                   avail_wheels.Wheel.parse_wheel_filename(arch="generic", filename="netCDF4-1.2.8-cp27-cp27mu-linux_x86_64.whl")],

                       "botocore": [avail_wheels.Wheel.parse_wheel_filename(arch="generic", filename="botocore-1.10.63-py2.py3-none-any.whl"),
                                    avail_wheels.Wheel.parse_wheel_filename(arch="generic", filename="botocore-1.9.5-py2.py3-none-any.whl"),
                                    avail_wheels.Wheel.parse_wheel_filename(arch="generic", filename="botocore-1.10.57-py2.py3-none-any.whl"),
                                    avail_wheels.Wheel.parse_wheel_filename(arch="generic", filename="botocore-1.9.11-py2.py3-none-any.whl")],

                       "pydicom": [avail_wheels.Wheel.parse_wheel_filename(arch="generic", filename="pydicom-1.1.0-1-py2.py3-none-any.whl"),
                                   avail_wheels.Wheel.parse_wheel_filename(arch="generic", filename="pydicom-0.9.9-py3-none-any.whl")],


                       "torch_cpu": [avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="torch_cpu-0.4.0-cp36-cp36m-linux_x86_64.whl"),
                                     avail_wheels.Wheel.parse_wheel_filename(arch="avx2", filename="torch_cpu-0.2.0+d8f3c60-cp27-cp27mu-linux_x86_64.whl")]}

        self.wheels['netCDF4'].reverse()

        self.output = [['botocore', '1.10.63', '', 'py2,py3', 'generic'],
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
                       ["torch_cpu", "0.2.0+d8f3c60", "", "cp27", "avx2"]]

        self.condensed_output = [
            ["botocore", "1.10.63, 1.10.57, 1.9.11, 1.9.5", '', "py2,py3", "generic"],
            ["netCDF4", "1.4.0, 1.3.1, 1.2.8", '', "cp36, cp35, cp27", "sse3, generic, avx2, avx"],
            ["pydicom", "1.1.0, 0.9.9", "1, ", "py3, py2,py3", "generic"],
            ["torch_cpu", "0.4.0, 0.2.0+d8f3c60", "", "cp36, cp27", "avx2"]
        ]

    def test_sort_ret(self):
        ret = avail_wheels.sort({}, None)
        self.assertIsInstance(ret, list)

    def test_sort_columns(self):
        ret = avail_wheels.sort(self.wheels, avail_wheels.HEADERS)
        self.assertEqual(ret, self.output)

    def test_sort_condense(self):
        ret = avail_wheels.sort(self.wheels, avail_wheels.HEADERS, True)
        self.assertEqual(ret, self.condensed_output)


class Test_get_wheels_method(unittest.TestCase):
    def setUp(self):
        self.wheelhouse = "wheelhouse_test_dir"
        self.raw_filenames = {'netCDF4': ["netCDF4-1.3.1-cp27-cp27mu-linux_x86_64.whl",
                                          "netCDF4-1.3.1-cp35-cp35m-linux_x86_64.whl",
                                          "netCDF4-1.2.0-cp36-cp36m-linux_x86_64.whl",
                                          "netCDF4-1.3.1-cp36-cp36m-linux_x86_64.whl"],
                              'torch_cpu': ["torch_cpu-0.4.0+computecanada-cp36-cp36m-linux_x86_64.whl"]}
        self.current_stack = 'nix'

        # Create the wheelhouse and its subdirs, files.
        for stack in [self.current_stack]:
            for arch in avail_wheels.env.available_architectures:
                os.makedirs(f"{self.wheelhouse}/{stack}/{arch}", exist_ok=True)
                for files in self.raw_filenames.values():
                    for file in files:
                        Path(f"{self.wheelhouse}/{stack}/{arch}/{file}").touch()

    def tearDown(self):
        # Delete wheelhouse
        for stack in [self.current_stack]:
            for arch in avail_wheels.env.available_architectures:
                for files in self.raw_filenames.values():
                    for file in files:
                        os.remove(f"{self.wheelhouse}/{stack}/{arch}/{file}")
                os.rmdir(f"{self.wheelhouse}/{stack}/{arch}")
            os.rmdir(f"{self.wheelhouse}/{stack}")
        os.rmdir(self.wheelhouse)

    def test_get_wheels_all_archs_all_pythons(self):
        search_paths = [f"{self.wheelhouse}/{self.current_stack}/{arch}" for arch in avail_wheels.env.available_architectures]
        other = {'netCDF4': [], 'torch_cpu': []}
        for arch in avail_wheels.env.available_architectures:
            for wheel_name, files in self.raw_filenames.items():
                for file in files:
                    other[wheel_name].append(avail_wheels.Wheel.parse_wheel_filename(arch=arch, filename=file))

        ret = avail_wheels.get_wheels(paths=search_paths, pythons=avail_wheels.env.available_pythons, reqs=None, latest=False)
        self.assertEqual(ret, other)

    def test_get_wheels_arch_all_pythons(self):
        arch = 'avx2'
        search_paths = [f'{self.wheelhouse}/{self.current_stack}/{arch}']
        other = {'netCDF4': [], 'torch_cpu': []}
        for wheel_name, files in self.raw_filenames.items():
            for file in files:
                other[wheel_name].append(avail_wheels.Wheel.parse_wheel_filename(arch=arch, filename=file))

        ret = avail_wheels.get_wheels(paths=search_paths, pythons=avail_wheels.env.available_pythons, reqs=None, latest=False)
        self.assertEqual(ret, other)

    def test_get_wheels_arch_python(self):
        arch = 'avx2'
        search_paths = [f"{self.wheelhouse}/{self.current_stack}/{arch}"]
        pythons = ['3.6']
        other = {'netCDF4': [avail_wheels.Wheel.parse_wheel_filename(arch=arch, filename=self.raw_filenames['netCDF4'][2]),
                             avail_wheels.Wheel.parse_wheel_filename(arch=arch, filename=self.raw_filenames['netCDF4'][3])],
                 'torch_cpu': [avail_wheels.Wheel.parse_wheel_filename(arch=arch, filename=self.raw_filenames['torch_cpu'][0])]}

        ret = avail_wheels.get_wheels(paths=search_paths, pythons=pythons, reqs=None, latest=False)
        self.assertEqual(ret, other)

    @unittest.skip("Need to refactor")
    def test_get_wheels_exactname_arch_python(self):
        arch = 'avx2'
        search_paths = [f"{self.wheelhouse}/{self.current_stack}/{arch}"]
        pythons = ['3.6']
        exactname = "netCDF4"
        other = {'netCDF4': [avail_wheels.Wheel(f"{arch}/{self.raw_filenames['netCDF4'][2]}"),
                             avail_wheels.Wheel(f"{arch}/{self.raw_filenames['netCDF4'][3]}")]}

        ret = avail_wheels.get_wheels(paths=search_paths, pythons=pythons, reqs=defaultdict(requirements.Requirement, {exactname: requirements.Requirement(exactname)}), latest=False)
        self.assertEqual(ret, other)

    @unittest.skip("Need to refactor")
    def test_get_wheels_wildname_arch_python(self):
        arch = 'avx2'
        search_paths = [f"{self.wheelhouse}/{self.current_stack}/{arch}"]
        pythons = ['3.6']
        wildname = "*CDF*"
        other = {'netCDF4': [avail_wheels.Wheel(f"{arch}/{self.raw_filenames['netCDF4'][2]}"),
                             avail_wheels.Wheel(f"{arch}/{self.raw_filenames['netCDF4'][3]}")]}

        ret = avail_wheels.get_wheels(paths=search_paths, pythons=pythons, reqs=defaultdict(requirements.Requirement, {wildname: requirements.Requirement(wildname)}), latest=False)
        self.assertEqual(ret, other)

    @unittest.skip("Need to refactor")
    def test_get_wheels_wildname_arch_python_version(self):
        arch = 'avx2'
        search_paths = [f"{self.wheelhouse}/{self.current_stack}/{arch}"]
        pythons = ['3.6']
        wildname = "*CDF*"
        # version = '1.3.1'
        other = {'netCDF4': [avail_wheels.Wheel(f"{arch}/{self.raw_filenames['netCDF4'][3]}")]}

        ret = avail_wheels.get_wheels(paths=search_paths, pythons=pythons, reqs=defaultdict(requirements.Requirement, {wildname: requirements.Requirement(wildname)}), latest=False)
        self.assertEqual(ret, other)

    @unittest.skip("Need to refactor")
    def test_get_wheels_wildversion_wildname_arch_python(self):
        arch = 'avx2'
        search_paths = [f"{self.wheelhouse}/{self.current_stack}/{arch}"]
        pythons = ['3.6']
        wildname = "*CDF*"
        # version = '1.2.*'
        other = {'netCDF4': [avail_wheels.Wheel(f"{arch}/{self.raw_filenames['netCDF4'][2]}")]}

        ret = avail_wheels.get_wheels(paths=search_paths, pythons=pythons, reqs=defaultdict(requirements.Requirement, {wildname: requirements.Requirement(wildname)}), latest=False)
        self.assertEqual(ret, other)

    def test_get_wheels_wrongversion_wildname_arch_python(self):
        arch = 'avx2'
        search_paths = [f"{self.wheelhouse}/{self.current_stack}/{arch}"]
        pythons = ['3.6']
        wildname = "*CDF*"
        version = '2.3'
        other = {}

        ret = avail_wheels.get_wheels(paths=search_paths, pythons=pythons, reqs=defaultdict(requirements.Requirement, {wildname: requirements.Requirement(f"{wildname}=={version}")}), latest=False)
        self.assertEqual(ret, other)


class Test_parse_args_method(unittest.TestCase):
    def setUp(self):
        self.redoSetUp(arch='sse3', python='3.6.3')

    def redoSetUp(self, arch=None, python=None):
        self.current_architecture = arch
        self.current_python = python

        if python:
            os.environ['EBVERSIONPYTHON'] = python
        elif 'EBVERSIONPYTHON' in os.environ:
            del os.environ['EBVERSIONPYTHON']

        reload(avail_wheels)  # Must reload script for env to be known
        self.parser = avail_wheels.create_argparser()

    def test_default_arch(self):
        self.parser.parse_args([])
        self.assertEqual(self.parser.get_default('arch'), None)

    def test_default_noarch(self):
        """ Special case (eg on personnal system). """
        self.redoSetUp()  # Need to overwrite setUp
        self.parser.parse_args([])

        self.assertEqual(self.parser.get_default('arch'), None)

    @unittest.skip(reason="Need to refactor")
    def test_default_python(self):
        default_python = ['3.6']
        self.parser.parse_args([])

        self.assertEqual(avail_wheels.env.current_python, self.current_python)
        self.assertEqual(self.parser.get_default('python'), default_python)

    @unittest.skip(reason="Need to refactor")
    def test_default_nopython(self):
        """ Special case when no modules are loaded or on personnal system. """
        self.redoSetUp()  # Need to overwrite setUp
        self.parser.parse_args([])

        self.assertEqual(avail_wheels.env.current_python, self.current_python)
        self.assertEqual(self.parser.get_default('python'), avail_wheels.env.available_pythons)

    def test_default_name(self):
        self.parser.parse_args([])
        self.assertEqual(self.parser.get_default('name'), [])

    def test_default_wheel(self):
        self.parser.parse_args([])
        self.assertEqual(self.parser.get_default('wheel'), None)

    def test_default_version(self):
        self.parser.parse_args([])
        self.assertEqual(self.parser.get_default('version'), None)

    def test_default_columns(self):
        self.parser.parse_args([])
        self.assertEqual(self.parser.get_default('column'), avail_wheels.HEADERS)

    def test_default_all_versions(self):
        self.parser.parse_args([])
        self.assertFalse(self.parser.get_default('all_versions'))

    def test_default_all_pythons(self):
        self.parser.parse_args([])
        self.assertFalse(self.parser.get_default('all_pythons'))

    def test_default_all_archs(self):
        self.parser.parse_args([])
        self.assertFalse(self.parser.get_default('all_archs'))

    def test_default_raw(self):
        self.parser.parse_args([])
        self.assertFalse(self.parser.get_default('raw'))

    def test_default_mediawiki(self):
        self.parser.parse_args([])
        self.assertFalse(self.parser.get_default('mediawiki'))

    def test_version(self):
        version = '1.2*'
        args = self.parser.parse_args(['--version', version])
        self.assertIsInstance(args.specifier, packaging.specifiers.SpecifierSet)
        self.assertEqual(args.specifier, packaging.specifiers.SpecifierSet(f"=={version}"))

    def test_version_noarg(self):
        temp_stdout = StringIO()
        with redirect_stderr(temp_stdout):
            with self.assertRaises(SystemExit):
                with self.assertRaises(ArgumentError):
                    self.parser.parse_args(['--version'])

    def test_all_versions(self):
        args = self.parser.parse_args(['--all_version'])
        self.assertIsInstance(args.all_versions, bool)
        self.assertTrue(args.all_versions)

    def test_arch(self):
        arch = ['avx2']
        args = self.parser.parse_args(['--arch', arch[0]])
        self.assertIsInstance(args.arch, list)
        self.assertEqual(args.arch, arch)

    def test_all_archs(self):
        args = self.parser.parse_args(['--all_archs'])
        self.assertIsInstance(args.all_archs, bool)
        self.assertTrue(args.all_archs)

    def test_many_arch(self):
        arch = ['avx2', 'avx']
        args = self.parser.parse_args(['--arch', *arch])
        self.assertIsInstance(args.arch, list)
        self.assertEqual(args.arch, arch)

    def test_arch_noarg(self):
        temp_stdout = StringIO()
        with redirect_stderr(temp_stdout):
            with self.assertRaises(SystemExit):
                with self.assertRaises(ArgumentError):
                    self.parser.parse_args(['--arch'])

    def test_python(self):
        python = ['3.7']
        args = self.parser.parse_args(['--python', python[0]])
        self.assertIsInstance(args.python, list)
        self.assertEqual(args.python, python)

    def test_many_python(self):
        python = ['3.6', '3.7']
        args = self.parser.parse_args(['--python', *python])
        self.assertIsInstance(args.python, list)
        self.assertEqual(args.python, python)

    def test_python_noarg(self):
        temp_stdout = StringIO()
        with redirect_stderr(temp_stdout):
            with self.assertRaises(SystemExit):
                with self.assertRaises(ArgumentError):
                    self.parser.parse_args(['--python'])

    def test_all_pythons(self):
        args = self.parser.parse_args(['--all_pythons'])
        self.assertIsInstance(args.all_pythons, bool)
        self.assertTrue(args.all_pythons)

    def test_name(self):
        name = "thename"
        args = self.parser.parse_args(['--name', "thename"])
        self.assertIsInstance(args.name, list)
        self.assertEqual(args.name[0].name, name)

    def test_names(self):
        names = ["thename", "thename"]
        args = self.parser.parse_args(['--name', names[0], names[1]])
        self.assertIsInstance(args.name, list)
        for r, v in zip(args.name, names):
            self.assertEqual(r.name, v)

    def test_name_noarg(self):
        temp_stdout = StringIO()
        with redirect_stderr(temp_stdout):
            with self.assertRaises(SystemExit):
                with self.assertRaises(ArgumentError):
                    self.parser.parse_args(['--name'])

    def test_wheel(self):
        wheel_name = "thename"
        args = self.parser.parse_args([wheel_name])
        self.assertIsInstance(args.wheel, list)
        self.assertEqual(args.wheel[0].name, wheel_name)

    def test_wheels(self):
        wheels = ["thename", "thename"]
        args = self.parser.parse_args([*wheels])
        self.assertIsInstance(args.wheel, list)
        for r, v in zip(args.wheel, wheels):
            self.assertEqual(r.name, v)

    def test_wheel_noarg(self):
        args = self.parser.parse_args([])
        self.assertIsInstance(args.wheel, list)
        self.assertEqual(args.wheel, [])

    def test_requirement_noarg(self):
        """
        Test no value for the option.
        """
        temp_stdout = StringIO()
        with redirect_stderr(temp_stdout):
            with self.assertRaises(SystemExit):
                with self.assertRaises(ArgumentError):
                    self.parser.parse_args(['--requirement'])

    def test_requirement_file(self):
        """
        Test one requirements file.
        """
        args = self.parser.parse_args(["--requirement", "requirements.txt"])

        self.assertIsInstance(args.requirements, list)
        self.assertEqual(args.requirements, ["requirements.txt"])

    def test_requirement_files(self):
        """
        Test multiple requirements files.
        """
        args = self.parser.parse_args(["--requirement", "requirements.txt", "reqs.txt"])

        self.assertIsInstance(args.requirements, list)
        self.assertEqual(args.requirements, ["requirements.txt", "reqs.txt"])


class Test_is_compatible_method(unittest.TestCase):
    def setUp(self):
        self.wheel = avail_wheels.Wheel.parse_wheel_filename(arch="avx", filename="netCDF4-1.3.1-cp27-cp27mu-linux_x86_64.whl")

    def test_is_compatible_true(self):
        self.assertTrue(avail_wheels.is_compatible(self.wheel, ['2.7']))

    def test_is_compatible_false(self):
        self.assertFalse(avail_wheels.is_compatible(self.wheel, ['3.5']))

    def test_is_compatible_many(self):
        self.assertTrue(avail_wheels.is_compatible(self.wheel, avail_wheels.env.available_pythons))


class Test_match_file(unittest.TestCase):

    def setUp(self):
        tmp = ["netCDF4-1.3.1-cp27-cp27mu-linux_x86_64.whl",
               "torch_cpu-0.4.1-cp27-cp27mu-linux_x86_64.whl",
               "tensorflow_cpu-1.11.0+computecanada-cp36-cp36m-linux_x86_64.whl"]
        self.wheels = [wheel for wheel in tmp] + [wheel.upper() for wheel in tmp]
        self.rexes = [re.compile(translate(wheel), re.IGNORECASE) for wheel in tmp]

    def test_match_file_true(self):
        """ Match file name case sensitevely and insensitevely. """
        for wheel in self.wheels:
            self.assertTrue(avail_wheels.match_file(wheel, self.rexes))

    def test_match_file_false(self):
        """ Do not match file name case sensitevely and insensitevely. """
        for wheel in self.wheels:
            self.assertFalse(avail_wheels.match_file("None", self.rexes))


class Test_get_rexes(unittest.TestCase):
    def setUp(self):
        pass

    def rexes_compile(self, patterns):
        return [re.compile(translate(pattern), re.IGNORECASE) for pattern in patterns]

    def test_get_rexes(self):
        self.assertEqual(avail_wheels.get_rexes(["numpy", "Nump*"]), self.rexes_compile(patterns=["numpy-*.whl", "Nump*-*.whl"]))


class Test_add_not_available_wheels(unittest.TestCase):
    def setUp(self):
        self.wheels = defaultdict(list, {'torch_cpu': [avail_wheels.Wheel(filename="torch_cpu", name="torch_cpu")], 'numpy': [avail_wheels.Wheel(filename="numpy", name="numpy")]})

        self.wheel_names = ['a', 'b', 'torch*']

    def test_not_avail_empty(self):
        """ Test that an empty dict of wheels only contains the given wheel names. """
        ret = avail_wheels.add_not_available_wheels(defaultdict(list), self.wheel_names)

        self.assertEqual(ret, {'a': [avail_wheels.Wheel(filename='a', name='a')],
                               'b': [avail_wheels.Wheel(filename='b', name='b')],
                               'torch*': [avail_wheels.Wheel(filename="torch*", name="torch*")]})

    def test_not_avail(self):
        """ Test that wheels patterns are not added if they previously matched. """
        ret = avail_wheels.add_not_available_wheels(self.wheels, self.wheel_names)

        self.assertEqual(ret, {'a': [avail_wheels.Wheel(filename='a', name='a')],
                               'b': [avail_wheels.Wheel(filename='b', name='b')],
                               'torch_cpu': [avail_wheels.Wheel(filename="torch_cpu", name="torch_cpu")],
                               'numpy': [avail_wheels.Wheel(filename="numpy", name="numpy")]})


class Test_normalize_name(unittest.TestCase):
    def test_normalize_type(self):
        """ Test that return type is list. """
        self.assertIsInstance(avail_wheels.normalize_name(""), str)

    def test_normalize(self):
        """ Test that normalize empty list, names with multiple dash are converted to underscores. """
        names = ['', 'torch-cpu', 'torch_cpu', 'torch-cpu.gpu']
        truth = ['', 'torch_cpu', 'torch_cpu', 'torch_cpu.gpu']

        for name, true_name in zip(names, truth):
            ret = avail_wheels.normalize_name(name)
            self.assertEqual(ret, true_name)


class Test_filter_search_paths(unittest.TestCase):
    archs = ("sse3", "avx", "avx2", "avx512", "generic")

    def setUp(self):
        self.search_paths = [f'path/{path}' for path in self.archs]

    def test_get_all_search_paths(self):
        """
        Test that without any filter values all search paths are returned.
        """
        self.assertEqual(avail_wheels.filter_search_paths(self.search_paths, None), self.search_paths)
        self.assertEqual(avail_wheels.filter_search_paths(self.search_paths, []), self.search_paths)

    def test_get_arch(self):
        """
        Test that arch are correctly filtered
        """
        self.assertEqual(avail_wheels.filter_search_paths(self.search_paths, ['sse3']), ['path/sse3'])
        self.assertEqual(avail_wheels.filter_search_paths(self.search_paths, ['sse3', 'generic']), ['path/sse3', 'path/generic'])

        self.assertEqual(avail_wheels.filter_search_paths(self.search_paths, ['avx']), ['path/avx'])
        self.assertEqual(avail_wheels.filter_search_paths(self.search_paths, ['avx', 'generic']), ['path/avx', 'path/generic'])

        self.assertEqual(avail_wheels.filter_search_paths(self.search_paths, ['avx2']), ['path/avx2'])
        self.assertEqual(avail_wheels.filter_search_paths(self.search_paths, ['avx2', 'generic']), ['path/avx2', 'path/generic'])

        self.assertEqual(avail_wheels.filter_search_paths(self.search_paths, ['avx512']), ['path/avx512'])
        self.assertEqual(avail_wheels.filter_search_paths(self.search_paths, ['avx512', 'generic']), ['path/avx512', 'path/generic'])


class Test_search_paths(MonkeyTest):
    dummy_cfg = DummyPipConfigFile()
    dummy_wheelhouse = DummyWheelhouse()

    def setUp(self):
        super().setUp()
        self.dummy_cfg.create()
        self.dummy_wheelhouse.create()
        self.monkeypatch.setenv("WHEELHOUSE", self.dummy_wheelhouse.path)

    def tearDown(self):
        super().tearDown()
        self.dummy_cfg.remove()
        self.dummy_wheelhouse.remove()

    def test_no_pip_config_file(self):
        """
        Test that no PIP_CONFIG_FILE environment variable exists.
        Search paths are all directories from the wheelhouse.
        """
        self.monkeypatch.delenv("PIP_CONFIG_FILE", raising=False)
        reload(avail_wheels)  # Must reload script for env to be known

        other = sorted([f"{self.dummy_wheelhouse.path}/{p}" for p in self.dummy_wheelhouse.wheelhouse.keys()])
        res = sorted(avail_wheels.get_search_paths())

        self.assertEqual(res, other)

    def test_pip_config_file_empty(self):
        """
        Test that PIP_CONFIG_FILE environment variable exists but empty, entire wheelhouse is actually searched.
        """
        self.monkeypatch.setenv("PIP_CONFIG_FILE", "")
        reload(avail_wheels)  # Must reload script for env to be known

        other = sorted([f"{self.dummy_wheelhouse.path}/{p}" for p in self.dummy_wheelhouse.wheelhouse.keys()])
        res = sorted(avail_wheels.get_search_paths())

        self.assertEqual(res, other)

    def test_pip_config_file_exists(self):
        """
        Test that PIP_CONFIG_FILE environment variable exists and use the configuration file.
        """
        self.monkeypatch.setenv("PIP_CONFIG_FILE", self.dummy_cfg.filename)

        other = sorted(["/tmp/wheelhouse/gentoo/avx2", "/tmp/wheelhouse/gentoo/generic", "/tmp/wheelhouse/generic"])
        res = sorted(avail_wheels.get_search_paths())

        self.assertEqual(res, other)


if __name__ == '__main__':
    unittest.main()
