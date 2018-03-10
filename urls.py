from django.conf.urls import url

#from quickviews import ModelDetailView
#from paper.models import Paper
from testtable.models import ChristmasSong

from . import views

# tests
urlpatterns = [
    #url(r'^$', views.index, name='index'),
    url(r'^upload/$', views.UploadRecordView.as_view(model_class=ChristmasSong, object_name_field_key='gift')),
    #url(r'^(?P<pk>[0-9]+)/save/$', views.DownloadView.as_view()),
    url(r'^(?P<pk>[0-9]+)/download/$', views.DownloadRecordView.as_view(model_class=ChristmasSong,format='json')),
    url(r'^download/$', views.DownloadRecordView.as_view(model_class=ChristmasSong, use_querysets=True)),
]
