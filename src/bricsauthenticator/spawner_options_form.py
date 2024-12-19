"""
Functions relating to `Spawner` options form generation and validation
"""

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