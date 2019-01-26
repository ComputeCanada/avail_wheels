# avail_wheels
`avail_wheels` is a Python script to list available wheels from the wheelhouse.
By default, it will:
-   only show you the  **latest version**  of a specific package (unless versions are given);
-   only show you versions that are compatible with the python module (if one loaded), otherwise all python versions will be shown;
-   only show you versions that are compatible with the CPU architecture that you are currently running on.

## Installation

### Requirements
* Python 3.7 and up

```
python3.7 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage and Examples
```
usage: avail_wheels [-h] [-n NAME [NAME ...]] [-v VERSION [VERSION ...] |
                    --all_versions]
                    [-p {2.7,3.5,3.6,3.7} [{2.7,3.5,3.6,3.7} ...] |
                    --all_pythons]
                    [-a {avx,avx2,avx512,generic,sse3} [{avx,avx2,avx512,generic,sse3} ...]
                    | --all_archs] [--mediawiki] [--raw]
                    [--column {name,version,build,python,abi,platform,arch} [{name,version,build,python,abi,platform,arch} ...]]
                    [--condense] [--not-available]
                    [wheel [wheel ...]]

List currently available wheels patterns from the wheelhouse. By default, it will:
    - only show you the latest version of a specific package (unless versions are given);
    - only show you versions that are compatible with the python module (if one loaded), otherwise all python versions will be shown;
    - only show you versions that are compatible with the CPU architecture that you are currently running on.

positional arguments:
  wheel                 Specify the name to look for (case insensitive).
                        (default: ['*'])

optional arguments:
  -h, --help            show this help message and exit
  -n NAME [NAME ...], --name NAME [NAME ...]
                        Specify the name to look for (case insensitive).
                        (default: None)

version:
  -v VERSION [VERSION ...], --version VERSION [VERSION ...]
                        Specify the version to look for. (default: ['*'])
  --all_versions        Show all versions of each wheel. (default: False)

python:
  -p {2.7,3.5,3.6,3.7} [{2.7,3.5,3.6,3.7} ...], --python {2.7,3.5,3.6,3.7} [{2.7,3.5,3.6,3.7} ...]
                        Specify the python versions to look for. (default:
                        ['2.7', '3.5', '3.6', '3.7'])
  --all_pythons         Show all pythons of each wheel. (default: False)

architecture:
  -a {avx,avx2,avx512,generic,sse3} [{avx,avx2,avx512,generic,sse3} ...], --arch {avx,avx2,avx512,generic,sse3} [{avx,avx2,avx512,generic,sse3} ...]
                        Specify the architecture to look for. (default:
                        ['generic', None])
  --all_archs           Show all architectures of each wheel. (default: False)

display:
  --mediawiki           Print a mediawiki table. (default: False)
  --raw                 Print raw files names. Has precedence over other
                        arguments of this group. (default: False)
  --column {name,version,build,python,abi,platform,arch} [{name,version,build,python,abi,platform,arch} ...]
                        Specify and order the columns to display. (default:
                        ['name', 'version', 'build', 'python', 'arch'])
  --condense            Condense wheel information into one line. (default:
                        False)
  --not-available       Also display wheels that were not available. (default:
                        False)

Examples:
    avail_wheels "*cdf*"
    avail_wheels numpy --version "1.15*"
    avail_wheels numpy --all_versions
    avail_wheels numpy torch_cpu --version "1.15*" 0.4.0
    avail_wheels numpy --python 2.7 3.6

For more information, see: https://docs.computecanada.ca/wiki/Python#Listing_available_wheels
```

## Development
Set environment variables to mock the wheelhouse.
```bash
export WHEELHOUSE=$(pwd)/cvmfs/soft.computecanada.ca/custom/python/wheelhouse;
export PYTHONS_DIR=$(pwd)/cvmfs/soft.computecanada.ca/easybuild/software/2017/Core/python;
```

## Tests
```bash
python tests.py
```

## Deployment
```bash
cp avail_wheels.py tests.py requirements.txt /cvmfs/soft.computecanada.ca/custom/python/envs/avail_wheels/
ln -s /cvmfs/soft.computecanada.ca/custom/python/envs/avail_wheels/avail_wheels.py avail_wheels
```
