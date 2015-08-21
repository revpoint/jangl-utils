from django.apps import AppConfig


class WorkersConfig(AppConfig):
    name = 'jangl_utils.workers'

    def ready(self):
        pass
