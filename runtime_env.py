#!/cvmfs/soft.computecanada.ca/custom/python/envs/avail_wheels/bin/python3

import os
from glob import glob


class RuntimeEnvironment(object):
    """
    RuntimeEnvironment class to evaluate in which environment we are.
    This effectively determine:
    - where is the wheelhouse located
    - which python version to use
    - which paths to search for wheels
    - which architecture
    - etc.
    """

    _wheelhouse = None
    _current_python = None
    _pip_config_file = None
    _python_dirs = None
    _current_architecture = None
    _available_architectures = frozenset(["avx", "avx2", "avx512", "generic", "sse3"])
    _available_pythons = None
    _compatible_pythons = None

    @property
    def wheelhouse(self):
        """
        Returns the wheelhouse path defined by the `WHEELHOUSE` environment variable.

        Default: /cvmfs/soft.computecanada.ca/custom/python/wheelhouse

        Returns
        -------
        str
            Path to the wheelhouse
        """
        if not self._wheelhouse:
            self._wheelhouse = os.environ.get(
                "WHEELHOUSE", "/cvmfs/soft.computecanada.ca/custom/python/wheelhouse"
            )

        return self._wheelhouse

    @property
    def pip_config_file(self):
        """
        Returns the pip configuration file path defined by the `PIP_CONFIG_FILE` environment variable
        or None if the variable is not defined.

        Returns
        -------
        str
            Path to the pip configuration file, or None
        """
        if not self._pip_config_file:
            self._pip_config_file = os.environ.get("PIP_CONFIG_FILE", None)

        return self._pip_config_file

    @property
    def current_python(self):
        """
        Returns the current python version or None if it could not be determined.

        The Python from the system is excluded.
        The Python version is sourced from a python module loaded or the Python from the activated virtual environment.

        Returns
        -------
        str
            Current Python version : major.minor.micro, or None
        """
        if not self._current_python:
            self._current_python = os.environ.get("EBVERSIONPYTHON", None)

        return self._current_python

    @property
    def python_directories(self):
        """
        Returns the python directories path defined by the PYTHON_DIRS environment variable.

        Default: /cvmfs/soft.computecanada.ca/easybuild/software/20*/Core/python

        Returns
        -------
        str
            Path to the Python directories (versions)
        """
        if not self._python_dirs:
            self._python_dirs = os.environ.get(
                "PYTHON_DIRS",
                "/cvmfs/soft.computecanada.ca/easybuild/software/20*/Core/python",
            )

        return self._python_dirs

    @property
    def current_architecture(self):
        """
        Returns the current architecture from RSNT_ARCH environment variable or None if it is not defined.

        Returns
        -------
        str
            Current architecture, or None
        """
        if not self._current_architecture:
            self._current_architecture = os.environ.get("RSNT_ARCH", None)

        return self._current_architecture

    @property
    def available_architectures(self):
        """
        Returns the available architectures from CVMFS.

        Returns
        -------
        list
            Available architectures
        """
        return self._available_architectures

    @property
    def available_pythons(self):
        """
        Returns available python versions (major.minor) from CVMFS.

        Returns
        -------
        list
            Available python versions
        """
        if not self._available_pythons:
            versions = set()
            for python_directory in glob(self.python_directories):
                for python_version in os.listdir(python_directory):
                    # Slice `3.8.0` to `3.8` (major.minor)
                    versions.add(python_version[:3])
            self._available_pythons = sorted(versions)

        return self._available_pythons

    @property
    def compatible_pythons(self):
        """
        Returns compatible pythons tags available.
        This includes universal (py2.py3, py3) and cpython tags.

        Returns
        -------
        list
            Compatible python tags
        """
        if not self._compatible_pythons:
            # {'2.7': ['py2.py3', 'py2', 'cp27'], '3.5': ['py2.py3', 'py3', 'cp35'], ...}
            self._compatible_pythons = {
                ap: ["py2.py3", f"py{ap[0]}", f"cp{ap[0]}{ap[2]}"]
                for ap in self.available_pythons
            }

        return self._compatible_pythons
