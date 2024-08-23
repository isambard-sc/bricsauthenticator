"""
JupyterHub `Authenticator` for the BriCS JupyterHub service
"""

import json

import jwt
from jupyterhub.auth import Authenticator
from jupyterhub.handlers import BaseHandler
from tornado import web
from tornado.httpclient import AsyncHTTPClient


class BricsLoginHandler(BaseHandler):
    async def get(self):
        # Retrieve the JWT token from the headers
        token = self.request.headers.get("X-Auth-Id-Token")
        if not token:
            raise web.HTTPError(401, "Missing X-Auth-Id-Token header")

        # Log raw JWT token prior to decoding (optional for debugging)
        self.log.debug(f"Raw JWT Token: {token}")

        oidc_server = "https://keycloak.isambard.ac.uk/realms/isambard"  # Hard-code to ensure it's a place we trust

        http_client = AsyncHTTPClient()
        try:
            response = await http_client.fetch(request=f"{oidc_server}/.well-known/openid-configuration", method="GET")
        except Exception as e:
            self.log.exception(f"Encountered exception when fetching OIDC server config")
            raise web.HTTPError(500) from e

        oidc_config = json.loads(response.body)
        signing_algos = oidc_config["id_token_signing_alg_values_supported"]

        # A 'User-Agent' header is required, otherwise the oidc_server returns HTTP 403 forbidden
        jwks_client = jwt.PyJWKClient(oidc_config["jwks_uri"], headers={"User-Agent": f"PyJWT/{jwt.__version__}"})
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        try:
            # Decode the JWT token and verify
            # Verifies signature and values of audience (aud), issuer (iss),
            # expiry (exp), and issued at (iat) claims
            # Verifies presence of short_name and projects claims (used in JupyterHub)
            decoded_token = jwt.decode(
                token,
                key=signing_key.key,
                algorithms=signing_algos,
                options={
                    "verify_signature": True,
                    "require": ["aud", "exp", "iss", "iat", "short_name", "projects"],
                },
                audience="zenith-jupyter",
                issuer=oidc_server,
            )

            # Log all key-value pairs in the JWT token (optional for debugging)
            self.log.debug(
                "Decoded JWT Token:\n" + "\n".join(f"{key}: {value}" for key, value in decoded_token.items())
            )

            # Extract the username (or other unique identifier) from the token
            username = decoded_token.get("short_name")
            if not username:
                raise web.HTTPError(401, "Invalid token: Missing short_name claim")

            projects = decoded_token.get("projects")

            # TODO Only allow authentication if any project has access to Jupyter
            #  by inspecting the resources allocated to each project

            # Authenticate the user with JupyterHub
            user = await self.auth_to_user({"name": username, "auth_state": projects})
            self.set_login_cookie(user)
            next_url = self.get_next_url(user)
            self.redirect(next_url)

        except jwt.InvalidTokenError as e:
            raise web.HTTPError(401, f"Invalid JWT token: {str(e)}")


class BricsAuthenticator(Authenticator):
    def get_handlers(self, app):
        return [(r"/login", BricsLoginHandler)]

    async def authenticate(self, *args, **kwargs):
        raise NotImplementedError("This method should not be called directly.")
