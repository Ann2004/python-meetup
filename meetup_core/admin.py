from django.contrib import admin
from .models import User, Event, SpeakerSpeech, Question, Donation, Subscription

admin.site.register(User)
admin.site.register(Event)
admin.site.register(SpeakerSpeech)
admin.site.register(Question)
admin.site.register(Donation)
admin.site.register(Subscription)
