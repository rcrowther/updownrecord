Updownrecord
============
Upload and download data to a Django installation via web forms. The data is structured as records (model instances) that can be in various formats ('ini', 'json' etc.).


When to use this application
----------------------------
This is weird idea. I may forget it. I hope, when I need it, I don't.

The app assumes the user is able to understand the idea of a model. Not that they are somewhat dumb or impatient and can only handle a text form. The idea assumes the user could (in most usage scenarios) organise model data for themselves.

In return the user gets silly-easy and efficient data upload/download. Bear in mind, this is not the usual file-upload scenario. The user has supplied text-based structured data. The data is moved as one, no mess with field-fractured web forms.  

I'd trust users to be able to do this, and enjoy the advantages. I suppose some people may feel that only admins can do this, and so place the ability under admin control. Bear in mind that Django security is still operative.

The reverse ability, to download a record from a remote location, provides a way to supply human-readable site data. The data is not functionally useless or a dump. It has possibilities.


Limitations
-----------
Self-contained records only (foreign keys are unsupported) 

Only handles CSV, CFG (microsoft '.ini'), JSON, and XML (that's a limitation? Someone will probably think so).

Text encoding must be UTF-8

High performance? Not likely.


Requires
--------
quickviews_


Alternatives
------------
What? Umm, an SQL script? Fabric? All the rest of that database maintenance equipment?


Status
------
This has been a tedious and time-consuming app to write. The problems are the uneven APIs for Python parsers (though I am glad they are available and developed), resolution of approaches to data structuring, and a constantly changing API.

Do not rely on the API. Fortunately, the app is a leaf node, ending with users. No need to worry about dependancies.


About data structuring
----------------------
The code contains extensive notes. In short, each download is resolved into a structure something like, for an object, object-as-dict; and for a queryset, list(object-as-dict()).

Uploads are treated in a similar way. This will not work for all data. For example, it is unusual to use 'ini' type files for consecutive record storage (this app enables that). Or, the SaveRecordView can not handle Microsoft Excel CSV output. However, all the handled formats are taxt-based, so they should be easy to edit into a form where they will upload.


Install
-------
In settings.py, ::

    INSTALLED_APPS = [
        ...
        'updownrecord.apps.UpdownrecordConfig',
        ]


Usage
-----
Download
~~~~~~~~
Enable a view. One line in a URL (if not complicated configuration), ::

    from updownrecord import views

    url(r'^download/(?P<pk>[0-9]+)$', views.DownloadView.as_view(model=Firework, data_type="csv")),

(that line uses the default url parameter name of 'pk') Now download object pk=9 as CSV, ::

    http://127.0.0.1:8000/firework/download/9

There are a surprising number of options on DownloadView (it has an API with some similarity to Django's ListView). It can be set to download 'page' ranges, ::

    url(r'^download/$', views.DownloadView.as_view(use_querysets=True, data_type="json")),

Note the use of the explicit 'use_querysets' value to trigger queryset handling. By default, queryset handling is from the URL querystring, pages are 25 objects. So, to download items pk=50-75 as JSON, ::
 
    http://127.0.0.1:8000/updownrecord/download?page=2 

Queryset handling can be overrdden to whatever you wish ( e.g. search for titles?) by fully overriding get_queryset().

Upload
~~~~~~~~
Upload is a simple one-field form.

Upload uses the same 'save' dynamic as Django ORM; if a pk (or, for auto-increment, an 'id' field) is presnt, then the upload updates. If not, the upload appends.

Upload guesses at the form of the file. This can be limited to one form e.g. ::

    data_types = ['csv']

Enable a view. One line in a URL (if not complicated configuration), ::

    url(r'^save/$', views.UploadRecordView.as_view(model_class=Firework)),

There are a couple of other options. Most notably, the form and form construction can limit filesize, ::

    url(r'^save/$', views.UploadRecordView.as_view(model_class=Firework, file_size_limit=1)),
    
limits uploads to 1MB.


.. _quickviews: https://github.com/rcrowther/quickviews
