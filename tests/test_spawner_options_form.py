import pytest

from bricsauthenticator.spawner_options_form import defuse, interpret_form_data, make_options_form


class TestDefuse:
    @pytest.mark.parametrize(
        "input_to_defuse, defused_output",
        [
            ("", "''"),
            ("brics", "brics"),
            ("brics ", "'brics '"),
            (" brics ", "' brics '"),
            ("brics; ls -l /", "'brics; ls -l /'"),
            ("my-project.portal", "my-project.portal"),
            ("my-project.portal; ls", "'my-project.portal; ls'"),
            ("my_project.portal", "my_project.portal"),
            ("my/project.a_portal", "my/project.a_portal"),
            (r"my\ project.my\ portal", r"'my\ project.my\ portal'"),
            ("project100.portal200", "project100.portal200"),
            ("$project100.$portal200", "'$project100.$portal200'"),
        ],
    )
    def test_defuse(self, input_to_defuse, defused_output):
        result = defuse(input_to_defuse)
        assert result == defused_output


class TestInterpretFormData:

    @pytest.fixture
    def valid_projects(self):
        return {
            "valid_project.a_portal",
            "valid-project.a-portal",
            "validproject1.portal1",
            "another_project.anotherportal",
        }

    @pytest.mark.parametrize(
        "form_data",
        [
            {
                "brics_project": ["valid_project.a_portal"],
                "runtime": ["01:00:00"],
                "ngpus": ["1"],
                "partition": ["valid_partition"],
                "reservation": ["valid_reservation"],
            },
            {
                "brics_project": ["valid-project.a-portal"],
                "runtime": ["00:12:34"],
                "ngpus": ["2"],
                "partition": ["valid-partition"],
                "reservation": ["valid-reservation"],
            },
            {
                "brics_project": ["validproject1.portal1"],
                "runtime": ["23:59:59"],
                "ngpus": ["3"],
                "partition": ["validpartition1"],
                "reservation": ["validreservation1"],
            },
            {
                "brics_project": ["valid_project.a_portal"],
                "runtime": ["01:00:00"],
                "ngpus": ["4"],
                "partition": ["VALID_partition"],
                "reservation": ["VALID_reservation"],
            },
        ],
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
        ["unknown_project.unknown_portal", "unknown-project.unknown-portal", "unknownproject1.unknownportal1"],
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
            pytest.param("invalid project.portal", id="project with space"),
            pytest.param("invalid_project!.portal", id="project with !"),
            pytest.param("1invalid_project.portal", id="project first char is number"),
            pytest.param("invalidProject.portal", id="project with capital letter"),
            pytest.param("project.invalid portal", id="portal with space"),
            pytest.param("project.invalid_portal!", id="portal with !"),
            pytest.param("project.1invalid_portal", id="portal first char is number"),
            pytest.param("project.invalidPortal", id="portal with capital letter"),
            pytest.param("project", id="no dot"),
            pytest.param(".project", id="dot at start"),
            pytest.param("project.", id="dot at end"),
            pytest.param("project..portal", id="2 dots in the middle"),
            pytest.param("project.something.portal", id="3 dot-separate strings"),
        ],
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
        ],
    )
    def test_invalid_runtime(self, valid_projects, runtime):
        form_data = {
            "brics_project": ["valid_project.a_portal"],
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
        ],
    )
    def test_invalid_ngpus(self, valid_projects, ngpus):
        form_data = {
            "brics_project": ["valid_project.a_portal"],
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
        ],
    )
    def test_invalid_partition_format(self, valid_projects, partition):
        form_data = {
            "brics_project": ["valid_project.a_portal"],
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
        ],
    )
    def test_invalid_reservation_format(self, valid_projects, reservation):
        form_data = {
            "brics_project": ["valid_project.a_portal"],
            "runtime": ["01:00:00"],
            "ngpus": ["1"],
            "reservation": [reservation],  # Invalid reservation format
        }

        with pytest.raises(ValueError, match="reservation not valid"):
            interpret_form_data(form_data, valid_projects)

    def test_optional_fields_empty(self, valid_projects):
        form_data = {
            "brics_project": ["valid_project.a_portal"],
            "runtime": ["01:00:00"],
            "ngpus": ["1"],
            "partition": [""],  # Empty partition (should default to None)
            "reservation": [""],  # Empty reservation (should default to None)
        }

        result = interpret_form_data(form_data, valid_projects)
        assert result["brics_project"] == "valid_project.a_portal"
        assert result["runtime"] == "01:00:00"
        assert result["ngpus"] == "1"
        assert result["partition"] is None
        assert result["reservation"] is None

    def test_missing_optional_fields(self, valid_projects):
        form_data = {
            "brics_project": ["valid_project.a_portal"],
            "runtime": ["01:00:00"],
            "ngpus": ["1"],
            # partition and reservation are missing
        }

        result = interpret_form_data(form_data, valid_projects)
        assert result["brics_project"] == "valid_project.a_portal"
        assert result["runtime"] == "01:00:00"
        assert result["ngpus"] == "1"
        assert result["partition"] is None
        assert result["reservation"] is None

    def test_invalid_form_data_unknown_key(self, valid_projects):
        form_data = {
            "brics_project": ["valid_project.a_portal"],
            "runtime": ["01:00:00"],
            "ngpus": ["1"],
            "partition": [""],
            "reservation": [""],
            "invalid_key": ["data"],
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
            "brics_project": ["valid_project.a_portal"],  # This one is valid
            "runtime": ["InvalidTimeFormat"],  # Invalid time format
            "ngpus": ["NotANumber"],  # Not a valid GPU count
            "partition": ["Invalid Partition!"],  # Invalid partition format
            "reservation": ["Invalid Reservation!"],  # Invalid reservation format
        }

        with pytest.raises(ValueError):
            interpret_form_data(form_data, valid_projects)


class TestMakeOptionsForm:

    def test_make_options_form_basic(self):
        """
        Test the make_options_form function with a basic project list.
        """
        projects = {
            "project1.portal": {"name": "Important project 1", "username": "vip.project1"},
            "project2.portal": {"name": "A Project 2", "username": "a_user.project2"},
            "project3.portal": {"name": "The Project 3", "username": "the_user.project3"},
        }
        html_output = make_options_form(projects)

        for project_id, project_data in projects.items():
            assert f'<option value="{project_id}">{project_id}: {project_data["name"]}</option>' in html_output

        assert '<select name="brics_project" id="brics_project_select">' in html_output
        assert '<select name="runtime" id="runtime_select">' in html_output
        assert '<select name="ngpus" id="ngpus_select">' in html_output

    def test_make_options_form_empty_projects(self):
        """
        Test the make_options_form function with an empty projects dict
        """
        html_output = make_options_form({})

        # Check for the placeholder option
        assert '<option value="" disabled>No projects available</option>' in html_output

        # Ensure the select element still exists
        assert '<select name="brics_project" id="brics_project_select">' in html_output

    def test_make_options_form_special_characters(self):
        """
        Test the make_options_form function with project names containing special characters.
        """
        projects = {
            "proj&1": {"name": "Special char project 1", "username": "special_char_user1"},
            "proj<2": {"name": "Special char project 2", "username": "special_char_user2"},
            "proj>3": {"name": "Special char project 3", "username": "special_char_user3"},
        }
        html_output = make_options_form(projects)

        for project_id, project_data in projects.items():
            assert f'<option value="{project_id}">{project_id}: {project_data["name"]}</option>' in html_output
