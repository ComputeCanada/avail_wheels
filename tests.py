import unittest
from pathlib import Path
from importlib import reload
from io import StringIO
from argparse import ArgumentError
from contextlib import redirect_stderr
from fnmatch import translate
from itertools import product
import os
import re
import avail_wheels


class Test_wheel_class(unittest.TestCase):
    def test_ctor_noparse(self):
        wheel = avail_wheels.Wheel("file", parse=False)
        self.assertEqual(wheel.filename, "file")

    def test_ctor_kwargs(self):
        wheel = avail_wheels.Wheel(filename="file", parse=False, arch='avx',
                                   name='torch_cpu', version='1.2.0', build="computecanada",
                                   python="cp36", abi="cp36m", platform="linux_x86_64")
        self.assertEqual(wheel.filename, "file")
        self.assertEqual(wheel.arch, "avx")
        self.assertEqual(wheel.name, "torch_cpu")
        self.assertEqual(wheel.version, "1.2.0")
        self.assertEqual(wheel.build, "computecanada")
        self.assertEqual(wheel.python, "cp36")
        self.assertEqual(wheel.abi, "cp36m")
        self.assertEqual(wheel.platform, "linux_x86_64")

    def test_parse_tags(self):
        filenames = ["avx2/netCDF4-1.3.1-cp36-cp36m-linux_x86_64.whl",
                     "avx/tensorflow_cpu-1.6.0+computecanada-cp36-cp36m-linux_x86_64.whl",
                     "generic/backports.functools_lru_cache-1.4-py2.py3-none-any.whl",
                     "sse3/Shapely-1.6.2.post1-cp35-cp35m-linux_x86_64.whl"]
        tags = {filenames[0]: {'arch': 'avx2', 'name': 'netCDF4', 'version': '1.3.1', 'build': '', 'python': 'cp36', 'abi': 'cp36m', 'platform': 'linux_x86_64'},
                filenames[1]: {'arch': 'avx', 'name': 'tensorflow_cpu', 'version': '1.6.0', 'build': "computecanada", 'python': 'cp36', 'abi': 'cp36m', 'platform': 'linux_x86_64'},
                filenames[2]: {'arch': 'generic', 'name': 'backports.functools_lru_cache', 'version': '1.4', 'build': '', 'python': 'py2.py3', 'abi': 'none', 'platform': "any"},
                filenames[3]: {'arch': 'sse3', 'name': 'Shapely', 'version': '1.6.2.post1', 'build': '', 'python': 'cp35', 'abi': 'cp35m', 'platform': "linux_x86_64"}}

        for file in filenames:
            wheel = avail_wheels.Wheel(file)
            self.assertEqual(wheel.filename, file)
            self.assertEqual(wheel.arch, tags[file]['arch'])
            self.assertEqual(wheel.name, tags[file]['name'])
            self.assertEqual(wheel.version, tags[file]['version'])
            self.assertEqual(wheel.build, tags[file]['build'])
            self.assertEqual(wheel.python, tags[file]['python'])
            self.assertEqual(wheel.abi, tags[file]['abi'])
            self.assertEqual(wheel.platform, tags[file]['platform'])

    def test_parse_tags_malformed_bad_sep(self):
        filename = "avx2/netCDF4-1.3.1.cp36-cp36m-linux_x86_64.whl"
        self.assertWarnsRegex(UserWarning, f"Could not get tags for : {filename}", avail_wheels.Wheel, filename=filename, parse=True)

    def test_parse_tags_malformed_missing_sep(self):
        filename = "avx2/netCDF4-1.3.1-cp36cp36m-linux_x86_64.whl"
        self.assertWarnsRegex(UserWarning, f"Could not get tags for : {filename}", avail_wheels.Wheel, filename=filename, parse=True)

    def test_parse_tags_malformed_missing_name(self):
        filename = "avx2/1.3.1-cp36-cp36m-linux_x86_64.whl"
        self.assertWarnsRegex(UserWarning, f"Could not get tags for : {filename}", avail_wheels.Wheel, filename=filename, parse=True)

    def test_wheel_print(self):
        wheel = str(avail_wheels.Wheel("file", parse=False))
        self.assertEqual(wheel, "file")

    def test_wheel_eq(self):
        a, b = avail_wheels.Wheel("avx2/torch_cpu-0.4.0-cp36-cp36m-linux_x86_64.whl"), avail_wheels.Wheel("avx2/torch_cpu-0.4.0-cp36-cp36m-linux_x86_64.whl")
        self.assertEqual(a, b)

    def test_wheel_noteq_attr(self):
        a, b = avail_wheels.Wheel("avx2/torch_cpu-0.4.0-cp36-cp36m-linux_x86_64.whl"), avail_wheels.Wheel("avx/torch_cpu-0.4.0-cp36-cp36m-linux_x86_64.whl")
        self.assertNotEqual(a, b)

    def test_wheel_noteq_instance(self):
        a, b = avail_wheels.Wheel("avx2/torch_cpu-0.4.0-cp36-cp36m-linux_x86_64.whl"), "avx2/torch_cpu-0.4.0-cp36-cp36m-linux_x86_64.whl"
        self.assertNotEqual(a, b)


class Test_latest_versions_method(unittest.TestCase):
    def setUp(self):
        self.wheels = {'netCDF4': [avail_wheels.Wheel("avx2/netCDF4-1.3.2-cp36-cp36m-linux_x86_64.whl"),
                                   avail_wheels.Wheel("avx2/netCDF4-1.3.2-cp35-cp35m-linux_x86_64.whl"),
                                   avail_wheels.Wheel("avx2/netCDF4-1.3.2-cp27-cp27mu-linux_x86_64.whl"),
                                   avail_wheels.Wheel("avx2/netCDF4-1.3.1-cp36-cp36m-linux_x86_64.whl"),
                                   avail_wheels.Wheel("avx2/netCDF4-1.3.1-cp36-cp36m-linux_x86_64.whl"),
                                   avail_wheels.Wheel("avx2/netCDF4-1.3.1-cp36-cp36m-linux_x86_64.whl"),
                                   avail_wheels.Wheel("avx2/netCDF4-1.2.0-cp36-cp36m-linux_x86_64.whl"),
                                   avail_wheels.Wheel("avx2/netCDF4-1.3-cp36-cp36m-linux_x86_64.whl")],
                       'torch_cpu': [avail_wheels.Wheel("avx2/torch_cpu-0.4.0-cp36-cp36m-linux_x86_64.whl")]}

        self.wheels['netCDF4'].reverse()

        self.latest_wheels = {'netCDF4': [avail_wheels.Wheel("avx2/netCDF4-1.3.2-cp27-cp27mu-linux_x86_64.whl"),
                                          avail_wheels.Wheel("avx2/netCDF4-1.3.2-cp35-cp35m-linux_x86_64.whl"),
                                          avail_wheels.Wheel("avx2/netCDF4-1.3.2-cp36-cp36m-linux_x86_64.whl")],
                              'torch_cpu': [avail_wheels.Wheel("avx2/torch_cpu-0.4.0-cp36-cp36m-linux_x86_64.whl")]}

    def test_latest_versions_method_all_pythons(self):
        ret = avail_wheels.latest_versions(self.wheels)
        self.assertEqual(ret, self.latest_wheels)


class Test_sort_method(unittest.TestCase):
    def setUp(self):
        self.wheels = {'netCDF4': [avail_wheels.Wheel("avx/netCDF4-1.3.1-cp27-cp27mu-linux_x86_64.whl"),
                                   avail_wheels.Wheel("avx/netCDF4-1.3.1-cp35-cp35m-linux_x86_64.whl"),
                                   avail_wheels.Wheel("avx/netCDF4-1.3.1-cp36-cp36m-linux_x86_64.whl"),
                                   avail_wheels.Wheel("avx2/netCDF4-1.3.1-cp27-cp27mu-linux_x86_64.whl"),
                                   avail_wheels.Wheel("avx2/netCDF4-1.3.1-cp35-cp35m-linux_x86_64.whl"),
                                   avail_wheels.Wheel("avx2/netCDF4-1.3.1-cp36-cp36m-linux_x86_64.whl"),
                                   avail_wheels.Wheel("sse3/netCDF4-1.3.1-cp27-cp27mu-linux_x86_64.whl"),
                                   avail_wheels.Wheel("sse3/netCDF4-1.3.1-cp35-cp35m-linux_x86_64.whl"),
                                   avail_wheels.Wheel("sse3/netCDF4-1.3.1-cp36-cp36m-linux_x86_64.whl"),
                                   avail_wheels.Wheel("generic/netCDF4-1.4.0-cp27-cp27mu-linux_x86_64.whl"),
                                   avail_wheels.Wheel("generic/netCDF4-1.2.8-cp27-cp27mu-linux_x86_64.whl")],

                       "botocore": [avail_wheels.Wheel("generic/botocore-1.10.63-py2.py3-none-any.whl"),
                                    avail_wheels.Wheel("generic/botocore-1.9.5-py2.py3-none-any.whl"),
                                    avail_wheels.Wheel("generic/botocore-1.10.57-py2.py3-none-any.whl"),
                                    avail_wheels.Wheel("generic/botocore-1.9.11-py2.py3-none-any.whl")],

                       "pydicom": [avail_wheels.Wheel("generic/pydicom-1.1.0-1-py2.py3-none-any.whl"),
                                   avail_wheels.Wheel("generic/pydicom-0.9.9-py3-none-any.whl")],


                       "torch_cpu": [avail_wheels.Wheel("avx2/torch_cpu-0.4.0-cp36-cp36m-linux_x86_64.whl"),
                                     avail_wheels.Wheel("avx2/torch_cpu-0.2.0+d8f3c60-cp27-cp27mu-linux_x86_64.whl")]}

        self.wheels['netCDF4'].reverse()

        self.output = [['botocore', '1.10.63', '', 'py2.py3', 'generic'],
                       ['botocore', '1.10.57', '', 'py2.py3', 'generic'],
                       ['botocore', '1.9.11', '', 'py2.py3', 'generic'],
                       ['botocore', '1.9.5', '', 'py2.py3', 'generic'],
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
                       ["pydicom", "1.1.0", "1", "py2.py3", "generic"],
                       ["pydicom", "0.9.9", "", "py3", "generic"],
                       ["torch_cpu", "0.4.0", "", "cp36", "avx2"],
                       ["torch_cpu", "0.2.0", "d8f3c60", "cp27", "avx2"]]

        self.condensed_output = [
            ["botocore", "1.10.63, 1.10.57, 1.9.11, 1.9.5", '', "py2.py3", "generic"],
            ["netCDF4", "1.4.0, 1.3.1, 1.2.8", '', "cp36, cp35, cp27", "sse3, generic, avx2, avx"],
            ["pydicom", "1.1.0, 0.9.9", "1, ", "py3, py2.py3", "generic"],
            ["torch_cpu", "0.4.0, 0.2.0", ", d8f3c60", "cp36, cp27", "avx2"]
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

        # Create the wheelhouse and its subdirs, files.
        for stack in ['generic']:
            for arch in avail_wheels.AVAILABLE_ARCHITECTURES:
                os.makedirs(f"{self.wheelhouse}/{stack}/{arch}", exist_ok=True)
                for files in self.raw_filenames.values():
                    for file in files:
                        Path(f"{self.wheelhouse}/{stack}/{arch}/{file}").touch()

    def tearDown(self):
        # Delete wheelhouse
        for stack in ['generic']:
            for arch in avail_wheels.AVAILABLE_ARCHITECTURES:
                for files in self.raw_filenames.values():
                    for file in files:
                        os.remove(f"{self.wheelhouse}/{stack}/{arch}/{file}")
                os.rmdir(f"{self.wheelhouse}/{stack}/{arch}")
            os.rmdir(f"{self.wheelhouse}/{stack}")
        os.rmdir(self.wheelhouse)

    def test_get_wheels_all_archs_all_pythons(self):
        other = {'netCDF4': [], 'torch_cpu': []}
        for arch in avail_wheels.AVAILABLE_ARCHITECTURES:
            for wheel_name, files in self.raw_filenames.items():
                for file in files:
                    other[wheel_name].append(avail_wheels.Wheel(f"{arch}/{file}"))

        ret = avail_wheels.get_wheels(path=self.wheelhouse, archs=avail_wheels.AVAILABLE_ARCHITECTURES, pythons=avail_wheels.AVAILABLE_PYTHONS, names_versions=product('*', '*'), latest=False)
        self.assertEqual(ret, other)

    def test_get_wheels_arch_all_pythons(self):
        archs = ['avx2']
        other = {'netCDF4': [], 'torch_cpu': []}
        for arch in archs:
            for wheel_name, files in self.raw_filenames.items():
                for file in files:
                    other[wheel_name].append(avail_wheels.Wheel(f"{arch}/{file}"))

        ret = avail_wheels.get_wheels(path=self.wheelhouse, archs=archs, pythons=avail_wheels.AVAILABLE_PYTHONS, names_versions=product('*', '*'), latest=False)
        self.assertEqual(ret, other)

    def test_get_wheels_arch_python(self):
        archs = ['avx2']
        pythons = ['3.6']
        other = {'netCDF4': [avail_wheels.Wheel(f"{archs[0]}/{self.raw_filenames['netCDF4'][2]}"),
                             avail_wheels.Wheel(f"{archs[0]}/{self.raw_filenames['netCDF4'][3]}")],
                 'torch_cpu': [avail_wheels.Wheel(f"{archs[0]}/{self.raw_filenames['torch_cpu'][0]}")]}

        ret = avail_wheels.get_wheels(path=self.wheelhouse, archs=archs, pythons=pythons, names_versions=product('*', '*'), latest=False)
        self.assertEqual(ret, other)

    def test_get_wheels_exactname_arch_python(self):
        archs = ['avx2']
        pythons = ['3.6']
        exactname = "netCDF4"
        other = {'netCDF4': [avail_wheels.Wheel(f"{archs[0]}/{self.raw_filenames['netCDF4'][2]}"),
                             avail_wheels.Wheel(f"{archs[0]}/{self.raw_filenames['netCDF4'][3]}")]}

        ret = avail_wheels.get_wheels(path=self.wheelhouse, archs=archs, pythons=pythons, names_versions=product([exactname], '*'), latest=False)
        self.assertEqual(ret, other)

    def test_get_wheels_wildname_arch_python(self):
        archs = ['avx2']
        pythons = ['3.6']
        wildname = "*CDF*"
        other = {'netCDF4': [avail_wheels.Wheel(f"{archs[0]}/{self.raw_filenames['netCDF4'][2]}"),
                             avail_wheels.Wheel(f"{archs[0]}/{self.raw_filenames['netCDF4'][3]}")]}

        ret = avail_wheels.get_wheels(path=self.wheelhouse, archs=archs, pythons=pythons, names_versions=product([wildname], "*"), latest=False)
        self.assertEqual(ret, other)

    def test_get_wheels_wildname_arch_python_version(self):
        archs = ['avx2']
        pythons = ['3.6']
        wildname = "*CDF*"
        version = '1.3.1'
        other = {'netCDF4': [avail_wheels.Wheel(f"{archs[0]}/{self.raw_filenames['netCDF4'][3]}")]}

        ret = avail_wheels.get_wheels(path=self.wheelhouse, archs=archs, pythons=pythons, names_versions=product([wildname], [version]), latest=False)
        self.assertEqual(ret, other)

    def test_get_wheels_wildversion_wildname_arch_python(self):
        archs = ['avx2']
        pythons = ['3.6']
        wildname = "*CDF*"
        version = '1.2.*'
        other = {'netCDF4': [avail_wheels.Wheel(f"{archs[0]}/{self.raw_filenames['netCDF4'][2]}")]}

        ret = avail_wheels.get_wheels(path=self.wheelhouse, archs=archs, pythons=pythons, names_versions=product([wildname], [version]), latest=False)
        self.assertEqual(ret, other)

    def test_get_wheels_wrongversion_wildname_arch_python(self):
        archs = ['avx2']
        pythons = ['3.6']
        wildname = "*CDF*"
        version = '2.3'
        other = {}

        ret = avail_wheels.get_wheels(path=self.wheelhouse, archs=archs, pythons=pythons, names_versions=product([wildname], [version]), latest=False)
        self.assertEqual(ret, other)


class Test_parse_args_method(unittest.TestCase):
    def setUp(self):
        self.redoSetUp(arch='sse3', python='3.6.3')

    def redoSetUp(self, arch=None, python=None):
        self.current_architecture = arch
        self.current_python = python

        if arch:
            os.environ['RSNT_ARCH'] = arch
        elif 'RSNT_ARCH' in os.environ:
            del os.environ['RSNT_ARCH']

        if python:
            os.environ['EBVERSIONPYTHON'] = python
        elif 'EBVERSIONPYTHON' in os.environ:
            del os.environ['EBVERSIONPYTHON']

        reload(avail_wheels)  # Must reload script for env to be known
        self.parser = avail_wheels.create_argparser()

    def test_default_arch(self):
        default_arch = ['generic', self.current_architecture]
        self.parser.parse_args([])
        self.assertEqual(avail_wheels.CURRENT_ARCHITECTURE, self.current_architecture)
        self.assertEqual(avail_wheels.ARCHITECTURES, default_arch)
        self.assertEqual(self.parser.get_default('arch'), default_arch)

    def test_default_noarch(self):
        """ Special case (eg on personnal system). """
        self.redoSetUp()  # Need to overwrite setUp
        default_arch = ['generic', self.current_architecture]
        self.parser.parse_args([])

        self.assertEqual(avail_wheels.CURRENT_ARCHITECTURE, self.current_architecture)
        self.assertEqual(avail_wheels.ARCHITECTURES, default_arch)
        self.assertEqual(self.parser.get_default('arch'), default_arch)

    def test_default_python(self):
        default_python = ['3.6']
        self.parser.parse_args([])

        self.assertEqual(avail_wheels.CURRENT_PYTHON, self.current_python)
        self.assertEqual(self.parser.get_default('python'), default_python)

    def test_default_nopython(self):
        """ Special case when no modules are loaded or on personnal system. """
        self.redoSetUp()  # Need to overwrite setUp
        self.parser.parse_args([])

        self.assertEqual(avail_wheels.CURRENT_PYTHON, self.current_python)
        self.assertEqual(self.parser.get_default('python'), avail_wheels.AVAILABLE_PYTHONS)

    def test_default_name(self):
        self.parser.parse_args([])
        self.assertEqual(self.parser.get_default('name'), None)

    def test_default_wheel(self):
        self.parser.parse_args([])
        self.assertEqual(self.parser.get_default('wheel'), ['*'])

    def test_default_version(self):
        self.parser.parse_args([])
        self.assertEqual(self.parser.get_default('version'), ["*"])

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
        version = ['1.2*']
        args = self.parser.parse_args(['--version', version[0]])
        self.assertIsInstance(args.version, list)
        self.assertEqual(args.version, version)

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
        names = ["thename"]
        args = self.parser.parse_args(['--name', names[0]])
        self.assertIsInstance(args.name, list)
        self.assertEqual(args.name, names)

    def test_names(self):
        names = ["thename", "thename"]
        args = self.parser.parse_args(['--name', names[0], names[1]])
        self.assertIsInstance(args.name, list)
        self.assertEqual(args.name, names)

    def test_name_noarg(self):
        temp_stdout = StringIO()
        with redirect_stderr(temp_stdout):
            with self.assertRaises(SystemExit):
                with self.assertRaises(ArgumentError):
                    self.parser.parse_args(['--name'])

    def test_wheel(self):
        wheels = ["thename"]
        args = self.parser.parse_args([wheels[0]])
        self.assertIsInstance(args.wheel, list)
        self.assertEqual(args.wheel, wheels)

    def test_wheels(self):
        wheels = ["thename", "thename"]
        args = self.parser.parse_args([*wheels])
        self.assertIsInstance(args.wheel, list)
        self.assertEqual(args.wheel, wheels)

    def test_wheel_noarg(self):
        args = self.parser.parse_args([])
        self.assertIsInstance(args.wheel, list)
        self.assertEqual(args.wheel, ['*'])


class Test_is_compatible_method(unittest.TestCase):
    def setUp(self):
        self.wheel = avail_wheels.Wheel("avx/netCDF4-1.3.1-cp27-cp27mu-linux_x86_64.whl")

    def test_is_compatible_none(self):
        self.assertFalse(avail_wheels.is_compatible(self.wheel, None))

    def test_is_compatible_true(self):
        self.assertTrue(avail_wheels.is_compatible(self.wheel, ['2.7']))

    def test_is_compatible_false(self):
        self.assertFalse(avail_wheels.is_compatible(self.wheel, ['3.5']))

    def test_is_compatible_many(self):
        self.assertTrue(avail_wheels.is_compatible(self.wheel, avail_wheels.AVAILABLE_PYTHONS))


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

    def test_get_rexes_star_star(self):
        self.assertEqual(avail_wheels.get_rexes(product(['*'], ['*'])), self.rexes_compile(patterns=["*-*[-+]*.whl"]))

    def test_get_rexes_star_version(self):
        self.assertEqual(avail_wheels.get_rexes(product(['*'], ['1.2'])), self.rexes_compile(patterns=["*-1.2[-+]*.whl"]))

    def test_get_rexes_star_versions(self):
        self.assertEqual(avail_wheels.get_rexes(product(['*'], ['1.2', '0.4.*'])), self.rexes_compile(patterns=["*-1.2[-+]*.whl", "*-0.4.*[-+]*.whl"]))

    def test_get_rexes_name_star(self):
        self.assertEqual(avail_wheels.get_rexes(product(["numpy", "NUMPY"], ['*'])), self.rexes_compile(patterns=["numpy-*[-+]*.whl", "NUMPY-*[-+]*.whl"]))

    def test_get_rexes_name_version(self):
        self.assertEqual(avail_wheels.get_rexes(product(["numpy", "NUMPY"], ["1.2"])), self.rexes_compile(patterns=["numpy-1.2[-+]*.whl", "NUMPY-1.2[-+]*.whl"]))

    def test_get_rexes_names_star(self):
        self.assertEqual(avail_wheels.get_rexes(product(["numpy", "TORCH_CPU"], ['*'])), self.rexes_compile(patterns=["numpy-*[-+]*.whl", "TORCH_CPU-*[-+]*.whl"]))

    def test_get_rexes_names_version(self):
        self.assertEqual(avail_wheels.get_rexes(product(["numpy", "TORCH_CPU"], ["1.2"])), self.rexes_compile(patterns=["numpy-1.2[-+]*.whl", "TORCH_CPU-1.2[-+]*.whl"]))

    def test_get_rexes_names_versions(self):
        self.assertEqual(avail_wheels.get_rexes(product(["numpy", "TORCH_CPU"], ["1.2", "0.4*"])), self.rexes_compile(patterns=["numpy-1.2[-+]*.whl", "numpy-0.4*[-+]*.whl", "TORCH_CPU-1.2[-+]*.whl", "TORCH_CPU-0.4*[-+]*.whl"]))


class Test_add_not_available_wheels(unittest.TestCase):
    def setUp(self):
        self.wheels = {'torch_cpu': [avail_wheels.Wheel(filename="torch_cpu", name="torch_cpu", parse=False)],
                       'numpy': [avail_wheels.Wheel(filename="numpy", name="numpy", parse=False)]}

        self.wheel_names = ['a', 'b', 'torch*']

    def test_not_avail_empty(self):
        """ Test that an empty dict of wheels only contains the given wheel names. """
        ret = avail_wheels.add_not_available_wheels({}, self.wheel_names)

        self.assertEqual(ret, {'a': [avail_wheels.Wheel(filename='a', name='a', parse=False)],
                               'b': [avail_wheels.Wheel(filename='b', name='b', parse=False)],
                               'torch*': [avail_wheels.Wheel(filename="torch*", name="torch*", parse=False)]})

    def test_not_avail(self):
        """ Test that wheels patterns are not added if they previously matched. """
        ret = avail_wheels.add_not_available_wheels(self.wheels, self.wheel_names)

        self.assertEqual(ret, {'a': [avail_wheels.Wheel(filename='a', name='a', parse=False)],
                               'b': [avail_wheels.Wheel(filename='b', name='b', parse=False)],
                               'torch_cpu': [avail_wheels.Wheel(filename="torch_cpu", name="torch_cpu", parse=False)],
                               'numpy': [avail_wheels.Wheel(filename="numpy", name="numpy", parse=False)]})


class Test_normalize_names(unittest.TestCase):
    def test_normalize_type(self):
        """ Test that return type is list. """
        self.assertIsInstance(avail_wheels.normalize_names([]), list)

    def test_normalize(self):
        """ Test that normalize empty list, names with multiple dash are converted to underscores. """
        self.assertEqual(avail_wheels.normalize_names([]), [])

        names = ['', 'torch-cpu', 'torch_cpu', 'torch-cpu-gpu']
        ret = avail_wheels.normalize_names(names)
        self.assertEqual(ret, ['', 'torch_cpu', 'torch_cpu', 'torch_cpu_gpu'])


if __name__ == '__main__':
    unittest.main()
