import csv
import json
import configparser
from xml.etree.ElementTree import XMLParser
import xml.etree.ElementTree as ET

import io
import collections
import os
from itertools import chain
import math
import copy

import traceback
from django.shortcuts import render
from django import forms
from django.core.exceptions import ValidationError

from quickviews import ModelCreateView, CreateView
from paper.models import Paper
from testtable.models import ChristmasSong


from django.http import HttpResponse, StreamingHttpResponse
from django.views.generic import View

#? get a 'SaveAs'
#? pk detection more than model._meta.pk, I recall
#? guess or state for upload
#? state or offer for download
#? how about updating too?
#? size limitations
#? Admin protection
#? check charsets
#? Just a parser for csv and JSON?
#? data can be more abstract?
#? allow args (e.g dialect to CSV dictwriter)
#? redirect or something on DownloadView
#? add app name as well as model name to the pk
#? format page filename
'''
== Structured output and input
The app can handle both single objects and a range of pks (though not,
currently, a queryset)
When handling a queryset, the data will be structured, pseudo-code, as
Array(Map(modelfieldname -> modelfieldvalue)).
For consistent handling, though a little more extensive for single items
than necessary, single items are written and retrieved as though in an 
array of one item.
For how each data style represents the structure, see the following
notes. 

== CSV
CSV is the only storage type which does not by default implement key to 
value (it can rely on knowing the structure to read into).
This is a problem, because we would like to implement the Django 
convention of 'if there is a pk, insert, if not, create'. Without keys
we get into difficult territory; counting fields to guess if a pk is 
present. All in all, the best bet seems to be to insist that CSV files
have a header (which is easily added). This means also we can then have 
the same approach to data structure across all representations. 
== XML
On the basis that, though they are atomic (and often auto-integers), 
Django PKs are primary information (not meta information), pks are
elements, not attributes,
https://stackoverflow.com/questions/152313/xml-attributes-vs-elements
=== CFG
CFG (Windows 'ini') can only represent group labels and key->values 
(sometimes with a group of default values).
This app assumes that the CFG file itself represents an array, and that
each group contained is an object.
 
PKs are data lines, not group labels. See the similar argument for XML.
The group title must then identify an object. Yet, for CFG, a group 
label must be unique. The solution is to auto-number the labels. Bear in
mind these group-label numbers are not data, they are index numerics.
Similar to an explicit array index.
'''
StructureData = collections.namedtuple('StructureData', ['name', 'detailfunc', 'qsfunc', 'mime'])



class DownloadRecordView(View):
    '''
    By default the view downloads a record selected by pk_url_kwarg
    
    If 'pk_url_kwarg = None' the view looks at queryset data. If the
    queryset has been defined, that is used (refreshing every time).
     
    If queryset is also None, the view pages the model data, selecting 
    by queryset_url_page_kwarg and queryset_page_size. 
    queryset_url_page_kwarg is sought in the query string, not the url 
    path e.g. ::
    
    http://127.0.0.1:8000/firework/download?page=2 
        
    Offered filenames are: for a single object, the pk of the source record.
    For a paged queryset 'page-[?]'. For a custom queryset, 'query' 
    (overridable on selection_id). Filenames are not intended as unique 
    identifiers. 
    
    If you wish to prefix the offered filename with the model name, 
    which makes the filename closer to a unique name, set 
    'model_in_filename=True'.
    
    @param pk_url_kwarg name of argument for pks
    @param model_in_filename prefix the filename with the model name
    '''
    #! size limit
    #data_type="csv"
    data_type="json"
    #data_type="cfg"
    #data_type="xml"
    model_class = ChristmasSong
    pk_url_kwarg = 'pk'
    use_querysets = False
    queryset = None
    queryset_url_page_kwarg = 'page'
    queryset_page_size = 4
    selection_id = 'query'
    include_pk = True
    #include_pk = False
    model_in_filename = False

    def model_name(self):
        return self.model_class._meta.model_name

    def model_fields(self):
        opts = self.model_class._meta
        # Note: my guess. Should be concrete_fields and private_fields?
        # Let the Django API decide, see if this works out. R.C.
        fields = opts.get_fields()
        if (not self.include_pk):
            fields.remove(opts.pk)
        return fields
        
    def model_fieldnames(self):
        return [f.name for f in self.model_fields()]

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
            firework/dowload/page/...            
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
                #page = int(self.kwargs[self.queryset_url_page_kwarg])
                page = int(self.request.GET.get(self.queryset_url_page_kwarg, '1'))
            except Exception:
                # ignore, default to 1
                page = 1
            if (page < 1):
                raise Http404("Invalid page '{}'".format(
                    page
                ))
            frm = ((page - 1) * self.queryset_page_size) + 1
            # NB: range is inclusive, 'to', we need our end to be 
            # 'until', so -1
            to = frm + (self.queryset_page_size - 1)
            queryset = self.model_class._default_manager.filter(pk__range=(frm, to))
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


    def obj_to_dict(self, fields, instance):
        """
        Return a dict containing the data in ``instance``.
        """
        opts = instance._meta
        pk_name = opts.pk.name
        # maintain some order, even if not critical
        data = collections.OrderedDict()
        for f in fields:
            data[f.name] = f.value_from_object(instance)
        return data

    def _dict2csv_obj(self, writer, data_dict):
        writer.writerow(data_dict)

    def dict2csv_detail(self, detail_dict):
        #? CSV continues to use the CSV parser because it has an option
        #? 'dialect' which may sometime be enabled
        fields = self.model_fieldnames()
        so = io.StringIO()
        writer = csv.DictWriter(so, fieldnames=fields)
        writer.writeheader()
        self._dict2csv_obj(writer, detail_dict)
        r = so.getvalue()
        so.close()
        return ''.join(r)

    def dict2csv_queryset(self, queryset_array):
        fields = self.model_fieldnames()
        so = io.StringIO()
        writer = csv.DictWriter(so, fieldnames=fields)
        writer.writeheader()
        for idx, detail_dict in enumerate(queryset_array):
            self._dict2csv_obj(writer, detail_dict)
        r = so.getvalue()
        so.close()
        return ''.join(r)

    def _dict2json(self, data):
        encoder = json.JSONEncoder(ensure_ascii=False)
        return encoder.encode(data)
                
    def dict2json_detail(self, detail_dict):
        return self._dict2json(detail_dict)

    def dict2json_queryset(self, queryset_array):
        return self._dict2json(queryset_array)
        
    def _dict2cfg_obj(self, b, data_dict):
        for k, v in data_dict.items():
            b.append('{0} = {1}\n'.format(k, v))
        
    def dict2cfg_detail(self, detail_dict):
        b = []
        b.append('[{}]\n'.format(self.model_name()))
        self._dict2cfg_obj(b, detail_dict)
        return ''.join(b)
        
    def dict2cfg_queryset(self, queryset_array):
        b = []
        for idx, detail_dict in enumerate(queryset_array):
            b.append('[{}]\n'.format(idx))
            self._dict2cfg_obj(b, detail_dict)
        return ''.join(b)
            
    def _dict2xml_obj(self, b, data_dict):
        b.append('<{}>\n'.format(self.model_name()))
        for k, v in data_dict.items():
            b.append('    <{0}>{1}</{0}>\n'.format(k, v))
        b.append('</{}>\n'.format( self.model_name()))
        
    def dict2xml_detail(self, detail_dict):
        b = []
        b.append('<?xml version = "1.0" encoding = "UTF-8"?>\n')
        self._dict2xml_obj(b, detail_dict)
        return ''.join(b)

    def dict2xml_queryset(self, queryset_array):
        b = []
        b.append('<?xml version = "1.0" encoding = "UTF-8"?>\n')
        b.append('<queryset>\n')
        for detail_dict in queryset_array:
            self._dict2xml_obj(b, detail_dict)
        b.append('</queryset>\n')
        return ''.join(b)

    _data_type_map = {
        'csv' : StructureData(
            name='csv', 
            detailfunc=dict2csv_detail, 
            qsfunc=dict2csv_queryset, 
            mime='text/csv'
        ),
        'json' : StructureData(
            name='json', 
            detailfunc=dict2json_detail, 
            qsfunc=dict2json_queryset, 
            mime='application/json'
        ),
        'cfg' : StructureData(
            name='cfg', 
            detailfunc=dict2cfg_detail, 
            qsfunc=dict2cfg_queryset,
            mime='text/plain'
        ),
        'xml' : StructureData(
            name='xml', 
            detailfunc=dict2xml_detail, 
            qsfunc=dict2xml_queryset, 
            mime='text/xml'
        ),
    }
      
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
        fields = self.model_fields()
        structdata = self._data_type_map[self.data_type]
        if (not self.use_querysets):
            pk = int(kwargs[self.pk_url_kwarg])
            obj = self.model_class._default_manager.get(pk=pk)
            data_dict = self.obj_to_dict(fields, obj)
            data_text = structdata.detailfunc(self, data_dict)
            self.selection_id = str(pk)
        else:
            qs = self.get_queryset()           
            data_dict = [self.obj_to_dict(fields, obj) for obj in qs]
            data_text = structdata.qsfunc(self, data_dict)
        dstfilename = self.destination_filename(self.selection_id, structdata.name)
        # set content and type
        response = HttpResponse(data_text, content_type=structdata.mime)
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

_extension_map = {
    'csv' : 'csv',
    'json' : 'json',
    'cfg': 'cfg',
    'ini': 'cfg',
    'xml': 'xml'
}



class UploadRecordView(CreateView):
    '''
    '''
    fields = ['data']
    model_class = ChristmasSong
    data_types = ['cfg', 'csv', 'json', 'xml']
    force_insert = True
    file_size_limit = 2
    #success_url = self.return_url()

    def get_form(self, form_class=None):
        form_class = get_upload_form(self.file_size_limit)
        return super().get_form(form_class)
        
    def get_type(self, uploadfile):
        tpe = None
        # try MIME
        mime = uploadfile.content_type
        tpe = _mime_map.get(mime)
        if (not tpe):
            # failed on mime, try extension
            base = os.path.basename(uploadfile.name)
            extension = base.rsplit('.', 1)[1]
            tpe = _extension_map.get(extension)
            if (not tpe):
              #? 404, cause not in validation
              raise ValidationError("Failed to identify uploaded file from mime or extension mime:'{0}' extension:'{1}'".format(mime, extension))
        return tpe
        
    def binaryToUTF8Iter(self, fileUploadObject):
        for line in fileUploadObject:
            yield line.decode('utf-8')
            
    def binaryToUTF8Str(self, fileUploadObject):
        s = fileUploadObject.read()
        return s.decode('utf-8')

    def _cfg2dict(self, parser, section_name):
        b = {}
        for k, v in parser[section_name].items():
            b[k] = v
        return b

    def cfg2dictlist(self, sections):
        l = []
        for section_name in sections:
            l.append(self._cfg2obj(parser, section_name))
        return l
                        
    def cfg2python(self, uploadfile):
        parser = configparser.ConfigParser()
        parser.read_file(self.binaryToUTF8Iter(uploadfile))
        sections = parser.sections()
        if (len(sections) > 1):
            return self.cfg2dictlist(parser, sections) 
        else:
            return self._cfg2dict(parser, sections[0])

    def csv2python(self, uploadfile):
        # if CSV has headers, this reads ok
        reader = csv.DictReader(self.binaryToUTF8Iter(uploadfile))
        l = [obj_dict for obj_dict in reader]
        if (len(l) > 1):
            return l
        else:
            # if only one, strip the object_dict out of the list
            return l[0]

    # Note on the JSON implementation
    # This is nice, but handles as a chunk 
    def json2python(self, uploadfile):
        decoder = json.JSONDecoder(strict=True) #object_pairs_hook=collections.OrderedDict)
        l = decoder.decode(self.binaryToUTF8Str(uploadfile))
        return l
        

    from xml.etree.ElementTree import XMLParser
    class DetectStarts():
        depth = 0
        closed = False
        def start(self, tag, attrib):
            if (not self.closed):
                self.depth += 1
        def end(self, tag):
            self.closed = True          
        def depth_decided(self):
            return self.closed

    def xml_find_depth(self, file_iter):
        ds = self.DetectStarts()
        parser = XMLParser(target=ds)
        for l in file_iter:
            parser.feed(l)
            if (ds.depth_decided()):
                break
        return ds.depth

    def _xml2dict(self, object_tag):
        b = {}
        for child in object_tag:
            b[child.tag] = child.text
        return b
                        
    # Note on the XML implementation
    # Python's builtin XML parsers are ...not designed for this.
    # The current implementation is ugly (has_child traversal, 
    # where are you?)
    # The current implementation is also not robust, depending on 
    # tag depths constructed as per instructions. However,
    # we require our format for other styles, even if the XML 
    # iumplementation is particularly weak (blame XML itself here, too)
    # So this is adequate. For now. R.C.  
    def xml2python(self, uploadfile):
        depth = self.xml_find_depth(self.binaryToUTF8Iter(uploadfile))
        if (depth > 2):
            # we assume that is object descriptions and their container
            # i.e. queryset
            l = []
            root = ET.fromstringlist(self.binaryToUTF8Iter(uploadfile))
            for obj in root:
                l.append(self._xml2dict(obj))
            return l
        else:
            # assume container with object fields i.e. detail
            root = ET.fromstringlist(self.binaryToUTF8Iter(uploadfile))
            return self._xml2dict(root)

    _data_type_map = {
        'cfg' : StructureData(name='cfg', detailfunc=cfg2python, qsfunc=None, mime='text/plain'),
        'csv' : StructureData(name='csv', detailfunc=csv2python, qsfunc=None, mime='text/csv'),
        'json' : StructureData(name='json', detailfunc=json2python, qsfunc=None, mime='application/json'),
        'xml' : StructureData(name='xml', detailfunc=xml2python, qsfunc=None, mime='text/xml')
    }    
    
    #def fail_action(self, form):
    #    print('fail')
    #    print(form)

    def success_action(self, form):
        obj = None
        uploadfile = self.request.FILES['data']
        data_type = self.get_type(uploadfile)
        structdata = self._data_type_map[data_type]
        data = structdata.detailfunc(self, uploadfile)
        #print('data')
        #print(str(data))
        if isinstance(data, list):
            #?use bulk save?
            for obj_dict in data:
                obj = self.model_class(**obj_dict)
                #obj.save(force_insert=self.force_insert)
        else:
            obj = self.model_class(**data)
            #obj.save(force_insert=self.force_insert)
        return obj

     
