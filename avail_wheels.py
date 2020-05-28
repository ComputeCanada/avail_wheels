#!/cvmfs/soft.computecanada.ca/custom/python/envs/avail_wheels/bin/python3

import os
import sys
import re
import argparse
import fnmatch
import operator
from tabulate import tabulate
from packaging import version
from itertools import product

__version__ = "1.1.1"

WHEELHOUSE = os.environ.get("WHEELHOUSE", "/cvmfs/soft.computecanada.ca/custom/python/wheelhouse")
PYTHONS_DIR = os.environ.get("PYTHONS_DIR", "/cvmfs/soft.computecanada.ca/easybuild/software/2017/Core/python")

CURRENT_ARCHITECTURE = os.environ.get("RSNT_ARCH")
AVAILABLE_ARCHITECTURES = sorted(os.listdir(WHEELHOUSE))  # Get the available architectures from CVMFS
ARCHITECTURES = ['generic', CURRENT_ARCHITECTURE]

AVAILABLE_PYTHONS = sorted({pv[:3] for pv in os.listdir(PYTHONS_DIR) if re.match(r"\d+.\d+(.\d+)?", pv)})  # Get the available python versions from CVMFS
CURRENT_PYTHON = os.environ.get("EBVERSIONPYTHON")
# {'2.7': ['py2.py3', 'py2', 'cp27'], '3.5': ['py2.py3', 'py3', 'cp35'], ...}
COMPATIBLE_PYTHON = {ap: ['py2.py3', f"py{ap[0]}", f"cp{ap[0]}{ap[2]}"] for ap in AVAILABLE_PYTHONS}

AVAILABLE_HEADERS = ['name', 'version', 'build', 'python', 'abi', 'platform', 'arch']
HEADERS = ['name', 'version', 'build', 'python', 'arch']

DEFAULT_STAR_ARG = ['*']


class Wheel():
    """
    The representation of a wheel and its tags.
    """

    # The wheel filename is {arch}/{distribution}-{version}([-+]{build tag})?-{python tag}-{abi tag}-{platform tag}.whl.
    # The version can be numeric, alpha or alphanum or a combinaison.
    WHEEL_RE = re.compile(r"(?P<arch>\w+)/(?P<name>[\w.]+)-(?P<version>(?:[\w\.]+)?)(?:[\+-](?P<build>\w+))*?-(?P<python>[\w\.]+)-(?P<abi>\w+)-(?P<platform>\w+)")

    filename, arch, name, version, build, python, abi, platform = "", "", "", "", "", "", "", ""

    def __init__(self, filename, parse=True, **kwargs):
        self.filename = filename
        self.__dict__.update(kwargs)

        if parse:
            self.parse_tags(filename)

    def parse_tags(self, wheel):
        """
        Parse and set wheel tags.
        The wheel filename is {arch}/{distribution}-{version}([-+]{build tag})?-{python tag}-{abi tag}-{platform tag}.whl.
        """
        m = self.WHEEL_RE.match(wheel)
        if m:
            self.arch = m.group('arch')
            self.name = m.group('name')
            self.version = m.group('version')
            self.build = m.group('build') or ""
            self.python = m.group('python')
            self.abi = m.group('abi')
            self.platform = m.group('platform')
        else:
            raise Exception(f"Could not get tags for : {wheel}")

    def loose_version(self):
        return version.parse(self.version)

    def __str__(self):
        return self.filename

    def __eq__(self, other):
        return isinstance(other, Wheel) and self.__dict__ == other.__dict__


def is_compatible(wheel, pythons):
    """
    Verify that the wheel python version is compatible with currently supported python versions.
    """
    for p in pythons or []:
        if wheel.python in COMPATIBLE_PYTHON[p]:
            return True
    return False


def match_file(file, rexes):
    """ Match file with one or more regular expressions. """
    for rex in rexes:
        if re.match(rex, file):
            return True
    return False


def get_rexes(names_versions):
    """
    Returns the patterns to match file names (case insensitive).
    Supports exact matching and globbing of name.
    Supports exact matching and globbing of version.
    pattern: name-version*.whl
    """
    return [re.compile(fnmatch.translate(f"{name}-{version}[-+]*.whl"), re.IGNORECASE) for name, version in names_versions]


def get_wheels(path, archs, names_versions, pythons, latest=True):
    """
    Glob the full list of wheels in the wheelhouse on CVMFS.
    Can also be filterd on arch, name, version or python.
    Return a dict of wheel name and list of tags.
    """
    wheels = {}
    rexes = get_rexes(names_versions)

    for arch in archs:
        for _, _, files in os.walk(f"{path}/{arch}"):
            for file in files:
                if match_file(file, rexes):
                    wheel = Wheel(f"{arch}/{file}")
                    if is_compatible(wheel, pythons):
                        if wheel.name in wheels:
                            wheels[wheel.name].append(wheel)
                        else:
                            wheels[wheel.name] = [wheel]

    # Filter versions
    return latest_versions(wheels) if latest else wheels


def latest_versions(wheels):
    """
    Returns only the latest version of each wheel.
    """
    latests = {}

    for wheel_name, wheel_list in wheels.items():
        wheel_list.sort(key=operator.methodcaller('loose_version'), reverse=True)
        latests[wheel_name] = []
        latest = wheel_list[0].loose_version()

        for wheel in wheel_list:
            if latest == wheel.loose_version():
                latests[wheel_name].append(wheel)
            else:
                break

    return latests


def sort(wheels, columns, condense=False):
    """
    Transforms dict of wheels to a list of lists
    where the columns are the wheel tags.
    """

    def loose_key(x):
        """
        Everything and nothing can be a version, loosely!
        """
        return version.parse(x)

    ret = []
    sep = ", "

    # Sort in-place, by name insensitively asc, then by version desc, then by arch desc, then by python desc
    # Since the sort is stable and Timsort can benefit from previous sort, this is fast.
    wheel_names = sorted(wheels.keys(), key=lambda s: s.casefold())
    for wheel_name in wheel_names:
        wheel_list = wheels[wheel_name]
        wheel_list.sort(key=operator.attrgetter('python'), reverse=True)
        wheel_list.sort(key=operator.attrgetter('arch'), reverse=True)
        wheel_list.sort(key=operator.methodcaller('loose_version'), reverse=True)

        # Condense wheel information on one line.
        # For every column, every wheel, insert the tag into a uniq set, then join tag values and re-sort.
        # Otherwise, get the columns.
        if condense:
            row = []
            dwheel = {}
            for column in columns:
                dwheel[column] = set()

                for wheel in wheel_list:
                    dwheel[column].add(getattr(wheel, column))

                row.append(sep.join(sorted(dwheel.get(column), key=loose_key, reverse=True)))

            ret.append(row)
        else:
            ret.extend([[getattr(wheel, column) for column in columns] for wheel in wheel_list])

    return ret


def add_not_available_wheels(wheels, wheel_names):
    """ Add the wheels names given from the user that were not found. """
    for wheel in wheel_names:
        # Do not duplicate and add names that translate to an already present name.
        if wheel not in wheels and all(not re.match(fnmatch.translate(wheel), w) for w in wheels.keys()):
            wheels[wheel] = [Wheel(filename=wheel, name=wheel, parse=False)]

    return wheels


def normalize_names(wheel_names):
    """
    Normalize wheel names. Replaces `-` for `_`.
    Pip support names with dashes, but wheel convert them to underscores.
    """
    return [name.replace('-', '_') for name in wheel_names]


def create_argparser():
    """
    Returns an arguments parser for `avail_wheels` command.
    Note : sys.argv is not parsed yet, must call `.parse_args()`.
    """

    class HelpFormatter(argparse.RawDescriptionHelpFormatter, argparse.ArgumentDefaultsHelpFormatter):
        """ Dummy class for RawDescription and ArgumentDefault formatter """

    description = "List currently available wheels patterns from the wheelhouse. By default, it will:"
    description += "\n    - only show you the latest version of a specific package (unless versions are given);"
    description += "\n    - only show you versions that are compatible with the python module (if one loaded), otherwise all python versions will be shown;"
    description += "\n    - only show you versions that are compatible with the CPU architecture that you are currently running on."

    epilog = "Examples:\n"
    epilog += "    avail_wheels \"*cdf*\"\n"
    epilog += "    avail_wheels numpy --version \"1.15*\"\n"
    epilog += "    avail_wheels numpy --all_versions\n"
    epilog += "    avail_wheels numpy torch_cpu --version \"1.15*\" 0.4.0\n"
    epilog += "    avail_wheels numpy --python 2.7 3.6\n"
    epilog += "\nFor more information, see: https://docs.computecanada.ca/wiki/Python#Listing_available_wheels"

    parser = argparse.ArgumentParser(prog="avail_wheels",
                                     formatter_class=HelpFormatter,
                                     description=description,
                                     epilog=epilog)

    parser.add_argument("wheel", nargs="*", default=DEFAULT_STAR_ARG, help="Specify the name to look for (case insensitive).")
    parser.add_argument("-n", "--name", nargs="+", default=None, help="Specify the name to look for (case insensitive).")

    version_group = parser.add_argument_group('version')
    parser.add_mutually_exclusive_group()._group_actions.extend([
        version_group.add_argument("-v", "--version", nargs="+", default=DEFAULT_STAR_ARG, help="Specify the version to look for."),
        version_group.add_argument("--all_versions", action='store_true', help="Show all versions of each wheel."),
    ])

    python_group = parser.add_argument_group('python')
    parser.add_mutually_exclusive_group()._group_actions.extend([
        python_group.add_argument("-p", "--python", choices=AVAILABLE_PYTHONS, nargs='+', default=[CURRENT_PYTHON[:3]] if CURRENT_PYTHON else AVAILABLE_PYTHONS, help="Specify the python versions to look for."),
        python_group.add_argument("--all_pythons", action='store_true', help="Show all pythons of each wheel."),
    ])

    arch_group = parser.add_argument_group('architecture')
    parser.add_mutually_exclusive_group()._group_actions.extend([
        arch_group.add_argument("-a", "--arch", choices=AVAILABLE_ARCHITECTURES, nargs='+', default=ARCHITECTURES, help="Specify the architecture to look for."),
        arch_group.add_argument("--all_archs", action='store_true', help="Show all architectures of each wheel.")
    ])

    display_group = parser.add_argument_group('display')
    display_group.add_argument("--mediawiki", action='store_true', help="Print a mediawiki table."),
    display_group.add_argument("--raw", action='store_true', help="Print raw files names. Has precedence over other arguments of this group."),
    display_group.add_argument("--column", choices=AVAILABLE_HEADERS, nargs='+', default=HEADERS, help="Specify and order the columns to display."),
    display_group.add_argument("--condense", action='store_true', help="Condense wheel information into one line.")
    display_group.add_argument("--not-available", action='store_true', help="Also display wheels that were not available.")

    return parser


def main():
    args = create_argparser().parse_args()

    # Add name values to the positionnal wheel argument
    if args.name and args.wheel == DEFAULT_STAR_ARG:
        args.wheel = args.name
    elif args.name:
        args.wheel.extend(args.name)

    # Pip support names with `-`, but wheel convert `-` to `_`.
    args.wheel = normalize_names(args.wheel)

    pythons = args.python if not args.all_pythons else AVAILABLE_PYTHONS
    archs = args.arch if not args.all_archs else AVAILABLE_ARCHITECTURES
    names_versions = product(args.wheel, args.version)
    latest = not args.all_versions and args.version == DEFAULT_STAR_ARG

    wheels = get_wheels(WHEELHOUSE, archs=archs, names_versions=names_versions, pythons=pythons, latest=latest)

    if args.not_available:
        wheels = add_not_available_wheels(wheels, args.wheel)

    # Handle SIGPIP emitted by piping to utils like head.
    # https://docs.python.org/3/library/signal.html#note-on-sigpipe
    try:
        if args.raw:
            for wheel_list in wheels.values():
                print(*wheel_list, sep='\n')
        else:
            wheels = sort(wheels, args.column, args.condense)
            print(tabulate(wheels, headers=args.column, tablefmt="mediawiki" if args.mediawiki else "simple"))
    except BrokenPipeError:
        # Python flushes standard streams on exit; redirect remaining output
        # to devnull to avoid another BrokenPipeError at shutdown
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        sys.exit(1)  # Python exits with error code 1 on EPIPE


if __name__ == "__main__":
    main()
