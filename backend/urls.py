from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^antraege$', views.antraege, name='antraege'),
    url(r'^antrag/(?P<antrag_id>[0-9]+)$', views.antrag, name='antrag'),
    url(r'^konfiguration$', views.konfiguration, name='konfiguration'),
]