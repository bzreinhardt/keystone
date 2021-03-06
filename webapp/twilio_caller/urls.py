from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'call$', views.call, name='call'),
    url(r'^record_callback/([0-9]+)$', views.record_callback,
        name='record_callback'),
    url(r'^connect/([0-9]+)$', views.connect, name='connect_endpoint'),
    url(r'^status/([0-9]+)$', views.status, name='call_status'),
    url(r'^viewer/([0-z]+)/$', views.viewer, name='render_viewer'),
    url(r'^notes/([0-z]+)/$', views.notes, name='notes'),
    url(r'^viewer/([0-z]+)/(?P<show_confidence>\w+)$', views.viewer, name='render_viewer'),
    url(r'^backend_viewer/([0-9A-Za-z_-]+)/$', views.backend_viewer, name='render_backend_viewer'),
    url(r'^upload$', views.simple_upload, name='simple_upload'),
    url(r'^upload_uberconf$', views.upload_uberconf, name='upload_uberconf'),
]
