

def generate_colorlog_settings(project_name, verbose=False, extra_packages=None,
                               project_level='INFO', extra_level='WARNING', verbose_level='DEBUG'):
    project_level = verbose_level if verbose else project_level
    extra_level = verbose_level if verbose else extra_level

    packages = [(project_name, project_level), ('jangl_utils', extra_level)]
    if extra_packages is not None:
        packages += [(package, extra_level) for package in extra_packages]

    return {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'color': {
                '()': 'colorlog.ColoredFormatter',
                'format': '%(log_color)s%(levelname)-8s %(name)s - %(message)s'
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'color',
                'level': project_level,
            }
        },
        'loggers': {
            name: {'handlers': ['console'], 'level': level} for name, level in packages
        },
    }
