#!/cvmfs/soft.computecanada.ca/custom/python/envs/avail_wheels/bin/python3

import os
from glob import glob
from subprocess import run
from functools import cached_property

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

    _available_architectures_2023 = frozenset(["x86-64-v3", "x86-64-v4", "generic"])
    _available_architectures_2020 = frozenset(["avx", "avx2", "avx512", "generic", "sse3"])

    @cached_property
    def wheelhouse(self):
        """
        Returns the wheelhouse path defined by the `WHEELHOUSE` environment variable.

        Default: /cvmfs/soft.computecanada.ca/custom/python/wheelhouse

        Returns
        -------
        str
            Path to the wheelhouse
        """
        return os.environ.get(
            "WHEELHOUSE", "/cvmfs/soft.computecanada.ca/custom/python/wheelhouse"
        )

    @cached_property
    def pip_config_file(self):
        """
        Returns the pip configuration file path defined by the `PIP_CONFIG_FILE` environment variable
        or None if the variable is not defined.

        Returns
        -------
        str
            Path to the pip configuration file, or None
        """
        return os.environ.get("PIP_CONFIG_FILE", None)

    @cached_property
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
        # virtual env. has precedence on modules
        if 'VIRTUAL_ENV' in os.environ:
            try:
                with open(f"{os.environ['VIRTUAL_ENV']}/pyvenv.cfg") as f:
                    for line in f:
                        key, _, value = line.partition('=')
                        if key.strip().startswith('version'):
                            python = value.strip()
                            break
            except (OSError, IOError):
                # fallback to subprocess if pyvenv.cfg is missing or unreadable
                python = run(["python", "-c", "import platform; print(platform.python_version())"], text=True, capture_output=True).stdout.strip()
        else:
            python = os.environ.get("EBVERSIONPYTHON", None)

        # Keep major and minor parts
        if python:
            python = ".".join(python.split(".")[:2])

        return python

    @cached_property
    def python_directories(self):
        """
        Returns the python directories path defined by the PYTHON_DIRS environment variable.

        Multiple paths must be separated by `:`.

        Default: /cvmfs/soft.computecanada.ca/easybuild/software/20*/Core/python:/cvmfs/soft.computecanada.ca/easybuild/software/20*/*/Core/python:/cvmfs/soft.computecanada.ca/easybuild/software/20*/*/Compiler/gcccore/python

        Returns
        -------
        str
            Path to the Python directories (versions)
        """
        return os.environ.get(
            "PYTHON_DIRS",
            ":".join([
                "/cvmfs/soft.computecanada.ca/easybuild/software/20*/Core/python",
                "/cvmfs/soft.computecanada.ca/easybuild/software/20*/*/Core/python",
                "/cvmfs/soft.computecanada.ca/easybuild/software/20*/*/Compiler/gcccore/python"
            ])
        )


    @cached_property
    def current_architecture(self):
        """
        Returns the current architecture from RSNT_ARCH environment variable or None if it is not defined.

        Returns
        -------
        str
            Current architecture, or None
        """
        return os.environ.get("RSNT_ARCH", None)

    @cached_property
    def available_architectures(self):
        """
        Returns the available architectures from CVMFS.

        Returns
        -------
        list
            Available architectures
        """
        # If gentoo 2023 or newer, use new architecture names
        if int(os.environ.get("EBVERSIONGENTOO", -1)) >= 2023:
            return self._available_architectures_2023
        else:
            return self._available_architectures_2020

    @cached_property
    def available_pythons(self):
        """
        Returns available python versions (major.minor) from CVMFS.

        Returns
        -------
        list
            Available python versions
        """
        versions = set()

        for path in self.python_directories.split(':'):
            for python_directory in glob(path):
                for python_version in os.listdir(python_directory):
                    parts = python_version.split('.')
                    if len(parts) > 1 and all(p.isdigit() for p in parts):
                        versions.add(f"{parts[0]}.{parts[1]}")

        # naturally sort versions
        return sorted(versions, key=lambda v:tuple(int(x) for x in v.split('.')))

    @cached_property
    def compatible_tags(self):
        """
        Returns compatible tags (interpreter-abi-platform) available.
        This includes universal (py2.py3, py3) and cpython tags.

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
                ...
            ])
        ```
        and previous compatible tags, like `cp38-abi3-linux_x86_64` or `py37-none-linux_x86_64`.

        Returns
        -------
        dict
            Compatible tags per available python version
        """
        from packaging import tags # lazy import
        platforms = tuple(tags._generic_platforms())

        return {
            ap: frozenset(
                [
                    *tags.compatible_tags(
                        python_version=(int(ap[0]), int(ap[2:])), platforms=platforms
                    ),
                    *tags.cpython_tags(
                        python_version=(int(ap[0]), int(ap[2:])), platforms=platforms
                    ),
                ],
            )
            for ap in self.available_pythons
        }
