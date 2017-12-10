from django.conf.urls import url

from quickviews import ModelDetailView
from paper.models import Paper

from . import views

# tests
urlpatterns = [
    #url(r'^$', views.index, name='index'),
    url(r'^save$', views.UploadRecordSave.as_view()),
    #url(r'^(?P<pk>[0-9]+)/save/$', views.DownloadView.as_view()),
    url(r'^download/$', views.DownloadView.as_view(pk_url_kwarg=None)),
    #url(r'^(?P<article_pk>[0-9]+)/$', list.ModelListBuilderView.as_view(model=Paper, use_fields=['title', 'author', 'create_date'])),
]
