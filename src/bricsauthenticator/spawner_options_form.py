"""
Functions relating to `Spawner` options form generation and validation
"""

import re
import shlex
from datetime import datetime

def make_options_form(project_list: list[str]) -> str:
    # Use inline styling to make all control labels the same width
    # This causes form controls to be horizontally aligned
    label_style = "display:inline-block;width:16em;text-align:left"

    # TODO Restrict list of selectable projects to those with access to Jupyter resources
    project_options = [f'<option value="{project}">{project}</option>' for project in project_list]
    project_select = (
        f'<label style="{label_style}" for="brics_project_select">Choose a project:</label>'
        + "\n".join(
            ['<select name="brics_project" id="brics_project_select">'] + project_options + ["</select>"]
        )
    )

    runtime_list = [("01:00:00", "1h"), ("02:00:00", "2h"), ("04:00:00", "4h"), ("08:00:00", "8h")]
    runtime_options = [f'<option value="{value}">{label}</option>' for value, label in runtime_list]
    runtime_select = (
        f'<label style="{label_style}" for="runtime_select">Select job duration:</label>'
        + "\n".join(['<select name="runtime" id="runtime_select">'] + runtime_options + ["</select>"])
    )

    ngpus_list = list(range(1, 5))
    ngpus_options = [f'<option value="{ngpus}">{ngpus}</option>' for ngpus in ngpus_list]
    ngpus_select = (
        f'<label style="{label_style}"for="ngpus_select">Select number of GH200s:</label>'
        + "\n".join(['<select name="ngpus" id="ngpus_select">'] + ngpus_options + ["</select>"])
    )

    partition_default = ""
    partition_input = (
        f'<label style="{label_style}" for="partition_input">Enter partition:</label>\n'
        + f'<input type="text" size=16 name="partition" id="partition_input" value="{partition_default}">'
    )

    reservation_default = ""
    reservation_input = (
        f'<label style="{label_style}" for="reservation_input">Enter reservation:</label>\n'
        + f'<input type="text" size=16 name="reservation" id="reservation_input" value="{reservation_default}">'
    )

    return "\n".join(
        [
            "<h2>",
            "Required settings",
            "</h2>",
            "<p>",
            project_select,
            "</p>",
            "<p>",
            runtime_select,
            "</p>",
            "<p>",
            ngpus_select,
            "</p>",
            "<hr>",
            "<h2>",
            "Optional settings",
            "</h2>",
            "<p>",
            "Leave empty to use default values",
            "</p>",
            "<p>",
            partition_input,
            "</p>",
            "<p>",
            reservation_input,
            "</p>",
        ]
    )


def defuse(input_to_defuse: str) -> str:
    """
    Apply shell quoting to defuse an input string for use in shell commands

    :return: input_to_defuse with shell-escaping
    """
    return shlex.quote(input_to_defuse)


def validate_form_data(form_data, valid_projects):
    """
    Validate the form data.

    :param form_data: The submitted form data as a dictionary of lists.
    :param valid_projects: A set of valid project names.
    :return: A dictionary of validated options.
    :raises ValueError: If any validation fails.
    """
    options = {}

    # Only allow expected keys in form_data
    if not set(form_data.keys()).issubset({"brics_project", "runtime", "ngpus", "partition", "reservation"}):
        raise ValueError("unknown form data keys")

    # Validate brics_project
    brics_project_regex = r"^[a-z][a-z0-9\-_]+$"
    brics_project = str(form_data["brics_project"][0])
    if not re.fullmatch(brics_project_regex, brics_project):
        raise ValueError("brics_project not valid")
    if brics_project not in valid_projects:
        raise ValueError("unknown brics_project")
    options["brics_project"] = brics_project

    # Validate runtime
    runtime = str(form_data["runtime"][0])
    try:
        datetime.strptime(runtime, "%H:%M:%S")
    except ValueError:
        raise ValueError("runtime not valid")
    options["runtime"] = runtime

    # Validate ngpus
    ngpus_regex = r"^\d$"
    ngpus = str(form_data["ngpus"][0])
    if not re.fullmatch(ngpus_regex, ngpus):
        raise ValueError("ngpus not valid")
    options["ngpus"] = ngpus

    # Handle partition (optional)
    partition_regex = r"^[a-zA-Z0-9\-_]*$"
    partition = str(form_data.get("partition", [""])[0])
    if partition and not re.fullmatch(partition_regex, partition):
        raise ValueError("partition not valid")
    options["partition"] = partition or None

    # Handle reservation (optional)
    reservation_regex = r"^[a-zA-Z0-9\-_]*$"
    reservation = str(form_data.get("reservation", [""])[0])
    if reservation and not re.fullmatch(reservation_regex, reservation):
        raise ValueError("reservation not valid")
    options["reservation"] = reservation or None

    return options


def interpret_form_data(form_data, valid_projects):
    """
    Interpret and validate form data.

    :param form_data: The submitted form data as a dictionary of lists.
    :param valid_projects: A set of valid project names.
    :return: A dictionary of validated and defused options.
    :raises ValueError: If any validation fails.
    """

    try:
        # Validate the form data
        validated_options = validate_form_data(form_data, valid_projects)

        # Defuse the validated options (make safe for shell use)
        defused_options = {key: defuse(value) for key, value in validated_options.items() if value is not None}

        # Ensure optional fields are included, even if they are None
        if "partition" not in defused_options:
            defused_options["partition"] = None
        if "reservation" not in defused_options:
            defused_options["reservation"] = None

    except ValueError as e:
        raise ValueError(f"Invalid spawner options input: {str(e)}")

    return defused_options