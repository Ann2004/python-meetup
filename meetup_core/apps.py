from django.apps import AppConfig


class MeetupCoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'meetup_core'


    def ready(self):
        import meetup_core.signals
