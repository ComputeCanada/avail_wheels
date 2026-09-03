#!/cvmfs/soft.computecanada.ca/custom/python/envs/avail_wheels/bin/python3

import os
import sys
import re
import argparse
import fnmatch
import operator
import warnings
import configparser
from tabulate import tabulate, tabulate_formats
import packaging
import wild_requirements as requirements
from runtime_env import RuntimeEnvironment
from collections import defaultdict
from itertools import chain
from functools import cached_property, lru_cache


__version__ = "3.0.0.dev"

env = RuntimeEnvironment()

AVAILABLE_HEADERS = ['name', 'version', 'localversion', 'build', 'python', 'abi', 'platform', 'arch']
HEADERS = ['name', 'version', 'python', 'arch']

DEFAULT_STAR_ARG = ['*']


def __warning_on_one_line(message, category, filename=None, lineno=None, file=None, line=None):
    return f'{category.__name__}: {message}\n'


warnings.formatwarning = __warning_on_one_line


# The wheel filename is {distribution}-{version}([-+]{build tag})?-{python tag}-{abi tag}-{platform tag}.whl.
# The version can be numeric, alpha or alphanum or a combinaison.
WHEEL_RE = re.compile(r"(?P<name>.+?)-(?P<version>.+?)(-(?P<build>\d[^-]*))?-(?P<tags>.+?-.+?-.+?)\.whl")


# Cache parsing tags. Only few (~52) occurences of tags exists accross the wheelhouse.
# ie CacheInfo(hits=18482, misses=52, maxsize=200, currsize=52)
@lru_cache(maxsize=200)
def _parse_tag_cached(tag):
    return packaging.tags.parse_tag(tag)


class Wheel():
    """
    The representation of a wheel and its tags.

    A wheel components are: name, version, build, tags(interpreter, abi, platform)
    This class also stores the filename and arch (parent folder)

    Examples
    --------
    >>> Wheel(filename='numpy-1.20.1-cp38-cp38-linux_x86_64.whl')
    Wheel(filename='numpy-1.20.1-cp38-cp38-linux_x86_64.whl', arch="", name="", version="", build="", tags=None)

    >>> Wheel.parse_wheel_filename(filename='numpy-1.20.1-cp38-cp38-linux_x86_64.whl')
    Wheel(filename='numpy-1.20.1-cp38-cp38-linux_x86_64.whl', arch="", name='numpy', version=<Version('1.20.1')>, build=(), tags=frozenset({<cp38-cp38-linux_x86_64 @ 140549067913536>}))
    """

    def __init__(self, filename="", arch="", name="", version="", build="", tags=frozenset()):
        self._filename = filename
        self._arch = arch
        self._name = name
        self._version = version
        self._build = build
        self._tags = tags

    @staticmethod
    def parse_wheel_filename(filename, arch=""):
        """
        Parse a wheel file into arch, name, version, build, tags(interpreter, abi, platform).
        A wheel file must end with `.whl` and have 4 or 5 components separated with dashes.

        The format is: {name}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl

        Returns
        -------
        Wheel
            Parsed wheel
        """
        m = WHEEL_RE.match(filename)
        if m:
            name, version, _, build, tags = m.groups()
            return Wheel(
                filename=filename,
                arch=arch,
                name=name,
                version=version,
                build=build or "",  # Build is optional
                tags=_parse_tag_cached(tags),
            )
        else:
            warnings.warn(f"Could not get tags for : {filename}")
            return Wheel(filename=filename, arch=arch)

    @cached_property
    def loose_version(self):
        return packaging.version.parse(self._version)

    @property
    def filename(self):
        return self._filename

    @property
    def arch(self):
        return self._arch

    @property
    def name(self):
        return self._name

    @cached_property
    def namelower(self):
        return self._name.lower()

    @property
    def version(self):
        return self.loose_version.public

    @property
    def localversion(self):
        return self.loose_version.local

    @property
    def build(self):
        return self._build

    @property
    def tags(self):
        return self._tags

    @cached_property
    def python(self):
        return ",".join(sorted(set(tag.interpreter for tag in self._tags)))

    @cached_property
    def abi(self):
        return ",".join(sorted(set(tag.abi for tag in self._tags)))

    @cached_property
    def platform(self):
        return ",".join(sorted(set(tag.platform for tag in self._tags)))

    def __str__(self):
        return self._filename

    def __repr__(self):
        return "Wheel({})".format(", ".join(f"{k[1:]}={v!r}" for k, v in self.__dict__.items()))

    def __eq__(self, other):
        if not isinstance(other, Wheel):
            return NotImplemented

        return (
            self._filename == other._filename
            and self._arch == other._arch
            and self._name == other._name
            and self._version == other._version
            and self._build == other._build
            and self._tags == other._tags
        )


def is_compatible(wheel, pythons):
    """
    Verify that the wheel tags are compatible with currently supported tags.
    """
    return any(not wheel.tags.isdisjoint(env.compatible_tags[p]) for p in pythons)


def match_file(file, rexes):
    """ Match file with one or more regular expressions. """
    for rex in rexes:
        if rex.match(file):
            return True
    return False


def match_version(wheel, reqs):
    """
    Match an exact requirements or a wild requirements.
    When a requirements has no specifiers, it automatically match.
    """
    if wheel.namelower in reqs:
        return wheel.version in reqs[wheel.namelower].specifier
    else:
        return any(re.match(fnmatch.translate(req_name), wheel.namelower, re.IGNORECASE) and wheel.version in req.specifier for req_name, req in reqs.items())


def get_rexes(reqs):
    """
    Returns the patterns to match file names (case insensitive).
    Supports exact matching and globbing of name.
    pattern: name-*.whl
    """
    return [re.compile(fnmatch.translate(f"{req}-*.whl"), re.IGNORECASE) for req in reqs]


def get_wheels(paths, reqs, pythons, latest):
    """
    Glob the full list of wheels in the wheelhouse on CVMFS.
    Can also be filterd on arch, name, version or python.
    Return a dict of wheel name and list of tags.
    """
    def _get_wheels_from_fs(paths):
        """
        Get wheels from the wheelhouse paths.
        """
        for path in paths:
            arch = os.path.basename(path)
            for entry in os.scandir(path):
                if entry.name.endswith('.whl'):
                    yield arch, entry.name

    wheels = defaultdict(list)

    if reqs:
        rexes = get_rexes(reqs)
        for arch, file in _get_wheels_from_fs(paths):
            if match_file(file, rexes):
                wheel = Wheel.parse_wheel_filename(file, arch)
                if is_compatible(wheel, pythons) and match_version(wheel, reqs):
                    wheels[wheel.namelower].append(wheel)

    # Display all available wheels that are compatible (no reqs were given)
    else:
        for arch, file in _get_wheels_from_fs(paths):
            wheel = Wheel.parse_wheel_filename(file, arch)
            if is_compatible(wheel, pythons):
                wheels[wheel.namelower].append(wheel)

    # Filter versions
    return latest_versions(wheels) if latest else wheels


def latest_versions(wheels):
    """
    Returns only the latest version of each wheel.
    """
    latests = {}

    for wheel_name, wheel_list in wheels.items():
        latest = max(w.version for w in wheel_list)
        latests[wheel_name] = [w for w in wheel_list if w.version == latest]

    return latests


def remove_duplicates(seq):
    """
    Remove duplicate items from a sequence while preserving order.
    """
    seen = set()
    ret = []

    for item in seq:
        key = tuple(item) if isinstance(item, list) else item
        if key not in seen:
            seen.add(key)
            ret.append(item)

    return ret


def sort(wheels, columns, condense=False):
    """
    Transforms dict of wheels to a list of lists
    where the columns are the wheel tags.
    """

    def loose_key(x):
        """
        Everything and nothing can be a version, loosely!
        """
        return packaging.version.parse(x)

    ret = []
    sep = ", "

    # Sort in-place, by name insensitively asc, then by version desc, then by arch desc, then by python desc
    # Since the sort is stable and Timsort can benefit from previous sort, this is fast.
    wheel_names = sorted(wheels.keys(), key=lambda s: s.casefold())
    for wheel_name in wheel_names:
        wheel_list = wheels[wheel_name]
        wheel_list.sort(key=lambda x: loose_key(x.python), reverse=True)
        wheel_list.sort(key=operator.attrgetter('arch'), reverse=True)
        wheel_list.sort(key=operator.attrgetter('loose_version'), reverse=True)

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

    return remove_duplicates(ret)


def add_not_available_wheels(wheels, reqs, not_available_only=False):
    """ Add the wheels names given from the user that were not found. """

    # Return the wheel set, or an empty set where wheels not available were added.
    ret = defaultdict(list) if not_available_only else wheels

    for wheel in reqs:
        # Do not duplicate and add names that translate to an already present name.
        if wheel not in wheels and all(not re.match(fnmatch.translate(wheel), w) for w in wheels.keys()):
            ret[wheel].append(Wheel(filename=wheel, name=wheel))

    return ret


def filter_search_paths(search_paths, arch_values):
    """
    Filter paths that ends with specific values.
    """
    if not arch_values:
        return search_paths

    return [
        path
        for path in search_paths
        if any(path.endswith(arch_value) for arch_value in arch_values)
    ]


def get_search_paths():
    """
    Gets the search paths from the $PIP_CONFIG_FILE or start at root of the wheelhouse.
    """
    if not env.pip_config_file:
        return [
            level2.path
            for level1 in os.scandir(env.wheelhouse) if level1.is_dir()
            for level2 in os.scandir(level1.path) if level2.is_dir()
        ]

    cfg = configparser.ConfigParser()
    with open(env.pip_config_file) as f:
        cfg.read_file(f)
    return cfg['wheel']['find-links'].split()


def get_requirements_set(args):
    """
    Get a unique set of requirements from the arguments.

    Requirements comes from:
        - positional `wheels`
        - name
        - requirements files

    Returns
    -------
    dict
        Requirements set
    """
    # Simulate a set, with associated requirement

    reqs = defaultdict(requirements.Requirement)

    # And add requirements from requirements files.
    if args.requirements:
        # Include here, as importing is slow!
        from pip._internal.req import req_file
        from pip._internal.network.session import PipSession
        import tomllib

        session = PipSession()
        for fname in args.requirements:
            # Read dependencies section from local pyproject.toml
            if os.path.basename(fname) == "pyproject.toml":
                with open(fname, 'rb') as f:
                    pyproject = tomllib.load(f)

                    # https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#dependencies-and-requirements
                    for freq in pyproject['project'].get('dependencies', []):
                        r = make_requirement(freq)
                        reqs[r.name] = r
            else:
                # assume requirements.txt file
                for freq in req_file.parse_requirements(fname, session=session):
                    r = make_requirement(freq.requirement)
                    reqs[r.name] = r

    # Then add requirements from the command line so they are prioritize.
    for req in chain(args.wheel, args.name):
        if args.specifier:
            reqs[req.name] = requirements.Requirement(f"{req.name}{args.specifier}")
        else:
            reqs[req.name] = req

    return reqs or None


def make_eq_specifier(v):
    """
    """
    try:
        return packaging.specifiers.SpecifierSet(f"=={v}")
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid version: {v!r}.")


def make_requirement(r):
    """
    """
    try:
        # Partition requirement on '+'.
        # This is useful for requirements like jaxlib==0.4.20+cuda12.cudnn89.computecanada which contains name, version and local version.
        # We want to keep the name and version part (jaxlib==0.4.20) and drop the local version (+).

        # When `+` is not found, it returns the whole string.
        return requirements.Requirement(r.partition('+')[0])
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid requirement: {r!r}.")


def create_argparser():
    """
    Returns an arguments parser for `avail_wheels` command.
    Note : sys.argv is not parsed yet, must call `.parse_args()`.
    """

    class HelpFormatter(argparse.RawDescriptionHelpFormatter, argparse.ArgumentDefaultsHelpFormatter):
        """ Dummy class for RawDescription and ArgumentDefault formatter """

    description = "List currently available wheels patterns from the wheelhouse. By default, it will:"
    description += "\n    - only show you the latest version of a specific package (unless versions are given);"
    description += "\n    - only show you versions that are compatible with the python module (if one loaded) or virtual environment (if activated), otherwise all python versions will be shown;"
    description += "\n    - only show you versions that are compatible with the CPU architecture and software environment (StdEnv) that you are currently running on."

    epilog = "Examples:\n"
    epilog += "\n".join([
        "    avail_wheels \"*cdf*\"",
        "    avail_wheels numpy -v \"1.21.*\"",
        "    avail_wheels numpy --all_versions",
        "    avail_wheels.py numpy==1.21",
        "    avail_wheels.py numpy>=1.21.*",
        "    avail_wheels numpy --python 3.8 3.10",
        "    avail_wheels -r requirements.txt",
        "    avail_wheels 'dgl-cpu<0.6.0' -r requirements.txt",
    ])
    epilog += "\nFor more information, see: https://docs.computecanada.ca/wiki/Python#Listing_available_wheels"

    parser = argparse.ArgumentParser(prog="avail_wheels",
                                     formatter_class=HelpFormatter,
                                     description=description,
                                     epilog=epilog)

    parser.add_argument("-V", action='version', version='%(prog)s {}'.format(__version__))
    parser.add_argument("wheel", nargs="*", type=make_requirement, help="Specify the name to look for (case insensitive).")
    parser.add_argument("-n", "--name", nargs="+", type=make_requirement, default=[], help="Specify the name to look for (case insensitive).")
    parser.add_argument("--all", action='store_true', help="Same as: --all_versions --all_pythons --all_archs")
    parser.add_argument("-r", "--requirement", dest="requirements", nargs="+", default=[], metavar="file", help="Install from the given requirements file. This option can be used multiple times.")

    version_group = parser.add_argument_group('version')
    parser.add_mutually_exclusive_group()._group_actions.extend([
        version_group.add_argument("-v", "--version", dest="specifier", metavar="version", type=make_eq_specifier, help="Specify the version to look for."),
        version_group.add_argument("--all_versions", action='store_true', help="Show all versions of each wheel."),
        version_group.add_argument("--all-versions", action='store_true', dest="all_versions"),
    ])

    python_group = parser.add_argument_group('python')
    parser.add_mutually_exclusive_group()._group_actions.extend([
        python_group.add_argument("-p", "--python", choices=env.available_pythons, nargs='+', default=[env.current_python] if env.current_python else env.available_pythons, help="Specify the python versions to look for."),
        python_group.add_argument("--all_pythons", action='store_true', help="Show all pythons of each wheel."),
        python_group.add_argument("--all-pythons", action='store_true', dest="all_pythons"),
    ])

    arch_group = parser.add_argument_group('architecture')
    parser.add_mutually_exclusive_group()._group_actions.extend([
        arch_group.add_argument("-a", "--arch", choices=env.available_architectures, nargs='+', help=f"Specify the architecture to look for from the paths configured in {env.pip_config_file}."),
        arch_group.add_argument("--all_archs", action='store_true', help=f"Show all architectures of each wheel from the paths configured in {env.pip_config_file}."),
        arch_group.add_argument("--all-archs", action='store_true', dest="all_archs")
    ])

    display_group = parser.add_argument_group('display')
    display_group.add_argument("--mediawiki", action='store_true', help="Print a mediawiki table."),
    display_group.add_argument("--format", choices=tabulate_formats, default='simple', help="Print table according to given format."),
    display_group.add_argument("--raw", action='store_true', help="Print raw files names. Has precedence over other arguments of this group."),
    display_group.add_argument("--column", choices=AVAILABLE_HEADERS, nargs='+', default=HEADERS, help="Specify and order the columns to display."),
    display_group.add_argument("--condense", action='store_true', help="Condense wheel information into one line.")
    display_group.add_argument("--not-available", action='store_true', help="Also display wheels that were not available.")
    display_group.add_argument("--not-available-only", action='store_true', help="Display only wheels that were not available.")

    return parser


def main():
    args = create_argparser().parse_args()

    if args.all:
        args.all_archs, args.all_versions, args.all_pythons = True, True, True

        # If all is set, then warn that we are ignoring --arch, --version and --python
        if args.arch or args.specifier or args.python:
            warnings.warn("Ignoring --arch, --version and --python since --all is set.")

    reqs = get_requirements_set(args)

    # Specifying `all_arch` set `--arch` to None, hence returns all search paths from PIP_CONFIG_FILE
    search_paths = filter_search_paths(get_search_paths(), args.arch)
    pythons = args.python if not args.all_pythons else env.available_pythons
    latest = not args.all_versions and args.specifier is None

    wheels = get_wheels(search_paths, reqs, pythons, latest)

    if args.not_available or args.not_available_only:
        wheels = add_not_available_wheels(wheels, reqs, args.not_available_only)

    # Handle SIGPIP emitted by piping to utils like head.
    # https://docs.python.org/3/library/signal.html#note-on-sigpipe
    try:
        if args.raw:
            for wheel_list in wheels.values():
                print(*wheel_list, sep='\n')
        else:
            wheels = sort(wheels, args.column, args.condense)
            print(tabulate(wheels, headers=args.column, tablefmt="mediawiki" if args.mediawiki else args.format))
    except BrokenPipeError:
        # Python flushes standard streams on exit; redirect remaining output
        # to devnull to avoid another BrokenPipeError at shutdown
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        sys.exit(1)  # Python exits with error code 1 on EPIPE


if __name__ == "__main__":
    main()
