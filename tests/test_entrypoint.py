from importlib.metadata import entry_points

from bricsauthenticator import BricsAuthenticator


def test_entrypoint() -> None:
    """
    Check that BricsAuthenticator is exposed via the jupyterhub.authenticators entry point group
    """

    authenticator_entry_points = entry_points(group="jupyterhub.authenticators")

    assert "brics" in authenticator_entry_points.names, 'entry point named "brics" should be exposed'

    brics_entry_point = authenticator_entry_points["brics"]

    assert (
        brics_entry_point.value == "bricsauthenticator:BricsAuthenticator"
    ), '"brics" entry point should have expected value'

    brics_authenticator = brics_entry_point.load()

    assert (
        brics_authenticator is BricsAuthenticator
    ), "calling load() on entry point should load BricsAuthenticator class"
