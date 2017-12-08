Updownrecord
============
Upload and download data to a Django installation via web forms. The data is structured as records (model instances) that can be in various formats ('ini', 'json' etc.).


When to use this application
----------------------------
This is weird idea. I may forget it, when I need it, and I hope I don't.

The app assumes the user is able to understand the idea of a model. Not that they are somewhat dumb or impatient and can only handle a text form. The idea assumes the user could (in most usage scenarios) organise model data for themselves.

In return the user gets silly-easy and efficient data upload/download. Bear in mind, this is not the usual file-upload scenario. The user has supplied structured data. The data is moved as one, no mess with field-fractured web forms.  

I'd trust users to be able to do this, and enjoy the advantages. I suppose some people may feel that only admins can do this, and so place the ability under admin control. Bear in mind that Django security is still operative.

The reverse ability, to download a record from a remote location, provides a way to supply human-readable site data which is not functionally useless or a dump. It has possibilities.


Limitations
-----------
(currently) Only one record

Self contained record only (ignores foreign keys) 


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
???


.. _quickviews: https://github.com/rcrowther/quickviews
