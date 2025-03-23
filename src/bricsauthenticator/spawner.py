"""
JupyterHub `Spawner` for the BriCS JupyterHub service
"""

from typing import Callable

import batchspawner
from tornado import web
from traitlets import Dict, Unicode, default

from bricsauthenticator.spawner_options_form import interpret_form_data, make_options_form


class BricsSlurmSpawner(batchspawner.SlurmSpawner):
    """
    BriCS-specific specialisation of :class:`SlurmSpawner`
    """

    brics_projects = Dict(
        value_trait=Dict(value_trait=Unicode(), key_trait=Unicode()),
        key_trait=Unicode(),
        help="""
        Dictionary mapping BriCS project names to dict of associated BriCS resources.
        
        Should be set by Authenticator via Spawner.auth_state_hook()
        """,
        default_value=dict(),
    )

    def __init__(
        self,
        interpret_form_data_fn: Callable = interpret_form_data,
        make_options_form_fn: Callable = make_options_form,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.interpret_form_data_fn = interpret_form_data_fn
        self.make_options_form_fn = make_options_form_fn

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
                spawner.log.debug("No auth_state acquired")
                spawner.brics_projects = {}
            spawner.log.debug(f"BriCS projects: {self.brics_projects.keys()}")

        return auth_state_hook

    @default("options_form")
    def _options_form_default(self) -> Callable:
        """
        Return a function to generate HTML options form for user to configure spawned session

        The form must include a control with "brics_project" name that returns a single selected
        project from the list of projects in `BricsSlurmSpawner.brics_projects` (from ``auth_state``).
        """

        self.log.debug("Entering BricsSlurmSpawner._options_form_default")

        def spawner_options_form(spawner):
            if not self.make_options_form_fn:
                raise ValueError("make_options_form_fn is not provided")
            return self.make_options_form_fn(projects=spawner.brics_projects)

        return spawner_options_form

    @default("options_from_form")
    def _options_from_form_default(self) -> Callable:
        """
        Return a function to interpret and validate HTTP form data from the :class:`Spawner` options page

        `form_data` arrives as a dict of lists of strings. This function
        extracts data from the raw `form_data` input and transforms it
        into a form usable by the :class:`Spawner` (accessible via
        `self.user_options`).
        """

        def interpret_form_with_error_handling(form_data, spawner):
            if not self.interpret_form_data_fn:
                raise ValueError("interpret_form_data_fn is not provided")
            valid_projects = set(spawner.brics_projects.keys())
            try:
                options = self.interpret_form_data_fn(form_data, valid_projects)
            except ValueError as e:
                raise web.HTTPError(500, str(e))
            return options

        return interpret_form_with_error_handling

    @property
    def brics_project_user_name(self) -> str:
        """
        Get the BriCS project user name based on the project selected in the spawner options form

        :return: BriCS project user name
        """
        self.log.debug("Entering BricsSlurmSpawner.brics_project_user_name()")
        return self.brics_projects[self.user_options["brics_project"]]["username"]

    @property
    def brics_project_name(self) -> str:
        """
        Get the BriCS short project name as selected in the spawner options form

        :return: BriCS short project name
        """
        self.log.debug("Entering BricsSlurmSpawner.brics_project_name()")
        return self.user_options["brics_project"]

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
        return f"/home/{self.brics_project_name.partition('.')[0]}/{self.brics_project_user_name}"

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

    def load_state(self, state: dict) -> None:
        """
        Restore state of :class:`BricsSlurmSpawner` after hub process restarts

        Overrides :func:`BatchSpawnerBase.loadstate` to add additional state
        specific to :class:`BricsSlurmSpawner`. 

        :param state: dict containing state loaded from database
        """
        super().load_state(state)
        if "brics_projects" in state:
            self.brics_projects = state["brics_projects"]
            self.log.debug(f"BricsSlurmSpawner.load_state() acquired brics_projects: {self.brics_projects}")

    def get_state(self) -> dict:
        """
        Save state of :class:`BricsSlurmSpawner` into database

        Overrides :func:`BatchSpawnerBase.loadstate` to add additional state
        specific to :class:`BricsSlurmSpawner`. 

        :return: a JSONable dict of state to persist in the database
        """
        state = super().get_state()
        state["brics_projects"] = self.brics_projects
        self.log.debug(f"BricsSlurmSpawner saving brics_projects: {self.brics_projects}")
        return state

    def clear_state(self) -> None:
        """
        Clear state of :class:`BricsSlurmSpawner` when single user server is stopped
        
        Overrides :func:`BatchSpawnerBase.loadstate` to add additional state
        specific to :class:`BricsSlurmSpawner`. 

        .. note::
            
            There is currently no additional state to clear as `brics_projects`
            should be persisted between single-user server instances. 
        """
        super().clear_state()
