"""
JupyterHub `Authenticator` for the BriCS JupyterHub service
"""

import json

import jwt
from jupyterhub.auth import Authenticator
from jupyterhub.handlers import BaseHandler
from tornado import web
from tornado.httpclient import AsyncHTTPClient
from traitlets import Unicode


class BricsLoginHandler(BaseHandler):
    def initialize(self, oidc_server: str, platform: str, http_client=None, jwks_client_factory=None):
        self.oidc_server = oidc_server
        self.platform = platform
        self.http_client = http_client or AsyncHTTPClient()
        self.jwks_client_factory = jwks_client_factory or self._default_jwks_client_factory

    def _default_jwks_client_factory(self, jwks_uri: str):
        headers = {"User-Agent": f"PyJWT/{jwt.__version__}"}
        return jwt.PyJWKClient(jwks_uri, headers=headers)

    async def get(self):
        token = self._extract_token()

        oidc_config = await self._fetch_oidc_config()
        signing_algos, jwks_uri = self._parse_oidc_config(oidc_config)
        signing_key = self._fetch_signing_key(jwks_uri, token)
        decoded_token = self._decode_jwt(token, signing_key, signing_algos)

        projects = self._normalize_projects(decoded_token)

        username = decoded_token.get("short_name")
        if not username:
            raise web.HTTPError(401, "Invalid token: Missing short_name claim")

        auth_state = self._auth_state_from_projects(projects, self.platform)

        if not len(auth_state) > 0:
            raise web.HTTPError(403, "No projects with valid platform")

        user = await self.auth_to_user({"name": username, "auth_state": auth_state})
        self.set_login_cookie(user)
        next_url = self.get_next_url(user)
        self.redirect(next_url)

    def _extract_token(self) -> str:
        token = self.request.headers.get("X-Auth-Id-Token")
        if not token:
            raise web.HTTPError(401, "Missing X-Auth-Id-Token header")
        self.log.debug(f"Raw JWT Token: {token}")
        return token

    async def _fetch_oidc_config(self) -> dict:
        try:
            self.log.debug(f"Requesting OIDC config from {self.oidc_server}")
            response = await self.http_client.fetch(f"{self.oidc_server}/.well-known/openid-configuration")
            return json.loads(response.body)
        except Exception as e:
            self.log.exception("Failed to fetch OIDC config")
            raise web.HTTPError(500) from e

    def _parse_oidc_config(self, oidc_config: dict):
        signing_algos = oidc_config["id_token_signing_alg_values_supported"]
        jwks_uri = oidc_config["jwks_uri"]
        return signing_algos, jwks_uri

    def _fetch_signing_key(self, jwks_uri: str, token: str):
        jwks_client = self.jwks_client_factory(jwks_uri)
        return jwks_client.get_signing_key_from_jwt(token)

    def _decode_jwt(self, token: str, signing_key, signing_algos: list) -> dict:
        try:
            return jwt.decode(
                token,
                key=signing_key.key,
                algorithms=signing_algos,
                options={
                    "verify_signature": True,
                    "require": ["aud", "exp", "iss", "iat", "short_name", "projects"],
                },
                audience="zenith-jupyter",
                issuer=self.oidc_server,
            )
        except jwt.InvalidTokenError as e:
            raise web.HTTPError(401, f"Invalid JWT token: {str(e)}")

    def _normalize_projects(self, decoded_token: dict) -> dict:
        projects = decoded_token.get("projects")

        if projects is None:
            return {}

        self.log.debug(f"projects claim is of type {type(projects)}")

        # If projects is a JSON string, decode it
        if isinstance(projects, str):
            try:
                projects = json.loads(projects)
                self.log.debug(f"Projects claim JSON decoded: {json.dumps(projects, indent=4)}")
            except json.JSONDecodeError:
                self.log.warning("Invalid projects format: could not decode JSON")
                return {}

        if not isinstance(projects, dict):
            self.log.warning(
                f"Invalid projects format after decoding (expected dict, got {type(projects)}), returning empty"
            )
            return {}
        
        return projects

    def _auth_state_from_projects(self, projects: dict, platform: str) -> dict:
        """
        Transform normalized projects claim to auth_state

        `projects` should be a dict mapping project short names to a dict
        of project data containing a project human name and a list of dicts
        containing information about resources associated with the project, e.g.

        {
          "project1.portal": {
            "name": "Project 1",
            "resources: [
              {
                "name": "portal.example.notebooks.shared",
                "username": "test_user.project1"
              },
              {
                "name": "portal.example.clusters.shared",
                "username": "test_user.project1"
              },
            ]
          },
          "project2.portal": {
            "name": "Project 2",
            "resources: [
              {
                "name": "portal.example.clusters.shared",
                "username": "test_user.project2"
              },
            ]
          }
        }

        The returned auth_state is a transformed version of this claim which
        contains data only for projects where there is at least one resource
        with a name which matches `platform`, e.g. for 
        `platform` == portal.example.notebooks.shared the result is

        {
          "project1.portal": {
            "name": "Project 1",
            "username": "test_user.project1",
          },
        },

        :param projects: "projects" claim from token
        :param platform: platform name to filter projects by
        :return: auth_state for passing to `Spawnerz
        """
        auth_state = dict()
        for project_id, project_data in projects.items():
            for resource in project_data["resources"]:
                if resource["name"] == platform:
                    auth_state[project_id] = {"name": project_data["name"], "username": resource["username"]}
                    break
        return auth_state

class BricsAuthenticator(Authenticator):

    oidc_server = Unicode(
        default_value="https://keycloak.isambard.ac.uk/realms/isambard",
        help="URL for OIDC server used to validate received token",
        allow_none=False,
    ).tag(config=True)

    brics_platform = Unicode(
        default_value="brics.aip1.notebooks.shared",
        help="BriCS platform being authenticated to as it appears in the JWT projects claim",
        allow_none=False,
    ).tag(config=True)

    def get_handlers(self, app):
        return [(r"/login", BricsLoginHandler, {"oidc_server": self.oidc_server, "platform": self.brics_platform})]

    async def authenticate(self, *args, **kwargs):
        raise NotImplementedError("This method should not be called directly.")
