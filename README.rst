Updownrecord
============
Upload and download data to a Django installation via web forms. The data is structured as records (model instances) that can be in various formats ('xml', 'json' etc.). 


When to use this application
----------------------------
This is weird idea. I may forget it. I hope, when I need it, I don't.

The app assumes the user is able to understand the idea of a model. Not that they are incapable or impatient and can only handle a text form. The idea assumes the user could (in most usage scenarios) organise model data for themselves.

In return the user gets silly-easy and efficient data upload/download. Bear in mind, this is not the usual file-upload scenario. The user has supplied text-based structured data. The data is moved as one, no mess with field-fractured web forms.  

I'd trust users to be able to do this, and enjoy the advantages. I suppose some people may feel that only admins should do this, and so place the ability under admin control. Bear in mind that Django security is still operative.

The reverse ability, to download a record from a remote location, provides a way to supply human-readable data from the models structuring a website. The data is not functionally useless or a dump. It has possibilities.


Limitations
-----------
Setup needs consideration for security.

Only handles CSV, FREECFG (see below), JSON, and XML (that's a limitation? Someone will probably think so).

High performance? Not likely.


Requires
--------
quickviews_


Alternatives
------------
What? Umm, an SQL script? Fabric? All the rest of that database maintenance equipment?


Status
------
This has been a tedious and time-consuming app to write. The problems are the uneven APIs for Python parsers (though I am glad they are available and developed), resolution of approaches to data structuring, Django's Serialization implementation, and a constantly changing API.

Do not rely on the API. Fortunately, the app is a leaf node, ending with users. No worry about dependancies.


Install
-------
In settings.py, ::

    INSTALLED_APPS = [
        ...
        'updownrecord.apps.UpdownrecordConfig',
        ]

If you want to use the included 'non-relational'serializers, add also, ::

    SERIALIZATION_MODULES = {
        "nonrel_csv": "updownrecord.serializers.csv",
        "nonrel_freecfg": "updownrecord.serializers.freecfg",
        "nonrel_json": "updownrecord.serializers.json",
        "nonrel_xml": "updownrecord.serializers.xml",
    }
    

Usage
-----
Data forms
~~~~~~~~~~
JSON and XML are well-known formats.

The app uses Django serialisers when asked. It also includes four more 
'non-relational' serializers. These will not, by specication, handle 
relations between models. Using these serializers is a kind of 
data-throttling, which can also help prevent exposing sensitive data. 
Text encoding can be anything, 'UTF-8' default. The JSON and XML 
versions save data in a form compatible with Django serializers.

The 'non-relational' serializers offer two extra, perhaps unusual, 
serialization formats. Both are interesting because they are easy
to read and hand-edit (unlike, especially, XML). The formats are, ::

CSV
    Comma Seeparated Values. Operates with or without a header line
    
FREECFG/CFG
    FREECFG is a home-made format which is similar to Microsoft 'ini' 
    files, but works round some limitations of the CFG format/Python 
    parser. The parser has no capacity for escapes, and whitespace is 
    stripped from all keys and values. FREECFG requires keys to adhere 
    to regex '\w+' i.e '[^a-zA-Z0-9\_]+'. 
    
    FREECFG has advantages. Section headers can be any string. The 
    parser can run with no section headers. Comments are inital 
    hash/pound, and valid anywhere. Values can be any length, including 
    paragraphs (only the start and end of values are stripped).

Serialized CSV is compact and very easy to machine-edit. FreeCFG is a
format that most people can understand and modify.

Download
~~~~~~~~
Enable a view. One line in a URL (if not complicated configuration), ::

    from updownrecord import views

    url(r'^(?P<pk>[0-9]+)/download/$', views.DownloadView.as_view(model=Firework, format="csv")),

(that line uses the default url parameter name of 'pk') Now download object pk=9 as CSV, ::

    http://127.0.0.1:8000/firework/9/download

There are a surprising number of options on DownloadView (it has an API similar to Django's ListView). 


Downloading object ranges
+++++++++++++++++++++++++
DownloadView can be set to download 'page' ranges, ::

    url(r'^download/$', views.DownloadView.as_view(use_querysets=True, format="json")),

Note the use of the explicit 'use_querysets' value to trigger queryset handling. By default, queryset handling is from the URL querystring, pages are 25 objects. So, to download items pk=50-75 as JSON, ::
 
    http://127.0.0.1:8000/updownrecord/download?page=2 

Queryset handling can be overridden to whatever you wish (e.g. search for titles?) by fully overriding get_queryset().


Options
+++++++
model_class
    State the model. Required (unless configured for fixed queryset).

pk_url_kwarg
    A URL argument to be found in a calling URL.

use_querysets
    Override self.pk_url_kwarg to return a set of data. At which point, the download class checks if there is a preset self.queryset. If not it looks for self.queryset_url_page_kwarg in the URL, if found it takes that as a paging argument based on self.queryset_page_size and otherwise fails. You can also override the dynamic queryset behaviour by overriding get_queryset().
    
include_pk
    if False will strip the pk field from downloads.
    
format
    (default='xml') Format data to this type, can be any of the types listed in the formats.

model_in_filename
    Adds the model name to the offered download filename.



Upload
~~~~~~~~
Upload is a simple one-field form.

Upload uses the same 'save' dynamic as the Django ORM; if a pk (or, for auto-increment, an 'id' field) is present, then the upload updates. If not, the upload appends.

Upload guesses at the form of the file (the code tries the MIME and the file extension of the uploaded file). The class can be limited to one format by setting the 'format' attribute e.g. ::

    format = 'csv'

Enable a view. One line in a URL (if not complicated configuration), ::

    url(r'^save/$', views.UploadRecordView.as_view(model_class=Firework), object_name_field_key='title'),


Other options
+++++++++++++
success_url
    Inherited from the underlying view. Redirect to the value of this
    attribute if the upload action is successful.
        
file_size_limit
    limit filesize (in MB), ::

        from updownrecord import UploadRecordView
        ...    
        urlpatterns = [
            url(r'^upload/$', UploadRecordView.as_view(model_class=Firework, file_size_limit=1)),
        ]
        
    limits uploads to 1MB.


popnone_normalize
    Normalise by removing (popping) any field value that tests as boolean False, such as empty strings (default=True).
    
    This is an elegant solution to normalizing much input data, because an unstated field takes defaults from the Django model. The places popnone_normalize may fail are when the field has no default (for some good reason?), when a field value is None for a defined purpose, etc. However, these seem to be corner cases. For example, popnone_normalize handles creation dates quite well (by removing any need to state a date, or concern about format, the Model falls back to a default). That is why the default for this option is True.

 
.. _quickviews: https://github.com/rcrowther/quickviews
