import unittest
import sys
from runtime_env import RuntimeEnvironment
from pytest import MonkeyPatch


class MonkeyTest(unittest.TestCase):
    def setUp(self):
        self.monkeypatch = MonkeyPatch()
        self.env = RuntimeEnvironment()

    def tearDown(self):
        self.monkeypatch.undo()


class Test_wheelhouse(MonkeyTest):
    def test_wheelhouse_default(self):
        """
        Test that the default wheelhouse is /cvmfs/soft.computecanada.ca/custom/python/wheelhouse
        """
        self.monkeypatch.delenv("WHEELHOUSE", raising=False)
        self.assertEqual(self.env.wheelhouse, "/cvmfs/soft.computecanada.ca/custom/python/wheelhouse")

    def test_wheelhouse_variable(self):
        """
        Test that the wheelhouse is read from WHEELHOUSE enviroment variable.
        """
        self.monkeypatch.setenv("WHEELHOUSE", "potato/house/")
        self.assertEqual(self.env.wheelhouse, "potato/house/")


class Test_pip_config_file(MonkeyTest):
    def test_pip_config_file_default(self):
        """
        Test that the default pip_config_file is None
        """
        self.monkeypatch.delenv("PIP_CONFIG_FILE", raising=False)
        self.assertIsNone(self.env.pip_config_file)

    def test_pip_config_file_variable(self):
        """
        Test that the pip config file is read from PIP_CONFIG_FILE enviroment variable.
        """
        self.monkeypatch.setenv("PIP_CONFIG_FILE", "pip.conf")
        self.assertEqual(self.env.pip_config_file, "pip.conf")


class Test_current_python(MonkeyTest):
    def test_current_python_default(self):
        """
        Test that the default current_python is None
        """
        self.monkeypatch.delenv('VIRTUAL_ENV', raising=False)
        self.monkeypatch.delenv('EBVERSIONPYTHON', raising=False)

        self.assertIsNone(self.env.current_python)

    def test_current_python_variable_module(self):
        """
        Test that the current python version is read from EBVERSIONPYTHON enviroment variable.
        """
        v = "3.8.2"
        self.monkeypatch.setenv('EBVERSIONPYTHON', v)
        self.monkeypatch.delenv('VIRTUAL_ENV', raising=False)

        self.assertEqual(self.env.current_python, v)

    def test_current_python_variable_venv(self):
        """
        Test that the current python version is read from VIRTUAL_ENV enviroment variable.
        """
        v = sys.version_info
        self.monkeypatch.delenv('EBVERSIONPYTHON', raising=False)

        self.assertEqual(self.env.current_python, f"{v.major}.{v.minor}.{v.micro}")


class Test_python_dirs(MonkeyTest):
    def test_python_dirs_default(self):
        """
        Test that the default python directories is from /cvmfs/soft.computecanada.ca/easybuild/software/20*/Core/python
        """
        self.monkeypatch.delenv("PYTHON_DIRS", raising=False)
        self.assertEqual(self.env.python_directories, "/cvmfs/soft.computecanada.ca/easybuild/software/20*/Core/python")

    def test_python_dirs_variable(self):
        """
        Test that the python directories is read from PYTHON_DIRS enviroment variable.
        """
        self.monkeypatch.setenv("PYTHON_DIRS", "potato/dir/")
        self.assertEqual(self.env.python_directories, "potato/dir/")


class Test_current_architecture(MonkeyTest):
    def test_current_architecture_default(self):
        """
        Test that the default current architecture is None when RSNT_ARCH is not defined
        """
        self.monkeypatch.delenv("RSNT_ARCH", raising=False)
        self.assertIsNone(self.env.current_architecture)

    def test_current_architecture_variable(self):
        """
        Test that the current architecture is read from RSNT_ARCH enviroment variable.
        """
        arch = "generic"
        self.monkeypatch.setenv("RSNT_ARCH", arch)
        self.assertEqual(self.env.current_architecture, arch)


class Test_available_architectures(MonkeyTest):
    def test_available_architectures(self):
        """
        Test that the default available_architectures is a frozenset(['avx', 'avx2', 'avx512', 'generic', 'sse3'])
        """
        self.assertIsInstance(self.env.available_architectures, frozenset)
        self.assertEqual(self.env.available_architectures, frozenset(['avx', 'avx2', 'avx512', 'generic', 'sse3']))


class Test_available_pythons(MonkeyTest):
    def test_available_pythons(self):
        """
        Test that the default available pythons versions are from CVMFS.
        """
        # TODO : Add test helper to construct python directories to test
        self.monkeypatch.delenv("PYTHON_DIRS", raising=False)
        self.assertEqual(self.env.available_pythons, ["2.7", "3.5", "3.6", "3.7", "3.8"])


class Test_compatible_pythons(MonkeyTest):
    def test_compatible_pythons(self):
        """
        Test that the default compatible pythons versions are from CVMFS.
        """
        self.assertIsInstance(self.env.compatible_pythons, dict)
        for av in self.env.available_pythons:
            self.assertIsInstance(self.env.compatible_pythons[av], frozenset)
            self.assertEqual(self.env.compatible_pythons[av], frozenset(["py2.py3", f"py{av[0]}", f"cp{av.replace('.', '')}"]))


if __name__ == '__main__':
    unittest.main()
