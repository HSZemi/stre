from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^registrierung$', views.registrierung, name='registrierung'),
    url(r'^login$', views.loginpage, name='loginpage'),
    url(r'^login/reset$', views.resetpassword, name='resetpassword'),
    url(r'^login/reset_confirm/(?P<uidb64>[0-9A-Za-z]+)/(?P<token>.+)/$', views.resetpasswordconfirm, name='resetpasswordconfirm'),
    url(r'^logout$', views.logoutpage, name='logout'),
    url(r'^info$', views.info, name='info'),
    url(r'^rechner$', views.rechner, name='rechner'),
    url(r'^impressum', views.impressum, name='impressum'),
    url(r'^datenschutz', views.datenschutz, name='datenschutz'),
    url(r'^antragstellung/(?P<semester_id>[0-9]+)$', views.antragstellung, name='antragstellung'),
    url(r'^antrag/(?P<antrag_id>[0-9]+)$', views.antrag, name='antrag'),
    url(r'^antrag/(?P<antrag_id>[0-9]+)/zurueckziehen$', views.antragzurueckziehen, name='antragzurueckziehen'),
    url(r'^account$', views.account, name='account'),
]