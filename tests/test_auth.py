import datetime
import json
import time
from contextlib import AbstractContextManager, nullcontext
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from tornado.httputil import HTTPHeaders, HTTPServerRequest
from tornado.web import Application, HTTPError

from bricsauthenticator.auth import BricsAuthenticator, BricsLoginHandler


@pytest.fixture
def handler():
    # Create a real Application instance with necessary settings
    application = Application()
    application.settings = {
        "hub": MagicMock(base_url="/hub/"),  # Mock 'hub' with base_url as a string
        "cookie_secret": b"secret",  # Add other required settings
        "log_function": MagicMock(),  # Mock the application-level logger
    }

    # Mock request with a connection attribute and empty headers
    request = MagicMock(spec=HTTPServerRequest)
    request.connection = MagicMock()  # Add the 'connection' attribute
    request.headers = HTTPHeaders({})

    # Initialize BricsLoginHandler with the mocked application, request, and required arguments
    handler_instance = BricsLoginHandler(
        application,
        request,
        platform="portal.dummy.platform.shared",
        jwt_audience="dummy-audience",
        jwt_leeway=5,
        oidc_server="https://example.com",
    )
    handler_instance.http_client = AsyncMock()
    handler_instance.jwks_client_factory = MagicMock()
    return handler_instance


def test_extract_token_missing_header(handler):
    handler.request.headers = HTTPHeaders({})
    with pytest.raises(HTTPError) as exc_info:
        handler._extract_token()
    assert exc_info.value.status_code == 401
    assert "Missing X-Auth-Id-Token header" in str(exc_info.value)


def test_extract_token_success(handler):
    handler.request.headers = HTTPHeaders({"X-Auth-Id-Token": "fake_token"})
    token = handler._extract_token()
    assert token == "fake_token"


@pytest.mark.asyncio
async def test_fetch_oidc_config_success(handler):
    mock_response = AsyncMock()
    mock_response.body = b'{"key": "value"}'
    handler.http_client.fetch.return_value = mock_response

    config = await handler._fetch_oidc_config()
    assert config == {"key": "value"}


@pytest.mark.asyncio
async def test_fetch_oidc_config_failure(handler):
    handler.http_client.fetch.side_effect = Exception("Fetch error")
    with pytest.raises(HTTPError) as exc_info:
        await handler._fetch_oidc_config()
    assert exc_info.value.status_code == 500


def test_parse_oidc_config(handler):
    oidc_config = {"id_token_signing_alg_values_supported": ["RS256"], "jwks_uri": "https://example.com/jwks_uri"}
    signing_algos, jwks_uri = handler._parse_oidc_config(oidc_config)
    assert signing_algos == ["RS256"]
    assert jwks_uri == "https://example.com/jwks_uri"


def test_fetch_signing_key(handler):
    mock_jwks_client = MagicMock()
    handler.jwks_client_factory.return_value = mock_jwks_client
    mock_signing_key = MagicMock()
    mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key

    signing_key = handler._fetch_signing_key("https://example.com/jwks_uri", "fake_token")
    assert signing_key == mock_signing_key
    handler.jwks_client_factory.assert_called_with("https://example.com/jwks_uri")
    mock_jwks_client.get_signing_key_from_jwt.assert_called_with("fake_token")


def test_decode_jwt_success(handler):
    handler.jwt_audience = "zenith-jupyter"  # Match token's "aud" claim
    decoded_token = {
        "aud": "zenith-jupyter",  # Should match handler.jwt_audience
        "exp": 12345,
        "iss": "https://example.com",
        "iat": 12344,
        "short_name": "user",
        "projects": {},
    }
    mock_signing_key = MagicMock()
    mock_signing_key.key = "fake_key"

    with patch("jwt.decode", return_value=decoded_token):
        result = handler._decode_jwt("fake_token", mock_signing_key, ["RS256"])
        assert result == decoded_token
        assert result == decoded_token


def test_decode_jwt_failure(handler):
    handler.jwt_audience = "zenith-jupyter"
    mock_signing_key = MagicMock()
    mock_signing_key.key = "fake_key"

    with patch("jwt.decode", side_effect=jwt.InvalidTokenError("Invalid token")):
        with pytest.raises(HTTPError) as exc_info:
            handler._decode_jwt("fake_token", mock_signing_key, ["RS256"])
        assert exc_info.value.status_code == 401


def test_normalize_projects_invalid_json(handler):
    decoded_token = {"projects": "invalid_json"}
    result = handler._normalize_projects(decoded_token)
    assert result == {}  # Expect an empty dict instead of a raw string


def test_normalize_projects_none(handler):
    decoded_token = {}
    result = handler._normalize_projects(decoded_token)
    assert result == {}


@pytest.mark.parametrize(
    "platform,normalized_projects,expected_result",
    [
        pytest.param(
            "portal.example.clusters.shared",
            {
                "project1.portal": {
                    "name": "Project 1",
                    "resources": [{"name": "portal.example.other.shared", "username": "test_user.project1"}],
                }
            },
            {},
            id="1 project, 0 matching platform",
        ),
        pytest.param(
            "portal.example.notebooks.shared",
            {
                "project1.portal": {
                    "name": "Project 1",
                    "resources": [
                        {"name": "portal.example.notebooks.shared", "username": "test_notebook_user.project1"},
                        {"name": "portal.example.other.shared", "username": "test_user.project1"},
                    ],
                }
            },
            {"project1.portal": {"name": "Project 1", "username": "test_notebook_user.project1"}},
            id="1 project, 1 matching platform",
        ),
        pytest.param(
            "portal.example.clusters.shared",
            {
                "project1.portal": {
                    "name": "Project 1",
                    "resources": [{"name": "portal.example.other.shared", "username": "test_user.project1"}],
                },
                "project2.portal": {
                    "name": "Project 2",
                    "resources": [{"name": "portal.example.other.shared", "username": "test_user.project2"}],
                },
            },
            {},
            id="2 project, 0 matching platform",
        ),
        pytest.param(
            "portal.example.notebooks.shared",
            {
                "project1.portal": {
                    "name": "Project 1",
                    "resources": [
                        {"name": "portal.example.notebooks.shared", "username": "test_notebook_user.project1"},
                        {"name": "portal.example.clusters.shared", "username": "test_cluster_user.project1"},
                    ],
                },
                "project2.portal": {
                    "name": "Project 2",
                    "resources": [{"name": "portal.example.other.shared", "username": "test_user.project2"}],
                },
            },
            {"project1.portal": {"name": "Project 1", "username": "test_notebook_user.project1"}},
            id="2 project, 1 matching platform",
        ),
        pytest.param(
            "portal.example.notebooks.shared",
            {
                "project1.portal": {
                    "name": "Project 1",
                    "resources": [
                        {"name": "portal.example.notebooks.shared", "username": "test_notebook_user.project1"},
                        {"name": "portal.example.clusters.shared", "username": "test_cluster_user.project1"},
                    ],
                },
                "project2.portal": {
                    "name": "Project 2",
                    "resources": [
                        {"name": "portal.example.notebooks.shared", "username": "test_notebook_user.project2"}
                    ],
                },
            },
            {
                "project1.portal": {"name": "Project 1", "username": "test_notebook_user.project1"},
                "project2.portal": {"name": "Project 2", "username": "test_notebook_user.project2"},
            },
            id="2 project, 2 matching platform",
        ),
    ],
)
def test_auth_state_from_projects(handler, platform: str, normalized_projects: dict, expected_result: dict):
    result = handler._auth_state_from_projects(projects=normalized_projects, platform=platform)
    assert result == expected_result


@pytest.mark.asyncio
async def test_get():
    # Create a real Application instance with necessary settings
    application = Application()
    application.settings = {
        "hub": MagicMock(base_url="/hub/"),  # Mock 'hub' with base_url as a string
        "cookie_secret": b"secret",  # Add other required settings
    }

    # Mock request with a connection attribute
    request = MagicMock(spec=HTTPServerRequest)
    request.connection = MagicMock()  # Add the 'connection' attribute
    request.headers = HTTPHeaders({"X-Auth-Id-Token": "fake_token"})

    # Create an instance of the handler
    handler = BricsLoginHandler(
        application,
        request,
        platform="portal.cluster.example.shared",
        oidc_server="https://example.com",
        jwt_audience="dummy-audience",
        jwt_leeway=5,
    )

    # Mock handler dependencies
    handler._extract_token = MagicMock(return_value="mock_token")
    handler._fetch_oidc_config = AsyncMock(
        return_value={"id_token_signing_alg_values_supported": ["RS256"], "jwks_uri": "https://example.com/jwks"}
    )
    handler._parse_oidc_config = MagicMock(return_value=(["RS256"], "https://example.com/jwks"))
    handler._fetch_signing_key = MagicMock(return_value=MagicMock(key="mock_key"))
    projects = {
        "project1": {
            "name": "Project 1",
            "resources": [{"name": "portal.cluster.example.shared", "username": "test_user.project1"}],
        }
    }
    decoded_token = {"short_name": "test_user", "projects": projects}
    handler._decode_jwt = MagicMock(return_value=decoded_token)
    handler._normalize_projects = MagicMock(return_value=projects)
    auth_state = {"project1": {"name": "Project 1", "username": "test_user.project1"}}
    handler._auth_state_from_projects = MagicMock(return_value=auth_state)
    user = MagicMock()
    user.name = "test_user"
    handler.auth_to_user = AsyncMock(return_value=user)
    handler.set_login_cookie = MagicMock()
    handler.get_next_url = MagicMock(return_value="/home")
    handler.redirect = MagicMock()

    # Call the actual `get` method
    await handler.get()

    # Assertions
    handler._extract_token.assert_called_once()
    handler._fetch_oidc_config.assert_called_once()
    handler._parse_oidc_config.assert_called_once_with(
        {"id_token_signing_alg_values_supported": ["RS256"], "jwks_uri": "https://example.com/jwks"}
    )
    handler._fetch_signing_key.assert_called_once_with("https://example.com/jwks", "mock_token")
    handler._decode_jwt.assert_called_once_with("mock_token", handler._fetch_signing_key.return_value, ["RS256"])
    handler._normalize_projects.assert_called_once_with(decoded_token)
    handler._auth_state_from_projects.assert_called_once_with(projects, handler.platform)
    handler.auth_to_user.assert_called_once_with({"name": "test_user", "auth_state": auth_state})
    handler.set_login_cookie.assert_called_once_with(user)
    handler.redirect.assert_called_once_with("/home")


@pytest.mark.parametrize(
    "platform, projects",
    [
        pytest.param("portal.example.notebooks.shared", {}, id="empty project claim"),
        pytest.param(
            "portal.example.other.shared",
            {
                "project1": {
                    "name": "Project 1",
                    "resources": [
                        {"name": "portal.example.notebooks.shared", "username": "test_notebook_user.project1"},
                        {"name": "portal.example.clusters.shared", "username": "test_cluster_user.project1"},
                    ],
                },
                "project2": {
                    "name": "Project 2",
                    "resources": [
                        {"name": "portal.example.notebooks.shared", "username": "test_notebook_user.project2"}
                    ],
                },
            },
            id="no projects with resource name matching platform",
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_no_valid_projects_exception(handler, platform: str, projects: dict[str, dict]):
    handler.platform = platform

    # Mock all methods up until a the token is decoded
    handler._extract_token = MagicMock()
    handler._fetch_oidc_config = AsyncMock()
    handler._parse_oidc_config = MagicMock(return_value=(MagicMock, MagicMock))
    handler._fetch_signing_key = MagicMock()

    decoded_token = {
        "aud": "zenith-jupyter",
        "exp": 12345,
        "iss": "https://example.com",
        "iat": 12344,
        "short_name": "user",
        "projects": projects,
    }

    # Mock the JWT decoding function and its return value
    handler._decode_jwt = MagicMock(return_value=decoded_token)

    with pytest.raises(HTTPError, match="No projects with valid platform") as exc_info:
        await handler.get()

    assert exc_info.value.status_code == 403


def test_get_handlers():
    # Create an instance of BricsAuthenticator
    authenticator = BricsAuthenticator()

    # Mock the app object
    app = MagicMock()

    # Call get_handlers and assert the result
    handlers = authenticator.get_handlers(app)
    assert len(handlers) == 1
    assert handlers[0][0] == r"/login"
    assert handlers[0][1] == BricsLoginHandler
    assert handlers[0][2]["oidc_server"] == authenticator.oidc_server
    assert handlers[0][2]["platform"] == authenticator.brics_platform
    assert handlers[0][2]["jwt_audience"] == authenticator.jwt_audience
    assert handlers[0][2]["jwt_leeway"] == authenticator.jwt_leeway


@pytest.mark.parametrize(
    "decoded_token, expected_output",
    [
        # dict[str, dict] should be passed through unchanged
        pytest.param(
            {
                "projects": {
                    "brics.brics": {
                        "name": "BriCS Technical Staff",
                        "resources": [
                            {"name": "brics.aip1.notebooks.shared", "username": "isambardfun.brics"},
                            {"name": "brics.aip1.clusters.shared", "username": "isambardfun.brics"},
                        ],
                    }
                }
            },
            {
                "brics.brics": {
                    "name": "BriCS Technical Staff",
                    "resources": [
                        {"name": "brics.aip1.notebooks.shared", "username": "isambardfun.brics"},
                        {"name": "brics.aip1.clusters.shared", "username": "isambardfun.brics"},
                    ],
                }
            },
            id="dict[str, dict] - unchanged",
        ),
        # dict[str, str] with JSON-encoded str should be decoded to dict[str, dict]
        pytest.param(
            {
                "projects": json.dumps(
                    {
                        "benchmarking.portal": {
                            "resources": [
                                {"name": "benchmarking.aip1.notebooks", "username": "user1"},
                                {"name": "benchmarking.i3.cluster", "username": "user2"},
                            ]
                        }
                    }
                )
            },
            {
                "benchmarking.portal": {
                    "resources": [
                        {"name": "benchmarking.aip1.notebooks", "username": "user1"},
                        {"name": "benchmarking.i3.cluster", "username": "user2"},
                    ]
                }
            },
            id="dict[str, str] JSON string - decode",
        ),
        # Invalid JSON should return an empty dict
        pytest.param({"projects": "{invalid_json"}, {}, id="Invalid JSON - return empty"),
        # Nested JSON string
        pytest.param(
            {"projects": json.dumps({"nested_project": {"resources": [{"name": "test.resource"}]}})},
            {"nested_project": {"resources": [{"name": "test.resource"}]}},
            id="Nested JSON string - decode",
        ),
        # Empty `projects` dict should return empty
        pytest.param({"projects": {}}, {}, id="Empty projects - return empty"),
        # Null `projects` value should return empty
        pytest.param({"projects": None}, {}, id="Projects None - return empty"),
        # JSON-encoded list (invalid case)
        pytest.param({"projects": json.dumps([{"name": "test.resource"}])}, {}, id="JSON encoded list - invalid case"),
    ],
)
def test_normalize_projects(handler, decoded_token, expected_output):
    """
    Test the _normalize_projects function to ensure it interprets
    different input correctly
    """
    result = handler._normalize_projects(decoded_token)
    assert result == expected_output


@pytest.mark.parametrize(
    "leeway_seconds, delta_seconds, with_leeway_cm",
    [
        pytest.param(5, 1, nullcontext(), id="5s leeway, 2s delta"),
        pytest.param(5, 3, nullcontext(), id="5s leeway, 3s delta"),
        pytest.param(5, 5, nullcontext(), id="5s leeway, 5s delta"),
        pytest.param(
            5, 6, pytest.raises(HTTPError, match=r"The token is not yet valid \(iat\)"), id="5s leeway, 6s delta"
        ),
        pytest.param(3.5, 1, nullcontext(), id="3.5s leeway, 1s delta"),
        pytest.param(
            3.5, 4, pytest.raises(HTTPError, match=r"The token is not yet valid \(iat\)"), id="3.5s leeway, 4s delta"
        ),
    ],
)
def test_jwt_iat_validation_with_leeway(
    freezer, handler, leeway_seconds: int | float, delta_seconds: int, with_leeway_cm: AbstractContextManager
):
    """
    Check that JWTs with iat less than or equal to current time + leeway are valid
    """

    signing_key = MagicMock(spec=jwt.PyJWK)
    signing_key.key = "test-secret"
    algorithm = "HS256"

    # Freeze time to so that there is zero time between token setup and validation
    # Set microsecond=0 to ensure that there are no rounding errors from using
    # integer iat and exp claims
    frozen_time = datetime.datetime.now().replace(microsecond=0)
    freezer.move_to(frozen_time)

    # Simulate a token with delta seconds in the future
    iat_adjusted = int(time.time() + delta_seconds)

    # ... that expires 5 minutes after it is issued
    exp = int(iat_adjusted + timedelta(minutes=5).total_seconds())

    payload = {
        "iat": iat_adjusted,
        "exp": exp,
        "aud": handler.jwt_audience,
        "iss": handler.oidc_server,
        "short_name": "testuser",
        "projects": {
            "project1.portal": {
                "name": "Project 1",
                "resources": [{"name": "portal.example.other.shared", "username": "test_user.project1"}],
            }
        },
    }

    token = jwt.encode(payload, signing_key.key, algorithm=algorithm)

    # Without leeway, this should fail
    with pytest.raises(HTTPError, match=r"The token is not yet valid \(iat\)") as exc_info:
        handler.jwt_leeway = 0
        _ = handler._decode_jwt(token, signing_key, [algorithm])

    assert exc_info.value.status_code == 401

    # With leeway, it should succeed if not delta_seconds > leeway_seconds
    with with_leeway_cm:
        handler.jwt_leeway = leeway_seconds
        decoded = handler._decode_jwt(token, signing_key, [algorithm])
        assert decoded == payload


@pytest.mark.parametrize(
    "leeway_seconds, delta_seconds, with_leeway_cm",
    [
        pytest.param(5, 1, nullcontext(), id="5s leeway, 2s delta"),
        pytest.param(5, 3, nullcontext(), id="5s leeway, 3s delta"),
        pytest.param(5, 5, pytest.raises(HTTPError, match=r"Signature has expired"), id="5s leeway, 5s delta"),
        pytest.param(5, 6, pytest.raises(HTTPError, match=r"Signature has expired"), id="5s leeway, 6s delta"),
        pytest.param(3.5, 1, nullcontext(), id="3.5s leeway, 1s delta"),
        pytest.param(3.5, 4, pytest.raises(HTTPError, match=r"Signature has expired"), id="3.5s leeway, 4s delta"),
    ],
)
def test_jwt_exp_validation_with_leeway(
    freezer, handler, leeway_seconds: int | float, delta_seconds: int, with_leeway_cm: AbstractContextManager
):
    """
    Check that JWTs with exp greater than current time - leeway are valid
    """

    signing_key = MagicMock(spec=jwt.PyJWK)
    signing_key.key = "test-secret"
    algorithm = "HS256"

    # Freeze time to so that there is zero time between token setup and validation
    # Set microsecond=0 to ensure that there are no rounding errors from using
    # integer iat and exp claims
    frozen_time = datetime.datetime.now().replace(microsecond=0)
    freezer.move_to(frozen_time)

    # Simulate a token with iat 5 minutes + delta_seconds in the past
    iat = int(time.time() - timedelta(minutes=5).total_seconds() - delta_seconds)

    # ... that expires 5 minutes after it is issued and delta_seconds before now
    exp = int(time.time() - delta_seconds)

    payload = {
        "iat": iat,
        "exp": exp,
        "aud": handler.jwt_audience,
        "iss": handler.oidc_server,
        "short_name": "testuser",
        "projects": {
            "project1.portal": {
                "name": "Project 1",
                "resources": [{"name": "portal.example.other.shared", "username": "test_user.project1"}],
            }
        },
    }

    token = jwt.encode(payload, signing_key.key, algorithm=algorithm)

    # Without leeway, this should fail
    with pytest.raises(HTTPError, match=r"Signature has expired") as exc_info:
        handler.jwt_leeway = 0
        _ = handler._decode_jwt(token, signing_key, [algorithm])

    assert exc_info.value.status_code == 401

    # With leeway, it should succeed if not delta_seconds >= leeway_seconds
    with with_leeway_cm:
        handler.jwt_leeway = leeway_seconds
        decoded = handler._decode_jwt(token, signing_key, [algorithm])
        assert decoded == payload
