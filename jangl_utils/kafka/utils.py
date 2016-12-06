import logging

logger = logging.getLogger(__name__)


def generate_client_settings(initial_settings, user_settings):
    settings = initial_settings.copy()
    for key, val in user_settings.iteritems():
        if val is None:
            continue
        if '.' not in key:
            continue
        logger.debug('using kafka setting {}: {}'.format(key, val))
        if key.startswith('topic.'):
            settings['default.topic.config'][key[6:]] = val
        else:
            settings[key] = val
    return settings
