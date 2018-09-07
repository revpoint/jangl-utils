from requests.adapters import HTTPAdapter
from urllib3 import Retry
from jangl_utils import settings, VERSION
from jangl_utils.backend_api import old
from jangl_utils.backend_api.base import BackendAPISession
from jangl_utils.backend_api.cached import CachedBackendAPISession, can_use_cache
from jangl_utils.backend_api.utils import get_service_url


__all__ = ['get_backend_api_session', 'get_service_url', 'BackendAPISession', 'CachedBackendAPISession']


BACKEND_USER_AGENT = 'JanglBackendAPI/{}'.format(VERSION)
BACKEND_CONTENT_TYPE = 'application/json'

MAX_ASYNC_POOLS = 50
MAX_ASYNC_POOL_CONNECTIONS = 30
MAX_RETRIES = Retry(3, backoff_factor=0.25)


def get_backend_api_session(cached=settings.ENABLE_BACKEND_API_CACHE and can_use_cache(),
                            use_new=settings.USE_NEW_BACKEND_API, **kwargs):
    if use_new:
        api_session = CachedBackendAPISession() if cached else BackendAPISession()
    else:
        api_session = old.CachedBackendAPISession() if cached else old.BackendAPISession()

    adapter = HTTPAdapter(pool_connections=kwargs.pop('max_async_pools', MAX_ASYNC_POOLS),
                          pool_maxsize=kwargs.pop('max_async_pool_connections', MAX_ASYNC_POOL_CONNECTIONS),
                          max_retries=kwargs.pop('max_retries', MAX_RETRIES))
    api_session.mount('http://', adapter)
    api_session.mount('https://', adapter)
    api_session.headers.update({
        'Content-Type': kwargs.pop('backend_content_type', BACKEND_CONTENT_TYPE),
        'User-Agent': kwargs.pop('backend_user_agent', BACKEND_USER_AGENT),
    })
    api_session.update_session_headers(**kwargs)
    return api_session
