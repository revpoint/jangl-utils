import json
from django.core.exceptions import ValidationError


class JWTAuthBackend(object):
    def authenticate(self, request, email=None, password=None, raise_validation=False, **kwargs):
        login_request = request.backend_api.post(('accounts', 'login'),
                                                 json.dumps({'email': email, 'password': password}))

        if login_request.ok:
            token = login_request.json().get('token')
            return token

        if raise_validation and login_request.status_code == 400:
            error = login_request.json().values()[0]
            raise ValidationError(error)
