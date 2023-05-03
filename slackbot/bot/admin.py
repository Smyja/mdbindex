from django.contrib import admin

from .models import SlackBot, SlackInstallation

# Register your models here.


admin.site.register(SlackBot)
admin.site.register(SlackInstallation)
