from django.conf.urls import url

from paper.models import Paper
from testtable.models import ChristmasSong

from . import views

# tests
urlpatterns = [
    url(r'^upload/$', views.UploadRecordView.as_view(model_class=ChristmasSong, format='json')),
    url(r'^(?P<pk>[0-9]+)/download/$', views.DownloadRecordView.as_view(model_class=ChristmasSong, format='json')),
    url(r'^download/$', views.DownloadRecordView.as_view(model_class=ChristmasSong, use_querysets=True)),
]
