"""
pytest tests/test_interpret_form_data.py
"""
import pytest
from bricsauthenticator.spawner import interpret_form_data

class TestInterpretFormData:

    @pytest.fixture
    def valid_projects(self):
        return {"valid_project", "valid-project", "validproject1", "another_project"}

    @pytest.mark.parametrize(
        "form_data",
        [ 
            {
                "brics_project": ["valid_project"],
                "runtime": ["01:00:00"],
                "ngpus": ["1"],
                "partition": ["valid_partition"],
                "reservation": ["valid_reservation"],
            },
            {
                "brics_project": ["valid-project"],
                "runtime": ["00:12:34"],
                "ngpus": ["2"],
                "partition": ["valid-partition"],
                "reservation": ["valid-reservation"],
            },
            {
                "brics_project": ["validproject1"],
                "runtime": ["23:59:59"],
                "ngpus": ["3"],
                "partition": ["validpartition1"],
                "reservation": ["validreservation1"],
            },
            {
                "brics_project": ["valid_project"],
                "runtime": ["01:00:00"],
                "ngpus": ["4"],
                "partition": ["VALID_partition"],
                "reservation": ["VALID_reservation"],
            }
        ]
    )
    def test_valid_input(self, valid_projects, form_data):

        result = interpret_form_data(form_data, valid_projects)
        assert result["brics_project"] == form_data["brics_project"][0]
        assert result["runtime"] == form_data["runtime"][0]
        assert result["ngpus"] == form_data["ngpus"][0]
        assert result["partition"] == form_data["partition"][0]
        assert result["reservation"] == form_data["reservation"][0]


    @pytest.mark.parametrize(
            "project",
            ["unknown_project", "unknown-project", "unknownproject1"]
    )
    def test_invalid_brics_project(self, valid_projects, project):
        form_data = {
            "brics_project": [project],
            "runtime": ["01:00:00"],
            "ngpus": ["1"],
        }

        with pytest.raises(ValueError, match="unknown brics_project"):
            interpret_form_data(form_data, valid_projects)

    @pytest.mark.parametrize(
            "project",
            [
                pytest.param("invalid project", id="with space"),
                pytest.param("invalid_project!", id="with !"),
                pytest.param("1invalid_project", id="first char is number"),
                pytest.param("invalidProject", id="with capital letter"),
            ]
    )
    def test_invalid_brics_project_format(self, valid_projects, project):
        form_data = {
            "brics_project": [project],
            "runtime": ["01:00:00"],
            "ngpus": ["1"],
        }

        with pytest.raises(ValueError, match="brics_project not valid"):
            interpret_form_data(form_data, valid_projects)


    @pytest.mark.parametrize(
            "runtime",
            [
                pytest.param("25:00:00", id="invalid time specification"),
                pytest.param("25 00 00", id="with space"),
                pytest.param("25:00:00!", id="with !"),
                pytest.param("25_00_00", id="_ instead of : "),
            ]
    )
    def test_invalid_runtime(self, valid_projects, runtime):
        form_data = {
            "brics_project": ["valid_project"],
            "runtime": [runtime],  # Invalid time format
            "ngpus": ["1"],
        }

        with pytest.raises(ValueError, match="runtime not valid"):
            interpret_form_data(form_data, valid_projects)

    @pytest.mark.parametrize(
            "ngpus",
            [
                pytest.param("10", id="invalid GPU count"),
                pytest.param("1 0", id="with space"),
                pytest.param("1-", id="with dash"),
            ]
    )
    def test_invalid_ngpus(self, valid_projects, ngpus):
        form_data = {
            "brics_project": ["valid_project"],
            "runtime": ["01:00:00"],
            "ngpus": [ngpus],  # Invalid GPU count
        }

        with pytest.raises(ValueError, match="ngpus not valid"):
            interpret_form_data(form_data, valid_projects)

    @pytest.mark.parametrize(
            "partition",
            [
                pytest.param("invalid partition", id="with space"),
                pytest.param("invalid_partition!", id="with !"),
            ]
    )
    def test_invalid_partition_format(self, valid_projects, partition):
        form_data = {
            "brics_project": ["valid_project"],
            "runtime": ["01:00:00"],
            "ngpus": ["1"],
            "partition": [partition],  # Invalid partition format
        }

        with pytest.raises(ValueError, match="partition not valid"):
            interpret_form_data(form_data, valid_projects)

    @pytest.mark.parametrize(
            "reservation",
            [
                pytest.param("invalid reservation", id="with space"),
                pytest.param("invalid_reservation!", id="with !"),
            ]
    )
    def test_invalid_reservation_format(self, valid_projects, reservation):
        form_data = {
            "brics_project": ["valid_project"],
            "runtime": ["01:00:00"],
            "ngpus": ["1"],
            "reservation": [reservation],  # Invalid reservation format
        }

        with pytest.raises(ValueError, match="reservation not valid"):
            interpret_form_data(form_data, valid_projects)

    def test_optional_fields_empty(self, valid_projects):
        form_data = {
            "brics_project": ["valid_project"],
            "runtime": ["01:00:00"],
            "ngpus": ["1"],
            "partition": [""],  # Empty partition (should default to None)
            "reservation": [""],  # Empty reservation (should default to None)
        }

        result = interpret_form_data(form_data, valid_projects)
        assert result["brics_project"] == "valid_project"
        assert result["runtime"] == "01:00:00"
        assert result["ngpus"] == '1'
        assert result["partition"] is None
        assert result["reservation"] is None

    def test_missing_optional_fields(self, valid_projects):
        form_data = {
            "brics_project": ["valid_project"],
            "runtime": ["01:00:00"],
            "ngpus": ["1"],
            # partition and reservation are missing
        }

        result = interpret_form_data(form_data, valid_projects)
        assert result["brics_project"] == "valid_project"
        assert result["runtime"] == '01:00:00'
        assert result["ngpus"] == '1'
        assert result["partition"] is None
        assert result["reservation"] is None

    def test_all_valid_without_optional_fields(self, valid_projects):
        form_data = {
            "brics_project": ["valid_project"],
            "runtime": ["01:00:00"],
            "ngpus": ["1"],
            # No optional fields (partition and reservation)
        }

        result = interpret_form_data(form_data, valid_projects)
        assert result["brics_project"] == "valid_project"
        assert result["runtime"] == '01:00:00'
        assert result["ngpus"] == '1'
        assert result["partition"] is None
        assert result["reservation"] is None

    def test_invalid_form_data_unknown_key(self, valid_projects):
        form_data = {
            "brics_project": ["valid_project"],
            "runtime": ["01:00:00"],
            "ngpus": ["1"],
            "partition": [""],
            "reservation": [""],
            "invalid_key": ["data"]
        }

        with pytest.raises(ValueError, match="unknown form data keys"):
            _ = interpret_form_data(form_data, valid_projects)


    def test_edge_case_empty_form(self, valid_projects):
        form_data = {
            "brics_project": [""],
            "runtime": [""],
            "ngpus": [""],
            "partition": [""],
            "reservation": [""],
        }

        with pytest.raises(ValueError):
            interpret_form_data(form_data, valid_projects)

    def test_invalid_regex_patterns(self, valid_projects):
        form_data = {
            "brics_project": ["valid_project"],  # This one is valid
            "runtime": ["InvalidTimeFormat"],   # Invalid time format
            "ngpus": ["NotANumber"],            # Not a valid GPU count
            "partition": ["Invalid Partition!"], # Invalid partition format
            "reservation": ["Invalid Reservation!"], # Invalid reservation format
        }

        with pytest.raises(ValueError):
            interpret_form_data(form_data, valid_projects)
