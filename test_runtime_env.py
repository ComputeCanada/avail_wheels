import unittest
import os
from runtime_env import RuntimeEnvironment


class Test_wheelhouse(unittest.TestCase):
    WHEELHOUSE__KEY = "WHEELHOUSE"

    def setUp(self, wheelhouse=None):
        """
        Set up the test with specific context.
        """
        os.environ.pop(self.WHEELHOUSE__KEY, None)
        if wheelhouse is not None:
            os.environ[self.WHEELHOUSE__KEY] = wheelhouse

        self.env = RuntimeEnvironment()

    def test_wheelhouse_default(self):
        """
        Test that the default wheelhouse is /cvmfs/soft.computecanada.ca/custom/python/wheelhouse
        """
        self.assertEqual(self.env.wheelhouse, "/cvmfs/soft.computecanada.ca/custom/python/wheelhouse")

    def test_wheelhouse_variable(self):
        """
        Test that the wheelhouse is read from WHEELHOUSE enviroment variable.
        """
        self.setUp(wheelhouse="potato/house/")
        self.assertEqual(self.env.wheelhouse, "potato/house/")


class Test_pip_config_file(unittest.TestCase):
    PIP_CONFIG_FILE__KEY = "PIP_CONFIG_FILE"

    def setUp(self, pip_config_file=None):
        """
        Set up the test with specific context.
        """
        os.environ.pop(self.PIP_CONFIG_FILE__KEY, None)
        if pip_config_file is not None:
            os.environ[self.PIP_CONFIG_FILE__KEY] = pip_config_file

        self.env = RuntimeEnvironment()

    def test_pip_config_file_default(self):
        """
        Test that the default pip_config_file is None
        """
        self.assertIsNone(self.env.pip_config_file)

    def test_pip_config_file_variable(self):
        """
        Test that the pip config file is read from PIP_CONFIG_FILE enviroment variable.
        """
        self.setUp(pip_config_file="pip.conf")
        self.assertEqual(self.env.pip_config_file, "pip.conf")


class Test_current_python(unittest.TestCase):
    MODULE_PYTHON_VER__KEY = "EBVERSIONPYTHON"

    def setUp(self, current_python=None):
        """
        Set up the test with specific context.
        """
        os.environ.pop(self.MODULE_PYTHON_VER__KEY, None)
        if current_python is not None:
            os.environ[self.MODULE_PYTHON_VER__KEY] = current_python

        self.env = RuntimeEnvironment()

    def test_current_python_default(self):
        """
        Test that the default current_python is None
        """
        self.assertIsNone(self.env.current_python)

    def test_current_python_variable(self):
        """
        Test that the current python version is read from EBVERSIONPYTHON enviroment variable.
        """
        self.setUp(current_python="3.8.2")
        self.assertEqual(self.env.current_python, "3.8.2")


class Test_python_dirs(unittest.TestCase):
    PYTHON_DIRS__KEY = "PYTHON_DIRS"

    def setUp(self, python_dirs=None):
        """
        Set up the test with specific context.
        """
        os.environ.pop(self.PYTHON_DIRS__KEY, None)
        if python_dirs is not None:
            os.environ[self.PYTHON_DIRS__KEY] = python_dirs

        self.env = RuntimeEnvironment()

    def test_python_dirs_default(self):
        """
        Test that the default python directories is from /cvmfs/soft.computecanada.ca/easybuild/software/20*/Core/python
        """
        self.assertEqual(self.env.python_directories, "/cvmfs/soft.computecanada.ca/easybuild/software/20*/Core/python")

    def test_python_dirs_variable(self):
        """
        Test that the python directories is read from PYTHON_DIRS enviroment variable.
        """
        self.setUp(python_dirs="potato/dir/")
        self.assertEqual(self.env.python_directories, "potato/dir/")


class Test_current_architecture(unittest.TestCase):
    CURRENT_ARCHITECTURES__KEY = "RSNT_ARCH"

    def setUp(self, current_architecture=None):
        """
        Set up the test with specific context.
        """
        os.environ.pop(self.CURRENT_ARCHITECTURES__KEY, None)
        if current_architecture is not None:
            os.environ[self.CURRENT_ARCHITECTURES__KEY] = current_architecture

        self.env = RuntimeEnvironment()

    def test_current_architecture_default(self):
        """
        Test that the default current_architecture is None
        """
        self.assertIsNone(self.env.current_architecture)

    def test_current_architecture_variable(self):
        """
        Test that the current python version is read from EBVERSIONPYTHON enviroment variable.
        """
        for arch in self.env.available_architectures:
            self.setUp(current_architecture=arch)
            self.assertEqual(self.env.current_architecture, arch)


class Test_available_architectures(unittest.TestCase):
    def setUp(self, current_python=None):
        """
        Set up the test with specific context.
        """
        self.env = RuntimeEnvironment()

    def test_available_architectures(self):
        """
        Test that the default available_architectures is a frozenset(['avx', 'avx2', 'avx512', 'generic', 'sse3'])
        """
        self.assertIsInstance(self.env.available_architectures, frozenset)
        self.assertEqual(self.env.available_architectures, frozenset(['avx', 'avx2', 'avx512', 'generic', 'sse3']))


class Test_available_pythons(unittest.TestCase):
    def setUp(self):
        """
        Set up the test with specific context.
        """
        self.env = RuntimeEnvironment()

    def test_available_pythons(self):
        """
        Test that the default available pythons versions are from CVMFS.
        """
        self.assertEqual(self.env.available_pythons, ["2.7", "3.5", "3.6", "3.7", "3.8"])


class Test_compatible_pythons(unittest.TestCase):
    def setUp(self):
        """
        Set up the test with specific context.
        """
        self.env = RuntimeEnvironment()

    def test_compatible_pythons(self):
        """
        Test that the default compatible pythons versions are from CVMFS.
        """
        self.assertIsInstance(self.env.compatible_pythons, dict)
        for av in self.env.available_pythons:
            self.assertIsInstance(self.env.compatible_pythons[av], list)
            self.assertEqual(self.env.compatible_pythons[av], ["py2.py3", f"py{av[0]}", f"cp{av.replace('.', '')}"])


if __name__ == '__main__':
    unittest.main()
