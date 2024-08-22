"""
JupyterHub `Authenticator` for the BriCS JupyterHub service
"""

import json

import jwt
from jupyterhub.auth import Authenticator
from jupyterhub.handlers import BaseHandler
from tornado import web


class BricsLoginHandler(BaseHandler):
    async def get(self):
        # Retrieve the JWT token from the headers
        token = self.request.headers.get("X-Auth-Id-Token")
        if not token:
            raise web.HTTPError(401, "Missing X-Auth-Id-Token header")

        # TODO Verify signature of JWT token
        try:
            # Decode the JWT token without verifying the signature
            decoded_token = jwt.decode(token, options={"verify_signature": False}, algorithms=["RS256"])

            # Print all key-value pairs in the JWT token (optional for debugging)
            print("Decoded JWT Token:")
            for key, value in decoded_token.items():
                print(f"{key}: {value}")

            # Extract the username (or other unique identifier) from the token
            username = decoded_token.get("short_name")
            if not username:
                raise web.HTTPError(401, "Invalid token: Missing short_name claim")

            projects = decoded_token.get("projects")

            # TODO Only allow authentication if any project has access to Jupyter
            #  by inspecting the resources allocated to each project

            # Authenticate the user with JupyterHub
            # user = self.user_from_username(username)
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
