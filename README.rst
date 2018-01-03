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

Only handles CSV, CFG (microsoft '.ini'), FREECFG (see below), JSON, and XML (that's a limitation? Someone will probably think so).

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

Do not rely on the API. Fortunately, the app is a leaf node, ending with users. No worry about dependancies.


About data structuring
----------------------
The code contains extensive notes. In short, each download is resolved into a structure something like, for an object, object-as-dict; and for a queryset, list(object-as-dict()).

Uploads are treated in a similar way. This will not work for all data. For example, it is unusual to use 'ini' type files for consecutive record storage (this app enables that). Or, the SaveRecordView can not handle Microsoft Excel CSV output. However, all the handled formats are text-based, so should be easy to edit into a form where they will upload.


Install
-------
In settings.py, ::

    INSTALLED_APPS = [
        ...
        'updownrecord.apps.UpdownrecordConfig',
        ]


Usage
-----
Data forms
~~~~~~~~~~
CSV, CFG (microsoft '.ini'), JSON, and XML are well-known formats. The file views.py contains extensive notes on how the app handles them, especially for upload. Briefly, all are treated as a dictionary of key->value pairs, and must be in that 
format.

A couple of notes:

CSV
    Operates with or without a header line
    
FREECFG
    FREECFG is a home-made format which works round some limitations of the CFG format/Python parser. It has no capacity for escapes or section headers, and whitespace is stripped from all keys and values.

    FREECFG requires keys to adhere to regex '\w+' i.e '[^a-zA-Z0-9\_]'. However, it has advantages: FREECFG requires no section headers at all. It can handle any length of value, including paragraphs (only the start and end of values are stripped). It is also efficient.

Download
~~~~~~~~
Enable a view. One line in a URL (if not complicated configuration), ::

    from updownrecord import views

    url(r'^(?P<pk>[0-9]+)/download/$', views.DownloadView.as_view(model=Firework, data_type="csv")),

(that line uses the default url parameter name of 'pk') Now download object pk=9 as CSV, ::

    http://127.0.0.1:8000/firework/9/download

There are a surprising number of options on DownloadView (it has an API with some similarity to Django's ListView). 


Downloading object ranges
+++++++++++++++++++++++++
DownloadView can be set to download 'page' ranges, ::

    url(r'^download/$', views.DownloadView.as_view(use_querysets=True, data_type="json")),

Note the use of the explicit 'use_querysets' value to trigger queryset handling. By default, queryset handling is from the URL querystring, pages are 25 objects. So, to download items pk=50-75 as JSON, ::
 
    http://127.0.0.1:8000/updownrecord/download?page=2 

Queryset handling can be overridden to whatever you wish ( e.g. search for titles?) by fully overriding get_queryset().


Options
+++++++
model_class
    State the model. Required.

pk_url_kwarg
    A URL argument to be found in a calling URL.

use_querysets
    Override self.pk_url_kwarg to return a set of data. At which point, the download class checks if there is a preset self.queryset. If not it looks for self.queryset_url_page_kwarg in the URL, if found it takes that as a paging argument based on self.queryset_page_size and otherwise fails. You can also override the dynamic queryset behaviour by overriding get_queryset().
    
include_pk
    if False will strip the pk field from downloads.
    
data_type
    (default='JSON') Format data to this type, can be any of the types listed in the formats.
    
key_map
    A dict to map Model keys -> input keys. So if an input record names a field 'description', and the Model names the field 'desc', join the values (you can also drop input fields by not declaring them), ::
        
        url(r'^upload/$', DownloadloadRecordView.as_view(model_class=Firework, key_map={'desc' : 'description'}))

    The same key map can be used as in UploadRecordView, see below.

model_in_filename
    Adds the model name to the offered download filename.



Upload
~~~~~~~~
Upload is a simple one-field form.

Upload uses the same 'save' dynamic as the Django ORM; if a pk (or, for auto-increment, an 'id' field) is present, then the upload updates. If not, the upload appends.

Upload guesses at the form of the file. This can be limited to one form e.g. ::

    data_types = ['csv']

Enable a view. One line in a URL (if not complicated configuration), ::

    url(r'^save/$', views.UploadRecordView.as_view(model_class=Firework)),

Normalise
+++++++++
Sometimes input data needs to be manipulated. For example, manipulation is often needed when input data can be blank but a Model field disallows blank. 

Please note that this step is not validation (or should not be). All Django's Model and Form validation is still in place, and will be used when necessary. Normalisation is only for bridging the gap between the form of input data, and the configuration of a Model.

For fine detail handling, override the normalize() method. For a nice solution, try removing the data entirely (rather than setting with a new value). This will ask a new save to use values from the Model, ::

    def normalize(self, data):
        if (not data['created']):
            del(data['created'])
        return data

However, that simple example duplicates existing action. See below for popnone_normalize, which is True by default. Mostly, only override normalize() if you need very fine-grained control over data input, and popnone_normalize=False. 

Other options
+++++++++++++

file_size_limit
    limit filesize (in MB), ::

        from updownrecord import UploadRecordView
        ...    
        urlpatterns = [
            url(r'^upload/$', UploadRecordView.as_view(model_class=Firework, file_size_limit=1)),
        ]
        
    limits uploads to 1MB.

default
    Set a type if mime/extension detection fails, ::

        url(r'^upload/$', UploadRecordView.as_view(model_class=Firework, default='json')),

key_map
    A dict to map Model keys -> input keys. So if an input record names a field 'description', and the Model names the field 'desc', join the values (you can also drop input fields by not declaring them), ::
        
        url(r'^upload/$', UploadRecordView.as_view(model_class=Firework, key_map={'desc' : 'description'}))

    The same key map can be used as in DownloadRecordView, see above.


popnone_normalize
    Normalise by removing (popping) any field value that tests as boolean False, such as empty strings (default=True).
    
    This is an elegant solution to normalizing much input data, because an unstated field then takes defaults from the Django model. The places popnone_normalize may fail are when the field has no default (for some good reason?), when a field value is None for a defined purpose, etc. However, these seem to be corner cases. For example, popnone_normalize handles creation dates quite well (by removing any need to state a date, or concern about format, the Model falls back to a default). That is why the default is True.
    
    
data workflow
++++++++++++++
For reference,

- Parse the input
- Convert the parsed key/values to a dict
- If key_map exists, map keys of dict to Model field names
- If popnone_normalize=True, remove 'empty' values
- Run normalize() for extra tweaks
- Convert dict to model, then save()

 
.. _quickviews: https://github.com/rcrowther/quickviews
