import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from tornado.web import HTTPError
from tornado.web import Application, HTTPError
from tornado.httputil import HTTPServerRequest
from bricsauthenticator.auth import BricsLoginHandler  
import jwt

@pytest.fixture
def handler():
    # Create a real Application instance with necessary settings
    application = Application()
    application.settings = {
        'hub': MagicMock(base_url="/hub/"),  # Mock 'hub' with base_url as a string
        'cookie_secret': b'secret',  # Add other required settings
        'log_function': MagicMock(),  # Mock the application-level logger
    }
    
    # Mock request with a connection attribute
    request = MagicMock(spec=HTTPServerRequest)
    request.connection = MagicMock()  # Add the 'connection' attribute
    
    # Initialize BricsLoginHandler with the mocked application, request, and required arguments
    handler_instance = BricsLoginHandler(application, request, oidc_server="https://example.com")
    handler_instance.http_client = AsyncMock()
    handler_instance.jwks_client_factory = MagicMock()
    return handler_instance


def test_extract_token_missing_header(handler):
    handler.request.headers = {}
    with pytest.raises(HTTPError) as exc_info:
        handler._extract_token()
    assert exc_info.value.status_code == 401
    assert "Missing X-Auth-Id-Token header" in str(exc_info.value)

def test_extract_token_success(handler):
    handler.request.headers = {"X-Auth-Id-Token": "fake_token"}
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
    oidc_config = {
        "id_token_signing_alg_values_supported": ["RS256"],
        "jwks_uri": "https://example.com/jwks_uri"
    }
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
    decoded_token = {"aud": "zenith-jupyter", "exp": 12345, "iss": "https://example.com", "iat": 12344, "short_name": "user", "projects": {}}
    mock_signing_key = MagicMock()
    mock_signing_key.key = "fake_key"

    with patch("jwt.decode", return_value=decoded_token):
        result = handler._decode_jwt(
            "fake_token",
            mock_signing_key,
            ["RS256"]
        )
        assert result == decoded_token

def test_decode_jwt_failure(handler):
    mock_signing_key = MagicMock()
    mock_signing_key.key = "fake_key"

    with patch("jwt.decode", side_effect=jwt.InvalidTokenError("Invalid token")):
        with pytest.raises(HTTPError) as exc_info:
            handler._decode_jwt("fake_token", mock_signing_key, ["RS256"])
        assert exc_info.value.status_code == 401

def test_normalize_projects_valid_json(handler):
    decoded_token = {"projects": '{"project1": "value1"}'}
    result = handler._normalize_projects(decoded_token)
    assert result == {"project1": "value1"}

def test_normalize_projects_invalid_json(handler):
    decoded_token = {"projects": "invalid_json"}
    result = handler._normalize_projects(decoded_token)
    assert result == "invalid_json"

def test_normalize_projects_none(handler):
    decoded_token = {}
    result = handler._normalize_projects(decoded_token)
    assert result == {}
