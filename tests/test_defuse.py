"""
pytest tests/test_validate_and_defuse.py
"""
import pytest
from bricsauthenticator.spawner import defuse

class TestValidateAndDefuse:
    @pytest.mark.parametrize(
        "input_to_defuse, defused_output",
        [
            ("", "''"),
            ("brics", "brics"),
            ("brics ", "'brics '"),
            (" brics ", "' brics '"),
            ("brics; ls -l /", "'brics; ls -l /'"),
            ("my-project", "my-project"),
            ("my-project; ls", "'my-project; ls'"),
            ("my_project", "my_project"),
            ("my/project", "my/project"),
            (r"my\ project", r"'my\ project'"),
            ("project100", "project100"),
            ("$project100", "'$project100'"),
        ]
    )
    def test_defuse(self, input_to_defuse, defused_output):
        result = defuse(input_to_defuse)
        assert result == defused_output  # No single quote needed though for this regex
