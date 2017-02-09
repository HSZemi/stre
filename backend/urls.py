from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.dashboard, name='dashboard'),
    url(r'^login$', views.loginpage, name='loginpage'),
    url(r'^reset$', views.resetpassword, name='resetpassword'),
    url(r'^antraege/(?P<semester_id>[0-9]+)$', views.antraege, name='antraege'),
    url(r'^antraege/(?P<semester_id>[0-9]+)/status/(?P<status_id>[0-9]+)$', views.antraege, name='antraege'),
    url(r'^antraege/(?P<semester_id>[0-9]+)/bulk_als_ueberwiesen_markieren$', views.bulk_als_ueberwiesen_markieren, name='bulk_als_ueberwiesen_markieren'),
    url(r'^antrag/(?P<antrag_id>[0-9]+)$', views.antrag, name='antrag'),
    url(r'^antrag/(?P<antrag_id>[0-9]+)/edit$', views.antrag_bearbeiten, name='antrag_bearbeiten'),
    url(r'^antrag/(?P<antrag_id>[0-9]+)/aktion/(?P<aktion_id>[0-9]+)$', views.antragaktion, name='antragaktion'),
    url(r'^antrag/(?P<antrag_id>[0-9]+)/aktion/(?P<aktion_id>[0-9]+)/(?P<brief_id>[0-9]+)$', views.antragaktion, name='antragaktion'),
    url(r'^antrag/(?P<antrag_id>[0-9]+)/brief/(?P<briefvorlage_id>[0-9]+)$', views.brief, name='brieferstellen'),
    url(r'^account/(?P<person_id>[0-9]+)$', views.account, name='account'),
    url(r'^account/(?P<person_id>[0-9]+)/edit$', views.account_bearbeiten, name='account_bearbeiten'),
    url(r'^history$', views.history, name='history'),
    url(r'^history/page/(?P<page_id>[0-9]+)$', views.history, name='history'),
    url(r'^history/(?P<antrag_id>[0-9]+)$', views.history, name='history'),
    url(r'^history/(?P<antrag_id>[0-9]+)/page/(?P<page_id>[0-9]+)$', views.history, name='history'),
    url(r'^adminhistory$', views.adminhistory, name='adminhistory'),
    url(r'^adminhistory/page/(?P<page_id>[0-9]+)$', views.adminhistory, name='adminhistory'),
    url(r'^accounthistory$', views.accounthistory, name='accounthistory'),
    url(r'^accounthistory/page/(?P<page_id>[0-9]+)$', views.accounthistory, name='accounthistory'),
    url(r'^adminhistory/(?P<page_id>[0-9]+)$', views.adminhistory, name='adminhistory'),
    url(r'^accounthistory/(?P<user_id>[0-9]+)$', views.accounthistory, name='accounthistory'),
    url(r'^accounthistory/(?P<user_id>[0-9]+)/page/(?P<page_id>[0-9]+)$', views.accounthistory, name='accounthistory'),
    url(r'^undo/(?P<history_id>[0-9]+)$', views.undo, name='undo'),
    url(r'^konfiguration$', views.konfiguration, name='konfiguration'),
    url(r'^markieren/(?P<dokument_id>[0-9]+)/(?P<markierung>[a-z-]+)$', views.markieren, name='markieren'),
    url(r'^suche/$', views.suche, name='suche'),
    url(r'^suche/(?P<suchbegriff>.+)$', views.suche, name='suche'),
    url(r'^tools/$', views.tools, name='tools'),
]