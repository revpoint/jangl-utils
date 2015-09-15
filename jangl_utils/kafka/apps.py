from django.apps import AppConfig
from jangl_utils.kafka.registry import autodiscover


class KafkaConfig(AppConfig):
    name = 'jangl_utils.kafka'

    def ready(self):
        autodiscover()
