from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^(?P<dokument_id>[0-9]+)$', views.datei, name='datei'),
]