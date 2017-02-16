
DEFAULT_FORMAT_STRING = '%(log_color)s%(levelname)-8s %(asctime)s%(reset)s | %(message)s'


def generate_colorlog_settings(project_name, verbose=False, extra_packages=(),
                               format_string=None, use_color=False,
                               project_level='INFO', extra_level='WARNING',
                               verbose_project_level='DEBUG', verbose_extra_level='INFO'):
    if verbose:
        project_level = verbose_project_level
        extra_level = verbose_extra_level

    def extra_with_level(extra):
        try:
            package, level = extra
        except (ValueError, TypeError):
            package = extra
            level = extra_level
        return package, level

    packages = [(project_name, project_level), ('jangl_utils', extra_level)]
    packages += [extra_with_level(package) for package in extra_packages]

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
            }
        },
        'loggers': {
            name: {'handlers': ['console'], 'level': level} for name, level in packages
        },
    }
