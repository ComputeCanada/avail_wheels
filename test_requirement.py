import pytest
import wild_requirements as requirements


@pytest.mark.parametrize("req", [
    "numpy",
    "NumPy",
    "numpy==1",
    "numpy==1.0",
    "numpy==1.0.0",
    "numpy===1.0.0",
    "numpy<1.0.0",
    "numpy<=1.0.0",
    "numpy>1.0.0",
    "numpy>=1.0.0",
    "numpy~=1.0.0",
    "numpy==1.0.*",
    "numpy==1.*",
    "numpy==*",
])
def test_grammar_valid_requirement(req):
    """
    Test valid requirement against the grammar.
    """
    requirements.REQUIREMENT.parse_string(req)


@pytest.mark.parametrize("req", [
    "numpy*",
    "*numpy*",
    "numpy*==1.0",
    "*numpy*==1.0.0",
    "*numpy*==1.0.*",
    "numpy_*",
    "numpy-*",
    "*numpy-*",
    "*numpy*-*",
])
def test_grammar_wild_requirement(req):
    """
    Test valid wild (*) requirement against the grammar.
    """
    requirements.REQUIREMENT.parse_string(req)


@pytest.mark.parametrize("req", [
    "nu!mpy",
    "*num*py*",
    "(numpy)",
    "[numpy]",
    "*numpy*cli-*",
])
def test_grammar_invalid_requirement(req):
    """
    Test invalid requirement against the grammar.
    """
    with pytest.raises(Exception):
        requirements.REQUIREMENT.parse_string(req)


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
