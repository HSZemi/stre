from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^register$', views.register, name='register'),
    url(r'^login$', views.loginpage, name='loginpage'),
    url(r'^login/reset$', views.resetpassword, name='resetpassword'),
    url(r'^info$', views.info, name='info'),
    url(r'^status$', views.status, name='status'),
]