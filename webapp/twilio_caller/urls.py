from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'call$', views.call, name='call'),
    url(r'^record_callback/([0-9]+)$', views.record_callback,
        name='record_callback'),
    url(r'^connect/([0-9]+)$', views.connect, name='connect_endpoint'),
    url(r'^status/([0-9]+)$', views.status, name='call_status'),
]
