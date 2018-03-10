import io
import collections
import os
import copy
import importlib


from django import forms
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.http import HttpResponse, Http404
from django.views.generic import View
from django.core import serializers as serializers

#1 protect
from quickviews import ModelCreateView, CreateView

#from .xml_serializer import *
#from .serializers import csv, json, freecfg, xml


'''
== Structure of data
The app can handle both single objects and querysets.
When handling a queryset, the data will be structured, pseudo-code, as
Array(Map(modelfieldname -> modelfieldvalue)).
When handling an object, the data will be structured, pseudo-code, as
Array(Map(modelfieldname -> modelfieldvalue))..
For how each data style represents the structure, see the following
notes. 

When objects need named ids for the group (CFG Detail/JSON) these are 
set to the model name. When this is not possible because the group names 
must be unique (CFG Queryset) they are simple index numerics.

The details of any group names are not relevant to the app. The code 
is only looking for a single group, or list of groups, of tag pairs. 
These are used to populate object fields.

=== CFG
CFG (Windows 'ini') can only represent group labels and key->values 
(sometimes with a group of default values).
This app assumes that the CFG file itself represents an array, and that
each group contained is an object.

CFG input must have at least one section header at the top pf the file
but see FREECFG below.

CFG will not allow group names to be repeated, so they are indexed
(pks are in the data lines). 
 
PKs are data lines, not group labels. See the similar argument for XML.

== FREECFG
FREECFG is a home-made format which works round some limitations of the 
CFG format/Python parser. It has no capacity for escapes or section 
headers, and whitespace is stripped from all keys and values.

FREECFG requires keys to adhere to regex '\w+' i.e '[^a-zA-Z0-9_]'
However, it has advantages: FREECFG requires no section headers at all.
And it can handle any length of value, including paragraphs (only
the start and end of values are stripped). It is also efficient.

== CSV
CSV is the only storage type which does not by default implement key to 
value (it can rely on knowing the structure to read into).
This is a problem, because we would like to implement the Django 
convention of 'if there is a pk, insert, if not, create'. Without keys
we get into difficult territory; counting fields to guess if a pk is 
present. All in all, the best bet seems to be to insist that CSV files
have a header (which is easily added). 

== JSON
JSON presents the least problems, as it can represent the structure 
naturally.

== XML
An XML file requires a root, so one element set represents that.

For detail, the field pairs are within the root.

For queryset, tag sets for each object are within the root.

On the basis that, though they are atomic (and often auto-integers), 
Django PKs are primary information (not meta information), pks are
elements, not attributes,
https://stackoverflow.com/questions/152313/xml-attributes-vs-elements
'''
SerializationData = collections.namedtuple('SerializationData', ['format', 'mimes', 'file_extensions', 'model_required'])

# First MIME/extension is used as default (e.g. for downloads)
SERIALIZATION_DATA = [
    SerializationData('json', ['text/json', 'application/json'], ['json'], False),
    SerializationData('xml', ['text/xml', 'application/xml'], ['xml'], False),
    # place additions to core later, where they will not override MIME/extension etc. defaults
    SerializationData("nonrel_csv",  ['text/csv'], ['csv'], True),
    SerializationData("nonrel_freecfg", ['text/plain'], ['cfg', 'freecfg', 'ini'], False),
    SerializationData("nonrel_json", ['text/json', 'application/json'], ['json'], False),
    SerializationData("nonrel_xml", ['text/xml', 'application/xml'], ['xml'], False),
]

def mime_map():
    b = {}
    for d in SERIALIZATION_DATA:
        for mime in d.mimes:
            if (not mime in b):
              b[mime] = d
    return b

MIME_MAP = mime_map()

def extension_map():
    b = {}
    for d in SERIALIZATION_DATA:
        for extension in d.file_extensions:
            if (not extension in b):
              b[extension] = d
    return b
    
EXTENSION_MAP = extension_map()

FORMAT_MAP = {d.format : d for d in SERIALIZATION_DATA}



#! introduce 'ignore'
#! remove popnone
#! use new serializers (how?)
#? remove 'model in filename' option
#? size limit (on what?)
# consider MIME and how to choose a mime for a serializer
# how to pass class to csv serializer?
class DownloadRecordView(View):
    '''
    
    By default the view downloads a single record selected by 
    pk_url_kwarg (default id 'pk'). If this setup is used, model_class
    must be set, e.g.
    
    url(r'^(?P<pk>[0-9]+)/download/$', views.DownloadRecordView.as_view(model_class=SomeModel)),

    If 'use_querysets = True' the view looks at queryset data. If the
    'queryset' attribute has been defined, that is used 
    (refreshing using queryset.all()). model_class can be none (i.e.
    mixed class) e.g.
    
    url(r'^download/$', views.DownloadRecordView.as_view(model_class=SomeModel, use_querysets=True, queryset=SomeModel.objects.filter(author="Eric Idle"))),

    If  'use_querysets = True' and the queryset is None, the view pages 
    the model defined in model_class, selecting by 
    queryset_url_page_kwarg (default = 'page') and queryset_page_size. 
    Note that queryset_url_page_kwarg is sought in the 
    query string, not the url path e.g. ::

    url(r'^download/$', views.DownloadRecordView.as_view(model_class=SomeModel, use_querysets=True)),

    reached by, ::
        
    http://127.0.0.1:8000/firework/download?page=2 
        
    Offered filenames are: for a single object, the pk of the source record.
    For a paged queryset 'page-[?]'. For a custom queryset, 'query' 
    (overridable on selection_id). Filenames are not intended as unique 
    identifiers. 
    
    If you wish to prefix the offered filename with the model name, 
    which makes the filename closer to a unique name, set 
    'model_in_filename=True'.
    
    @param model_class only classes of this model wil be allowed.
    @param pk_url_kwarg name of argument for pks
    @param use_querysets override the pk_url_kwarg for query handling.
    @param model_in_filename prefix the filename with the model name
    '''
    # XML as default
    format="xml"
    mime=None
    model_class = None
    pk_url_kwarg = 'pk'
    use_querysets = False
    queryset = None
    queryset_url_page_kwarg = 'page'
    queryset_page_size = 25
    selection_id = 'query'
    #include_pk = True
    model_in_filename = False
      
    def __init__(self, **kwargs):
        if ('format' in kwargs):
            self.format = kwargs['format']
        if (not self.format):
            raise ImproperlyConfigured(
                "DownloadRecordView requires a definition of 'format'")
        if ('mime' in kwargs):
            self.mime = kwargs['mime']
        else:
            data = FORMAT_MAP.get(self.format, None)
            if (not data):
                raise ImproperlyConfigured(
                    "DownloadRecordView requires a MIME type. No default found for the format (and no MIME provided via 'mime' parameter): format:'{}'".format(
                    self.format
                    ))
            self.mime = data.mimes[0]            
        super().__init__(**kwargs)

    def model_name(self):
        return self.model_class._meta.model_name

    def get_queryset(self):
        """
        Return the list of items for this view.

        The return value must be an iterable and may be an instance of
        `QuerySet` in which case `QuerySet` specific behavior will be enabled.
        
        The default is to assemble a 'page' of data, delimited by 
        'queryset_page_size' and URL defined by 'queryset_url_page_kwarg'
        If a URL arg can not be found, the queryset defaults to page 1.
        
        This method can be overridden to become dynamic i.e. respond
        to URL parameters. One way to pass query parameeters is to use a
        query string. The request is held on the class as 
        'self.request'. To access, use code like, ::
            selector = request.GET.get('somekwarg', None)
        Another way would be to use a subpathed URL parameter,
            firework/download/page/...            
        Then do a filter on the model manager and return. In this way
        the download view can offer to users the ability to, for exaple,
        download items 'authored by...' etc. 
        
        Please consider: if you gather URL parameters in this way, you 
        are responsible for validation (though the Django URL regex is 
        a good start).
        """
        if self.queryset is not None:
            queryset = self.queryset
            if isinstance(queryset, QuerySet):
                queryset = queryset.all()
        elif self.model_class is not None:
            try:
                # this is how to get query args from Django 
                page = int(self.request.GET.get(self.queryset_url_page_kwarg, '1'))
            except Exception:
                # ignore, default to 1
                page = 1
            if (page < 1):
                raise Http404("Invalid page number requested '{}'".format(
                    page
                ))
            frm = ((page - 1) * self.queryset_page_size) + 1
            # NB: range is inclusive, 'to', we need our end to be 
            # 'until', so -1
            to = frm + (self.queryset_page_size - 1)
            queryset = self.model_class._default_manager.filter(pk__range=(frm, to))
            if (not len(queryset) > 0):
                raise Http404("Query us empty, possibly page number too high for data? page:'{}'".format(
                    page
                )) 
            self.selection_id = 'page-{}'.format(page)
        else:
            raise ImproperlyConfigured(
                "{} is missing a QuerySet. Define "
                "().pk_url_kwarg (for single items), %(cls)s.queryset, or override "
                "().get_queryset().".format(
                    self.__class__.__name__
                )
            )
        return queryset

    def destination_filename(self, selection_id, extension, to=None):
        modelstr = ''
        if (self.model_in_filename):
            modelstr = '{}_'.format(self.model_class._meta.model_name)
        filename = '{0}{1}.{2}'.format(
            modelstr, 
            selection_id,
            extension
        )
        return filename
            
    def get(self, request, *args, **kwargs):
        if (not self.use_querysets):
            pk = int(kwargs[self.pk_url_kwarg])
            qs = self.model_class._default_manager.filter(pk=pk)
            self.selection_id = str(pk)
        else:
            qs = self.get_queryset()
        s = serializers.get_serializer(self.format)
        serializer = s()
        serializer.serialize(qs)          
        # set content and type
        response = HttpResponse(serializer.getvalue(), content_type=self.mime)
        dstfilename = self.destination_filename(self.selection_id, self.format)
        # Add the treat-as-file header
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(dstfilename)
        return response
    
    

from django.core.exceptions import ValidationError

def get_upload_form(file_size_limit=None):
    class _UploadRecordForm(forms.Form):
        def file_size(value):
            if (file_size_limit):
                limit = file_size_limit * 1024 * 1024
                if value.size > limit:
                    raise ValidationError('File too large. Size should not exceed {} MB.'.format(
                        file_size_limit
                    ))
        data = forms.FileField(label='Data', validators=[file_size])
    return _UploadRecordForm



# These two dicts are for purposes of identifying files.
# The data has no need to be complete. If data is provided,
# it should be a close guess at intention (e.g. do not try to make all 
# 'text/' mimes into config files. But 'text/xml' wants to be known as 
# XML)
_mime_map = {
    'text/csv' : 'csv',
    'text/json' : 'json',
    'application/json' : 'json',
    'text/xml' : 'xml',
    'application/xml' : 'xml'
}




import re
from configparser import ParsingError

#! yes, want a forced must-deal-with this format and mime
class UploadRecordView(CreateView):
    '''
    Simple form to upload structured data to a model.
    
    Success may depend of the form of the data and deserialisation
    chosen.

    @param formats limit the dta types (beyond the ability to process)
    @param file_size_limit in MB (e.g. value = 2 is 2MB)
    @param default for form of input file. Tried if MIME and and extension fail.
    '''
    model_class = None
    formats = ['cfg', 'freecfg', 'csv', 'json', 'xml']
    # for data type
    default = None
    force_insert = False
    file_size_limit = 2
    popnone_normalize = True
    #success_url = self.return_url()
    
    def __init__(self, **kwargs):
        if (not 'object_name_field_key' in kwargs):
            raise ImproperlyConfigured(
                "DownloadRecordView requires a definition of 'object_name_field_key'")
        self.object_name_field_key = kwargs['object_name_field_key']
        super().__init__(**kwargs)
        #if (self.default and (not (self.default in self.formats))):
            #raise ImproperlyConfigured('{} default not found in data types. default:"{}", valid data types:{}'.format(
                #self.__class__.__name__,
                #self.default,
                #', '.join(self.formats),
                #))    
        
    def get_form(self, form_class=None):
        form_class = get_upload_form(self.file_size_limit)
        return super().get_form(form_class)
        
    def get_type(self, uploadfile):
        format = None
        # try MIME
        mime = uploadfile.content_type
        data = MIME_MAP.get(mime)
        
        if (not data):
            # failed on mime, try extension
            base = os.path.basename(uploadfile.name)
            extension = None
            try:
                extension = base.rsplit('.', 1)[1]
            except IndexError:
                raise Http404("Failed to identify uploaded file from mime and unable to find extension. mime:'{0}'".format(
                    mime
                ))
                
            data = EXTENSION_MAP.get(extension)
            if (not data):
                raise Http404("Failed to identify uploaded file from mime or extension. mime:'{0}' extension:'{1}'".format(
                    mime, 
                    extension
                ))
        return data.format
        
    def binaryToUTF8Iter(self, fileUploadObject):
        for line in fileUploadObject:
            yield line.decode('utf-8')
        
    def save_action(self, data):
        '''
        Map, normalise then save a dict object representation.
        '''
        #if (self.popnone_normalize):
        #    data = {k:v for k, v in data.items() if v}
        obj = self.model_class(**data)
        obj.save(force_insert=self.force_insert)
        return obj
        
    def success_action(self, form):
        obj = None
        uploadfile = self.request.FILES['data']
        format = self.get_type(uploadfile)
        obj= None
        # Chime for Django: uploadfile objects are enough of an 
        # iterable string or stream to go into a deserializer direct 
        # R.C.
        for dobject in serializers.deserialize(format, uploadfile):
           obj = dobject.object
           print(str(obj))           
           #? Protect for recovery, or allow to explode on exception?
           #dobject.object.save(force_insert=self.force_insert)
        return obj
