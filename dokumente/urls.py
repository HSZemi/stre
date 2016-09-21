from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^dokument/(?P<dokument_id>[0-9]+)$', views.datei, name='datei'),
    url(r'^brief/(?P<brief_id>[0-9]+)$', views.brief, name='brief'),
    url(r'^export/ueberweisung/(?P<semester_id>[0-9]+)$', views.export_ueberweisung, name='export_ueberweisung'),
]