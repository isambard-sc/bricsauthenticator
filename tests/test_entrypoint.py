from importlib.metadata import entry_points
from typing import Any

import pytest

from bricsauthenticator import BricsAuthenticator, BricsSlurmSpawner

@pytest.mark.parametrize(
        "ep_name, ep_value, ep_group, ep_loaded",
        [
            pytest.param("brics", "bricsauthenticator:BricsAuthenticator", "jupyterhub.authenticators", BricsAuthenticator, id="jupyterhub.authenticators"),
            pytest.param("brics", "bricsauthenticator:BricsSlurmSpawner", "jupyterhub.spawners", BricsSlurmSpawner, id="jupyterhub.spawners"),
        ]
)
def test_entrypoint(ep_name: str, ep_value: str, ep_group: str, ep_loaded: Any) -> None:
    """
    Check that entrypoints defined by the package are exposed as expected
    """

    group_entry_points = entry_points(group=ep_group)

    assert ep_name in group_entry_points.names, f'entry point named "{ep_name}" should be exposed in group "{ep_group}"'

    entry_point = group_entry_points[ep_name]

    assert (
        entry_point.value == ep_value
    ), f'"{ep_name}" entry point should have expected value "{ep_value}"'

    load_result = entry_point.load()

    assert (
        load_result is ep_loaded
    ), "calling load() on entry point should load BricsAuthenticator class"
