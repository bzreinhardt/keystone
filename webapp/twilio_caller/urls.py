from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'call$', views.call, name='call'),
    url(r'^record_callback$', views.record_callback, name='record_callback'),
    url(r'^connect/(\+[0-9]{11})$',
        views.connect, name='connect_endpoint'),
]
