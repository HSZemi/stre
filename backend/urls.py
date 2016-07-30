from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.dashboard, name='dashboard'),
    url(r'^login$', views.loginpage, name='loginpagebackend'),
    url(r'^antraege/(?P<semester_id>[0-9]+)$', views.antraege, name='antraege'),
    url(r'^antrag/(?P<antrag_id>[0-9]+)$', views.antrag, name='antragbackend'),
    url(r'^konfiguration$', views.konfiguration, name='konfiguration'),
]