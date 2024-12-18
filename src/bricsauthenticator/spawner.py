"""
JupyterHub `Spawner` for the BriCS JupyterHub service
"""

import re
import shlex
from datetime import datetime
from typing import Callable

import batchspawner
from traitlets import default


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
        defused_options = {
            key: defuse(value)
            for key, value in validated_options.items() if value is not None
        }

        # Ensure optional fields are included, even if they are None
        if 'partition' not in defused_options:
            defused_options['partition'] = None
        if 'reservation' not in defused_options:
            defused_options['reservation'] = None

    except ValueError as e:
        raise ValueError(f"Invalid spawner options input: {str(e)}")

    return defused_options

class BricsSlurmSpawner(batchspawner.SlurmSpawner):
    """
    BriCS-specific specialisation of :class:`SlurmSpawner`
    """

    @default("auth_state_hook")
    def _auth_state_hook_default(self) -> Callable:
        """
        Return a function that gets the ``auth_state`` returned by `BricsAuthenticator

        ``auth_state`` is expected to contain a dictionary with BriCS project 
        names as keys
        """
        self.log.debug("Entering BricsSlurmSpawner._auth_state_hook_default")

        def auth_state_hook(spawner, auth_state) -> None:
            spawner.log.debug("Entering auth_state_hook")
            if auth_state:
                spawner.log.debug(f"Acquired auth_state: {str(auth_state)}")
                spawner.brics_projects = auth_state
            else:
                spawner.log.debug(f"No auth_state acquired")
                spawner.brics_projects = {}
            spawner.log.debug(f"BriCS projects: {self.brics_projects.keys()}")
        
        return auth_state_hook

    @default("options_form")
    def _options_form_default(self):
        """
        Return a function to generate HTML options form for user to configure spawned session

        The form must include a control with "brics_project" name that returns a single selected
        project from the list of projects in `BricsSlurmSpawner.brics_projects` (from ``auth_state``).
        """

        self.log.debug("Entering BricsSlurmSpawner._options_form_default")

        def make_options_form(spawner) -> str:
            # Use inline styling to make all control labels the same width
            # This causes form controls to be horizontally aligned
            label_style = 'display:inline-block;width:16em;text-align:left'

            # TODO Restrict list of selectable projects to those with access to Jupyter resources
            project_list = list(self.brics_projects.keys())
            project_options = [f'<option value="{project}">{project}</option>' for project in project_list]
            project_select = f'<label style="{label_style}" for="brics_project_select">Choose a project:</label>' + "\n".join(
                ['<select name="brics_project" id="brics_project_select">'] + project_options + ["</select>"]
            )


            runtime_list = [("01:00:00", "1h"), ("02:00:00", "2h"), ("04:00:00", "4h"), ("08:00:00", "8h")]
            runtime_options = [f'<option value="{value}">{label}</option>' for value, label in runtime_list]
            runtime_select = f'<label style="{label_style}" for="runtime_select">Select job duration:</label>' + "\n".join(
                ['<select name="runtime" id="runtime_select">'] + runtime_options + ["</select>"]
            )

            ngpus_list = list(range(1, 5))
            ngpus_options = [f'<option value="{ngpus}">{ngpus}</option>' for ngpus in ngpus_list]
            ngpus_select = f'<label style="{label_style}"for="ngpus_select">Select number of GH200s:</label>' + "\n".join(
                ['<select name="ngpus" id="ngpus_select">'] + ngpus_options + ["</select>"]
            )

            partition_default = ""
            partition_input = f'<label style="{label_style}" for="partition_input">Enter partition:</label>\n' + \
                    f'<input type="text" size=16 name="partition" id="partition_input" value="{partition_default}">'

            reservation_default = ""
            reservation_input = f'<label style="{label_style}" for="reservation_input">Enter reservation:</label>\n' + \
                    f'<input type="text" size=16 name="reservation" id="reservation_input" value="{reservation_default}">'

            return "\n".join(
                [
                    "<h2>", "Required settings", "</h2>",
                    "<p>", project_select, "</p>",
                    "<p>", runtime_select, "</p>",
                    "<p>", ngpus_select, "</p>",
                    "<hr>",
                    "<h2>", "Optional settings", "</h2>",
                    "<p>", "Leave empty to use default values", "</p>",
                    "<p>", partition_input, "</p>",
                    "<p>", reservation_input, "</p>",
                ]
            )
        
        return make_options_form

    @default("options_from_form")
    def _options_from_form_default(self):
        """
        Return a function to interpret and validate HTTP form data from the :class:`Spawner` options page

        `form_data` arrives as a dict of lists of strings. This function
        extracts data from the raw `form_data` input and transforms it
        into a form usable by the :class:`Spawner` (accessible via
        `self.user_options`).
        """

        def interpret_form_with_error_handling(form_data, spawner):
            valid_projects = set(spawner.brics_projects.keys())
            try:
                options = interpret_form_data(form_data, valid_projects)
            except ValueError as e:
                raise web.HTTPError(500, str(e))
            return options

        return interpret_form_with_error_handling

    @property
    def brics_project_user_name(self) -> str:
        """
        Get the BriCS project user name of the form <USER>.<PROJECT>

        :return: BriCS project user name
        """
        self.log.debug("Entering BricsSlurmSpawner.brics_project_user_name()")
        return self.user.name + "." + self.brics_project_name

    @property
    def brics_project_name(self) -> str:
        """
        Get the BriCS short project name as selected in the spawner options form

        :return: BriCS short project name
        """
        self.log.debug("Entering BricsSlurmSpawner.brics_project_name()")
        return self.user_options['brics_project']

    def _req_username_default(self) -> str:
        """
        Dynamic default value for req_username trait
        """
        self.log.debug("Entering BricsSlurmSpawner._req_username_default()")
        return self.brics_project_user_name

    def _req_homedir_default(self) -> str:
        """
        Dynamic default value for req_homedir trait
        """
        self.log.debug("Entering BricsSlurmSpawner._req_homedir_default()")
        return f"/home/{self.brics_project_name}/{self.brics_project_user_name}"

    def user_env(self, env):
        """
        Set user environment variables
        
        These are used in spawner submitting environment (see :func:`BatchSpawnerBase.submit_batch_script`) and the 
        user session job environment (see :func:`BatchSpawnerBase._req_keepvars_default`).

        This overrides :func:`UserEnvMixin.user_env`, avoiding accessing the Unix password database using
        :func:`pwd.getpwnam` (this does not make sense when running inside a container).

        :return: environment dictionary with USER, HOME, and SHELL keys set
        """
        self.log.debug("Entering BricsSlurmSpawner.user_env()")
        env["USER"] = self.req_username
        env["HOME"] = self.req_homedir
        env["SHELL"] = "/bin/bash"
        return env

