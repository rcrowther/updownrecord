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
Self contained records only (ignores foreign keys) 

Only handles CSV, CFG (microsoft '.ini'), JSON, and XML (that's a limitation? Someone will probably think so).


Requires
--------
quickviews_


Alternatives
------------
What? Umm, an SQL script? Fabric? All the rest of that database maintenance equipment?


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

.. _quickviews: https://github.com/rcrowther/quickviews
