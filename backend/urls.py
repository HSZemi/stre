from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.dashboard, name='dashboard'),
    url(r'^login$', views.loginpage, name='loginpagebackend'),
    url(r'^antraege/(?P<semester_id>[0-9]+)$', views.antraege, name='antraege'),
    url(r'^antraege/(?P<semester_id>[0-9]+)/status/(?P<status_id>[0-9]+)$', views.antraege, name='antraege'),
    url(r'^antrag/(?P<antrag_id>[0-9]+)$', views.antrag, name='antragbackend'),
    url(r'^antrag/(?P<antrag_id>[0-9]+)/aktion/(?P<aktion_id>[0-9]+)$', views.antragaktion, name='antragaktion'),
    url(r'^antrag/(?P<antrag_id>[0-9]+)/aktion/(?P<aktion_id>[0-9]+)/(?P<brief_id>[0-9]+)$', views.antragaktion, name='antragaktion'),
    url(r'^antrag/(?P<antrag_id>[0-9]+)/brief/(?P<briefvorlage_id>[0-9]+)', views.brief, name='brieferstellen'),
    url(r'^history$', views.history, name='history'),
    url(r'^history/(?P<antrag_id>[0-9]+)$', views.history, name='history'),
    url(r'^undo/(?P<history_id>[0-9]+)$', views.undo, name='undo'),
    url(r'^konfiguration$', views.konfiguration, name='konfiguration'),
]