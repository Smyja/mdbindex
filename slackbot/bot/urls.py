from django.http import HttpRequest
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from slack_bolt.adapter.django import SlackRequestHandler

from bot import views

from .slack_listeners import app

handler = SlackRequestHandler(app=app)


@csrf_exempt
def slack_events_handler(request: HttpRequest):
    return handler.handle(request)


def slack_oauth_handler(request: HttpRequest):
    return handler.handle(request)


urlpatterns = [
    path("", views.index, name="index"),
    path("slack/events", slack_events_handler, name="handle"),
    path("slack/install", slack_oauth_handler, name="install"),
    path("slack/oauth_redirect", slack_oauth_handler, name="oauth_redirect"),
    path("api/v1/upload", views.upload_file, name="upload_file"),
    path("api/v1/ask", views.ask_bot, name="ask_bot"),
    path("api/v1/askkk", views.generate_names, name="generate_names"),
    # path("api/v1/askk", views.test_stream, name="teststream")
]
