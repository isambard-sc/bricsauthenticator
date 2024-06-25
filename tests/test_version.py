import re

from mappingauthenticator import __version__, __version_tuple__


def test_version() -> None:
    """
    Check version dunder module variables are present and consistent

    .. note:: Only checks the major.minor.patch component of the version
    """
    # Check that version number starts with major.minor.patch number (and optional v prefix)
    match = re.fullmatch(r"^v?(?P<major>\d+)\.(?P<minor>\d)+\.(?P<patch>\d+).*$", __version__)

    assert match, "__version__ should start with a valid dotted version number"

    version_tuple_from_str = (int(match.group("major")), int(match.group("minor")), int(match.group("patch")))

    assert (
        version_tuple_from_str == __version_tuple__[0:3]
    ), "__version__ and __version_tuple__ should have consistent dotted version numbers"
