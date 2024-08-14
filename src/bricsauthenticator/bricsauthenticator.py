"""
JupyterHub `Authenticator` for the BriCS JupyterHub service
"""

from tornado.web import HTTPError
from jupyterhub.auth import Authenticator

class BricsAuthenticator(Authenticator):
    """
    TODO docstring
    """

    async def authenticate(self, handler, data):
        """
        TODO docstring
        TODO type hints
        """

        raise HTTPError(status_code=418, log_message="Authenticator not implemented")

