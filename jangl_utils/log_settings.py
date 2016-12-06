def generate_colorlog_settings(project_name, verbose=False):
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
                'level': 'DEBUG' if verbose else 'INFO',
            }
        },
        'loggers': {
            project_name: {
                'handlers': ['console'],
                'level': 'DEBUG' if verbose else 'INFO',
            },
            'jangl_utils': {
                'handlers': ['console'],
                'level': 'DEBUG' if verbose else 'WARNING',
            },
        },
    }
