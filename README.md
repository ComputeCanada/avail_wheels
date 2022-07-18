# avail_wheels
`avail_wheels` is a Python script to list available wheels from the wheelhouse.
By default, it will:
-   only show you the  **latest version**  of a specific package (unless versions are given);
-   only show you versions that are compatible with the python module (if one loaded) or virtual environment (if activated), otherwise all python versions will be shown;
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
usage: avail_wheels [-h] [-V] [-n NAME [NAME ...]] [--all] [-r file [file ...]] [-v version | --all_versions | --all-versions] [-p {2.7,3.5,3.6,3.7,3.8,3.9,3.10} [{2.7,3.5,3.6,3.7,3.8,3.9,3.10} ...] | --all_pythons
                    | --all-pythons] [-a {avx,avx512,avx2,generic,sse3} [{avx,avx512,avx2,generic,sse3} ...] | --all_archs | --all-archs] [--mediawiki]
                    [--format {fancy_grid,fancy_outline,github,grid,html,jira,latex,latex_booktabs,latex_longtable,latex_raw,mediawiki,moinmoin,orgtbl,pipe,plain,presto,pretty,psql,rst,simple,textile,tsv,unsafehtml,youtrack}]
                    [--raw] [--column {name,version,localversion,build,python,abi,platform,arch} [{name,version,localversion,build,python,abi,platform,arch} ...]] [--condense] [--not-available]
                    [--not-available-only]
                    [wheel ...]

List currently available wheels patterns from the wheelhouse. By default, it will:
    - only show you the latest version of a specific package (unless versions are given);
    - only show you versions that are compatible with the python module (if one loaded) or virtual environment (if activated), otherwise all python versions will be shown;
    - only show you versions that are compatible with the CPU architecture that you are currently running on.

positional arguments:
  wheel                 Specify the name to look for (case insensitive). (default: None)

optional arguments:
  -h, --help            show this help message and exit
  -V                    show program's version number and exit
  -n NAME [NAME ...], --name NAME [NAME ...]
                        Specify the name to look for (case insensitive). (default: [])
  --all                 Same as: --all_versions --all_pythons --all_archs (default: False)
  -r file [file ...], --requirement file [file ...]
                        Install from the given requirements file. This option can be used multiple times. (default: [])

version:
  -v version, --version version
                        Specify the version to look for. (default: None)
  --all_versions        Show all versions of each wheel. (default: False)
  --all-versions

python:
  -p {2.7,3.5,3.6,3.7,3.8,3.9,3.10} [{2.7,3.5,3.6,3.7,3.8,3.9,3.10} ...], --python {2.7,3.5,3.6,3.7,3.8,3.9,3.10} [{2.7,3.5,3.6,3.7,3.8,3.9,3.10} ...]
                        Specify the python versions to look for. (default: ['3.9'])
  --all_pythons         Show all pythons of each wheel. (default: False)
  --all-pythons

architecture:
  -a {avx,avx512,avx2,generic,sse3} [{avx,avx512,avx2,generic,sse3} ...], --arch {avx,avx512,avx2,generic,sse3} [{avx,avx512,avx2,generic,sse3} ...]
                        Specify the architecture to look for from the paths configured in None. (default: None)
  --all_archs           Show all architectures of each wheel from the paths configured in None. (default: False)
  --all-archs

display:
  --mediawiki           Print a mediawiki table. (default: False)
  --format {fancy_grid,fancy_outline,github,grid,html,jira,latex,latex_booktabs,latex_longtable,latex_raw,mediawiki,moinmoin,orgtbl,pipe,plain,presto,pretty,psql,rst,simple,textile,tsv,unsafehtml,youtrack}
                        Print table according to given format. (default: simple)
  --raw                 Print raw files names. Has precedence over other arguments of this group. (default: False)
  --column {name,version,localversion,build,python,abi,platform,arch} [{name,version,localversion,build,python,abi,platform,arch} ...]
                        Specify and order the columns to display. (default: ['name', 'version', 'build', 'python', 'arch'])
  --condense            Condense wheel information into one line. (default: False)
  --not-available       Also display wheels that were not available. (default: False)
  --not-available-only  Display only wheels that were not available. (default: False)

Examples:
    avail_wheels "*cdf*"
    avail_wheels numpy -v "1.21.*"
    avail_wheels numpy --all_versions
    avail_wheels.py numpy==1.21
    avail_wheels.py numpy>=1.21.*
    avail_wheels numpy --python 3.8 3.10
    avail_wheels -r requirements.txt
    avail_wheels 'dgl-cpu<0.6.0' -r requirements.txt
For more information, see: https://docs.computecanada.ca/wiki/Python#Listing_available_wheels
```

### Examples
#### Names
To list wheels containing `cdf` (case insensitive) in its name:
```bash
avail_wheels "*cdf*"
name      version    python    arch
--------  ---------  --------  -------
h5netcdf  0.7.4      py2,py3   generic
netCDF4   1.5.8      cp39      avx2
netCDF4   1.5.8      cp38      avx2
netCDF4   1.5.8      cp310     avx2
```
Or an exact name:
```bash
avail_wheels numpy
name    version    python    arch
------  ---------  --------  -------
numpy   1.23.0     cp39      generic
numpy   1.23.0     cp38      generic
numpy   1.23.0     cp310     generic
```

#### Version
To list a specific version, one can use the same format as with `pip`:
```bash
$ avail_wheels numpy==1.23
name    version    python    arch
------  ---------  --------  -------
numpy   1.23.0     cp39      generic
numpy   1.23.0     cp38      generic
numpy   1.23.0     cp310     generic
```
Or use the long option:
```bash
$ avail_wheels numpy --version 1.23
name    version    python    arch
------  ---------  --------  -------
numpy   1.23.0     cp39      generic
numpy   1.23.0     cp38      generic
numpy   1.23.0     cp310     generic
```
With the `pip` format, one can use different operators : `==`, `<`, `>`, `~=`, `<=`,`>=`, `!=`. For instance, to list inferior versions:
```bash
$ avail_wheels 'numpy<1.23'
name    version    python    arch
------  ---------  --------  -------
numpy   1.22.2     cp39      generic
numpy   1.22.2     cp38      generic
numpy   1.22.2     cp310     generic
```
And to list all available versions:
```bash
~ $ avail_wheels "*cdf*" --all-version
name      version    python    arch
--------  ---------  --------  -------
h5netcdf  0.7.4      py2,py3   generic
netCDF4   1.5.8      cp39      avx2
netCDF4   1.5.8      cp38      avx2
netCDF4   1.5.8      cp310     avx2
netCDF4   1.5.6      cp38      avx2
netCDF4   1.5.6      cp37      avx2
netCDF4   1.5.4      cp38      avx2
netCDF4   1.5.4      cp37      avx2
netCDF4   1.5.4      cp36      avx2
```

#### Python
One can list a specific version of Python:
```bash
avail_wheels 'numpy<1.23' --python 3.9
name    version    python    arch
------  ---------  --------  -------
numpy   1.22.2     cp39      generic
```

#### Requirements file
One can list available wheels based on a `requirements.txt` file with:
```bash
$ avail_wheels -r requirements.txt 
name       version    python    arch
---------  ---------  --------  -------
packaging  21.3       py3       generic
tabulate   0.8.10     py3       generic
```
And display wheels that are not available:
```bash
$ avail_wheels -r requirements.txt --not-available
name       version    python    arch
---------  ---------  --------  -------
packaging  21.3       py3       generic
pip
tabulate   0.8.10     py3       generic
```


## Development
Set environment variables to mock the CVMFS.
```bash
export WHEELHOUSE=$PWD/cvmfs/soft.computecanada.ca/custom/python/wheelhouse;
export PYTHONS_DIR=$PWD'/cvmfs/soft.computecanada.ca/easybuild/software/20*/Core/python';
export PIP_CONFIG_FILE=$PWD/pip-avx2.conf;
export RSNT_ARCH=avx2;
```

## Tests
```bash
pytest .
```

## Deployment
```bash
cp avail_wheels.py tests.py requirements.txt /cvmfs/soft.computecanada.ca/custom/python/envs/avail_wheels/
ln -s /cvmfs/soft.computecanada.ca/custom/python/envs/avail_wheels/avail_wheels.py avail_wheels
```
