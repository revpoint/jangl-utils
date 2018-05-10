from time import time

from oauthlib.oauth2 import BackendApplicationClient, FatalClientError
from requests import codes
from requests_oauthlib import OAuth2Session


TOKEN_EXPIRES_SOON = 300


class HydraException(Exception):
    def __init__(self, response, message=None, **kwargs):
        self.response = response
        message = message or str(response)
        super(HydraException, self).__init__(message, **kwargs)


def _expires_soon(token):
    return token['expires_at'] - TOKEN_EXPIRES_SOON <= time()


class Hydra:
    def __init__(self, client_id, client_secret, client_scope, endpoint_url):
        self.client_id = client_id
        self.client_secret = client_secret
        self.client_scope = client_scope
        self.endpoint_url = endpoint_url.rstrip('/')

    def __repr__(self):
        return '<Hydra: {self.client_id}>'.format(self=self)

    def __getattr__(self, item):
        if item.startswith('_'):
            raise AttributeError
        return getattr(self.backend_client, item)

    def __getitem__(self, item):
        return self.open_id_config[item]

    def get_url(self, url, **kwargs):
        return self.endpoint_url + url.format(self=self, **kwargs)

    @property
    def backend_client(self):
        if (not hasattr(self, '_backend_client') or
                _expires_soon(self._backend_client.token)):
            self._backend_client = self.get_backend_client_session()
        return self._backend_client

    @property
    def open_id_config(self):
        if not hasattr(self, '_open_id_config'):
            self._open_id_config = self.get_open_id_config()
        return self._open_id_config

    def get_backend_client_session(self):
        client = BackendApplicationClient(client_id=self.client_id)
        session = OAuth2Session(client=client, scope=self.client_scope)
        session.fetch_token(
            self.get_url('/oauth2/token'),
            client_id=self.client_id,
            client_secret=self.client_secret,
            scope=self.client_scope,
        )
        return session

    def get_open_id_config(self):
        url = self.get_url('/.well-known/openid-configuration')
        response = self.get(url)
        if response.ok:
            return response.json()

    def get_user_session(self, token, token_updater=None, **kwargs):
        refresh_url = self.get_url('/oauth2/token')
        refresh_kwargs = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }
        return OAuth2Session(
            self.client_id,
            token=token,
            auto_refresh_url=refresh_url,
            auto_refresh_kwargs=refresh_kwargs,
            token_updater=token_updater,
            **kwargs
        )

    def get_auth_url(self, scope, **kwargs):
        oauth = OAuth2Session(self.client_id, scope=scope)
        auth_url, state = oauth.authorization_url(
            self.get_url('/oauth2/auth'),
            **kwargs
        )
        return auth_url, state

    def get_consent_request(self, consent_id):
        url = self.get_url('/oauth2/consent/requests/{consent_id}', consent_id=consent_id)
        response = self.get(url)
        if response.ok:
            return response.json()

    def accept_consent_request(self, consent_id, subject, grant_scopes,
                               access_token_extra, id_token_extra):
        url = self.get_url('/oauth2/consent/requests/{consent_id}/accept', consent_id=consent_id)
        data = {
            'subject': subject,
            'grantScopes': grant_scopes,
            'accessTokenExtra': access_token_extra,
            'idTokenExtra': id_token_extra,
        }
        response = self.patch(url, json=data)
        if response.status_code != codes.NO_CONTENT:
            raise HydraException(response.json())

    def reject_consent_request(self, consent_id, reason):
        url = self.get_url('/oauth2/consent/requests/{consent_id}/reject', consent_id=consent_id)
        data = {'reason': reason}
        response = self.patch(url, json=data)
        if response.status_code != codes.NO_CONTENT:
            raise HydraException(response.json())

    def get_client_info(self, client_id):
        url = self.get_url('/clients/{client_id}', client_id=client_id)
        response = self.get(url)
        if response.ok:
            return response.json()

    def exchange_code(self, code):
        session = OAuth2Session(self.client_id)
        return session.fetch_token(
            self.get_url('/oauth2/token'),
            code=code,
            client_secret=self.client_secret,
        )

    def refresh_token(self, token):
        session = OAuth2Session(self.client_id, token=token)
        try:
            return session.refresh_token(
                self.get_url('/oauth2/token'),
                client_id=self.client_id,
                client_secret=self.client_secret,
            )
        except FatalClientError:
            pass

    def introspect_token(self, token):
        url = self.get_url('/oauth2/introspect')
        data = {'token': token['access_token']}
        response = self.post(url, data)
        if response.ok:
            return response.json()

    def get_user_info(self, token, token_updater=None):
        session = self.get_user_session(token, token_updater)
        url = self.get_url('/userinfo')
        response = session.post(url)
        if response.ok:
            return response.json()
