import sys

DEFAULT_FORMAT_STRING = '%(log_color)s%(levelname)-8s %(asctime)s%(reset)s | %(message)s'


def generate_colorlog_settings(project_name, verbose=False, use_color=False,
                               format_string=None, extra_packages=('jangl_utils',),
                               project_level='INFO', extra_level='WARNING',
                               verbose_project_level='DEBUG', verbose_extra_level='INFO'):
    if verbose:
        project_level = verbose_project_level
        extra_level = verbose_extra_level

    def extra_with_level(extra):
        try:
            pkg_name, level = extra
        except (ValueError, TypeError):
            pkg_name = extra
            level = extra_level
        return pkg_name, level

    packages = [(project_name, project_level)] + [extra_with_level(pkg) for pkg in extra_packages]
    loggers = {name: {'handlers': ['console'], 'level': level} for name, level in packages}
    loggers['output'] = {'handlers': ['output'], 'level': 'INFO'}

    return {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'color': {
                '()': 'colorlog.ColoredFormatter',
                'format': format_string or DEFAULT_FORMAT_STRING
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'color' if use_color else '',
                'level': project_level,
            },
            'output': {
                'class': 'logging.StreamHandler',
                'level': 'INFO',
                'stream': sys.stdout,
            },
        },
        'loggers': loggers,
    }
