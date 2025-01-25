import pytest
from unittest.mock import MagicMock
from bricsauthenticator.spawner import BricsSlurmSpawner


def test_auth_state_hook_default():
    spawner = BricsSlurmSpawner()
    auth_state_hook = spawner.auth_state_hook

    mock_auth_state = {"project1": ["infra1", "infra2"]}
    spawner.brics_projects = {}
    auth_state_hook(spawner, mock_auth_state)

    assert spawner.brics_projects == mock_auth_state

    auth_state_hook(spawner, None)
    assert spawner.brics_projects == {}


def test_options_form_default(mocker):
    mock_make_options_form = mocker.MagicMock(return_value="<form>mock_form</form>")
    spawner = BricsSlurmSpawner(make_options_form_fn=mock_make_options_form)

    form_callable = spawner.options_form
    assert form_callable(spawner) == "<form>mock_form</form>"
    mock_make_options_form.assert_called_once_with(project_list=[])


def test_options_from_form_default(mocker):
    mock_interpret_form_data = mocker.MagicMock(return_value={"brics_project": "project1"})
    spawner = BricsSlurmSpawner(interpret_form_data_fn=mock_interpret_form_data)
    form_data = {"brics_project": ["project1"]}

    options_callable = spawner.options_from_form
    user_options = options_callable(form_data, spawner)
    assert user_options == {"brics_project": "project1"}
    mock_interpret_form_data.assert_called_once_with(form_data, set())


def test_brics_project_properties():
    spawner = BricsSlurmSpawner()
    spawner.user = MagicMock()
    spawner.user.name = "testuser"
    spawner.user_options = {"brics_project": "project1"}

    assert spawner.brics_project_user_name == "testuser.project1"
    assert spawner.brics_project_name == "project1"


def test_user_env():
    spawner = BricsSlurmSpawner()
    spawner.req_username = "testuser.project1"
    spawner.req_homedir = "/home/project1/testuser.project1"

    env = spawner.user_env({})
    assert env["USER"] == "testuser.project1"
    assert env["HOME"] == "/home/project1/testuser.project1"
    assert env["SHELL"] == "/bin/bash"
