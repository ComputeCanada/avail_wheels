#!/cvmfs/soft.computecanada.ca/custom/python/envs/avail_wheels/bin/python3

import os
from glob import glob
import platform
import re
from packaging import tags, version


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
    _compatible_tags = None

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
            Current Python version : major.minor, or None
        """
        if not self._current_python:
            # virtual env. has precedence on modules
            if 'VIRTUAL_ENV' in os.environ:
                self._current_python = platform.python_version()
            else:
                self._current_python = os.environ.get("EBVERSIONPYTHON", None)

            # Keep major and minor parts
            if self._current_python:
                self._current_python = ".".join(self._current_python.split(".")[:2])

        return self._current_python

    @property
    def python_directories(self):
        """
        Returns the python directories path defined by the PYTHON_DIRS environment variable.

        Multiple paths must be separated by `:`.

        Default: /cvmfs/soft.computecanada.ca/easybuild/software/20*/Core/python:/cvmfs/soft.computecanada.ca/easybuild/software/20*/*/Core/python

        Returns
        -------
        str
            Path to the Python directories (versions)
        """
        if not self._python_dirs:
            self._python_dirs = os.environ.get(
                "PYTHON_DIRS",
                ":".join([
                    "/cvmfs/soft.computecanada.ca/easybuild/software/20*/Core/python",
                    "/cvmfs/soft.computecanada.ca/easybuild/software/20*/*/Core/python",
                ])
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
            for path in self.python_directories.split(':'):
                for python_directory in glob(path):
                    for python_version in os.listdir(python_directory):
                        if re.match(r"\d+.\d+(.\d+)?", python_version):
                            # Slice `3.8.0` to `3.8` (major.minor)
                            versions.add('.'.join(python_version.split('.')[:2]))
            # naturally sort versions
            self._available_pythons = sorted(versions, key=version.parse)

        return self._available_pythons

    @property
    def compatible_tags(self):
        """
        Returns compatible tags (interpreter-abi-platform) available.
        This includes universal (py2.py3, py3) and cpython tags.

        The tags returned are filtered for the available python instead of
        using a python range to generate the tags.

        For example, on a Linux system, for python 3.9:
        ```
            '3.9': frozenset([
                "cp39-cp39-linux_x86_64"
                "cp39-abi3-linux_x86_64",
                "cp39-none-linux_x86_64",
                "py3-none-linux_x86_64",
                "py39-none-linux_x86_64",
                "py3-none-any",
                "py39-none-any",
            ])
        ```

        Returns
        -------
        dict
            Compatible tags per available python version
        """
        if not self._compatible_tags:
            self._compatible_tags = {
                ap: frozenset(
                    filter(
                        lambda x: x.interpreter in (f"py{ap[0]}", f"py{ap[0]}{ap[2:]}", f"cp{ap[0]}{ap[2:]}"),
                        [
                            *tags.compatible_tags(
                                python_version=(int(ap[0]), int(ap[2:])), platforms=tags._generic_platforms()
                            ),
                            *tags.cpython_tags(
                                python_version=(int(ap[0]), int(ap[2:])), platforms=tags._generic_platforms()
                            ),
                        ],
                    )
                )
                for ap in self.available_pythons
            }

        return self._compatible_tags
