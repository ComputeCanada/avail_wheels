import pytest
import wild_requirements as requirements

VERSIONS = [
    "",  # Tests unversioned requirements
    "==1",
    "==1.0",
    "==1.0.0",
    "===1.0.0",
    "<1.0.0",
    "<=1.0.0",
    ">1.0.0",
    ">=1.0.0",
    "~=1.0.0",
    "==1.0.*",
    "==1.*",
    "==*",
    ">=1.26,<3",        # Version range with upper/lower bounds
    ">=1.26, !=2.0.0",  # Version range with exclusion and spacing
]

VALID_NAMES = [
    "numpy",
    "NumPy",
    "climlab_cam3_radiation",
]

WILDCARD_NAMES = [
    "numpy*",
    "*numpy*",
    "numpy_*",
    "numpy-*",
    "*numpy-*",
    "*numpy*-*",
    "climlab_cam3_*",
    "climlab_cam3*",
    "climlab_*_*",
    "*_*_*",
    "climlab*",
    "climlab-*",
    "climlab*_cam3*",
    "*_cam3_*",
    "*cam3*",
    "*_cam3_radiation",
    "*_*_radiation",
    "*_*radiation",
    "*radiation",
    "*-gpu",
]

INVALID_NAMES = [
    "nu!mpy",
    "(numpy)",
    "[numpy]",
    "*",                  # Pure wildcard rejected by `.addCondition()`
    "pennylane-*-",       # Trailing punctuation
    "-*gpu",              # Leading punctuation
    "climlab--radiation", # Consecutive punctuation
    "--",                 # Pure punctuation / leading punctuation
]


@pytest.mark.parametrize("version", VERSIONS)
@pytest.mark.parametrize("name", VALID_NAMES + WILDCARD_NAMES)
def test_grammar_valid_requirement(name, version):
    """Test valid names and wildcard names with all version combinations."""
    req_str = f"{name}{version}"
    requirements.REQUIREMENT.parseString(req_str)


@pytest.mark.parametrize("version", VERSIONS)
@pytest.mark.parametrize("name", INVALID_NAMES)
def test_grammar_invalid_requirement(name, version):
    """Test invalid names fail across all version combinations."""
    req_str = f"{name}{version}"
    with pytest.raises(Exception):
        requirements.REQUIREMENT.parseString(req_str)


def test_requirement_class():
    """
    Test the Requirement class.

    The Requirement class should parse the requirement string and store its parts.
    The name should be normalized to lowercase. And `-` should be replaced with `_`.
    """
    req = requirements.Requirement("NumPy==1.0.0")
    assert req.name == "numpy"
    assert req.specifier == "==1.0.0"
    assert req.extras == set()
    assert req.url is None
    assert req.marker is None
    assert str(req) == "numpy==1.0.0"
    assert repr(req) == "<Requirement('numpy==1.0.0')>"

    req = requirements.Requirement("SpaCy-metrics!=1.0.0")
    assert req.name == "spacy_metrics"
    assert req.specifier == "!=1.0.0"
    assert req.extras == set()
    assert req.url is None
    assert req.marker is None
    assert str(req) == "spacy_metrics!=1.0.0"
    assert repr(req) == "<Requirement('spacy_metrics!=1.0.0')>"


def test_requirement_eq():
    """
    Test that the requirement compare to each other.
    """
    assert requirements.Requirement("SpaCy-metrics!=1.0.0") == requirements.Requirement("SpaCy-metrics!=1.0.0")
    assert requirements.Requirement("SpaCy-metrics!=1.0.0") != requirements.Requirement("SpaCy-metrics!=1.1.0")
