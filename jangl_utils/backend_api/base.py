import logging
import requests

from django.utils import six
from requests import HTTPError
from rest_framework.exceptions import APIException
from jangl_utils import json as json_utils, logger, settings
from jangl_utils.backend_api.utils import get_service_url


class BackendAPISession(requests.Session):
    def __init__(self):
        super(BackendAPISession, self).__init__()
        self.hooks.setdefault('response', []).append(json_utils.decode_json_response_hook)

    @property
    def session_cid(self):
        return self.headers.get(settings.CID_HEADER_NAME)

    def request(self, method, url, params=None, data=None, headers=None, cookies=None, files=None, auth=None,
                timeout=None, allow_redirects=True, proxies=None, hooks=None, stream=None, verify=None, cert=None,
                json=None, **kwargs):
        site_id = kwargs.pop('site_id', None)
        force_json = kwargs.pop('force_json', True)
        raise_on_exception = kwargs.pop('raise_on_exception', True)
        raise_to_front = kwargs.pop('raise_to_front', True)
        return_json = kwargs.pop('return_json', True)

        if isinstance(url, (tuple, list)):
            url = get_service_url(url[0], *url[1:], **kwargs)
        if data:
            if isinstance(data, six.text_type):
                data = data.encode('utf-8')
            elif force_json and not isinstance(data, six.string_types):
                data = json_utils.to_json(data)

        if site_id is not None:
            headers = headers or {}
            headers[settings.SITE_ID_HEADER_NAME] = str(site_id)

        self._log('request', method.upper(), url)
        self._debug(data)

        response = super(BackendAPISession, self).request(
            method,
            url,
            params=params,
            data=data,
            headers=headers,
            cookies=cookies,
            files=files,
            auth=auth,
            timeout=timeout,
            allow_redirects=allow_redirects,
            proxies=proxies,
            hooks=hooks,
            stream=stream,
            verify=verify,
            cert=cert,
            json=json,
        )

        self._log('response', response.status_code, response.url)
        if not stream:
            self._debug(response.text)

        if raise_on_exception:
            try:
                response.raise_for_status()
            except HTTPError:
                if raise_to_front:
                    raise APIException(response.text, response.reason)
                raise

        if return_json:
            return response.json()

        return response

    def update_session_headers(self, cid=None, site_id=None, host=None, authorization=None,
                               api_token=None, account=None, twilio_signature=None, cookies=None):
        if cid:
            self.headers[settings.CID_HEADER_NAME] = str(cid)

        if site_id:
            self.headers[settings.SITE_ID_HEADER_NAME] = str(site_id)
        elif host:
            self.headers['Host'] = str(host)

        if authorization:
            self.headers['Authorization'] = authorization
        elif api_token:
            if isinstance(api_token, dict):
                auth = '{0} {1}'.format('Bearer', api_token['access_token'])
            else:
                auth = '{0} {1}'.format('JWT', api_token)
            self.headers['Authorization'] = auth

        if account:
            self.headers['X-Auth-Account'] = account

        if twilio_signature:
            self.headers['X-Twilio-Signature'] = twilio_signature

        if cookies:
            requests.utils.add_dict_to_cookiejar(self.cookies, cookies)

    def _log(self, log_type, *args):
        cid = '[{}] '.format(self.session_cid) if self.session_cid else ''
        logger.info('{}API {} - {}'.format(cid, log_type.upper(), ' '.join(map(str, args))))

    def _debug(self, data):
        if data:
            log_level = getattr(logging, settings.BACKEND_API_VERBOSE_LOG_LEVEL)
            logger.log(log_level, data)

