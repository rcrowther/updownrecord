Testtable
=========
Upload and download data structured as records (model instances) direct to Django instalations.

    'updownrecord.apps.UpdownrecordConfig',


When to use this application
----------------------------
This is weird idea. I may forget it, when I need it, and I hope I don't.

The app assumes the user is able to understand the idea of a model. Not that they are somewhat dumb or impatient and can only handle a text form. The idea assumes the user could (in most usage scenarios) organise model data for themselves.

In return the user gets silly-easy and efficient data upload/download. Bear in mind, this is not the usual file-upload scenario. The user has supplied data that is structured. The data is moved as one, without messing with field-fractured web forms.  

I'd trust users to be able to do this, and enjoy the advantages. I suppose some people may feel that only admins can do this, and so place the ability under admin control. Bear in mind that Django security is still operative.

The reverse ability, to stream a record back from a remote location, provides an interesting way to supply human-readable site data which is not functionally useless or a complete dump. It has interesting possibilities.


Limitations
-----------
Currently, only one record


Requires
--------
quickviews_


Alternatives
------------
What? Umm, an SQL script? Fabric? all the rest of that database maintenance equipment?


Install
-------
In settings.py, ::

    INSTALLED_APPS = [
        ...
        'updownrecord.apps.UpdownrecordConfig',
        ]


Usage
-----
???


.. _quickviews: https://github.com/rcrowther/quickviews
