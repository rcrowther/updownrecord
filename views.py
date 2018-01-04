import csv
import json
import configparser
from updownrecord import freecfg

from xml.etree.ElementTree import XMLParser
import xml.etree.ElementTree as ET

import io
import collections
import os
import copy

from django import forms
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.http import HttpResponse, Http404
from django.views.generic import View

from quickviews import ModelCreateView, CreateView


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
StructureData = collections.namedtuple('StructureData', ['name', 'detailfunc', 'qsfunc', 'mime'])


def _validate_keymap(class_name, model_class, key_map):
    fieldnames = [f.name for f in model_class._meta.fields]
    for k in key_map.keys():
        if k not in fieldnames:
            raise ImproperlyConfigured('{} key_map attribute states db key not declared as model field name. key:"{}", model:{}'.format(
                class_name,
                k,
                model_class._meta.object_name
                ))

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
    @param use_querysets override the pk_url_kwarg for query handling.
    @param include_pk if False will remove the pk field from downloads.
    @param model_in_filename prefix the filename with the model name
    '''
    #! size limit
    #data_type="csv"
    data_type="json"
    #data_type="cfg"
    #data_type="xml"
    model_class = None
    pk_url_kwarg = 'pk'
    use_querysets = False
    queryset = None
    queryset_url_page_kwarg = 'page'
    queryset_page_size = 25
    selection_id = 'query'
    include_pk = True
    key_map = {}
    model_in_filename = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if (not (self.data_type in self._data_type_map)):
            raise ImproperlyConfigured('{} data_type not found in data types. data_type:"{}", valid data types:{}'.format(
                self.__class__.__name__,
                self.data_type,
                ', '.join(self._data_type_map.keys()),
                ))
             
        if (self.key_map):
            _validate_keymap(self.__class__.__name__, self.model_class, self.key_map)

                        
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
        if (self.key_map):
            data = collections.OrderedDict((self.key_map[k], v) for k, v in data.items() if k in self.key_map)
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

    def dict2freecfg_detail(self, detail_dict):
        b = freecfg.Builder()
        b.mkentries(detail_dict)
        return b.result()
                
    def dict2freecfg_queryset(self, queryset_array):
        #b = []
        #for idx, detail_dict in enumerate(queryset_array):
            #b.append('[{}]\n'.format(idx))
            #self._dict2cfg_obj(b, detail_dict)
        #return ''.join(b)
        b = freecfg.Builder()
        for idx, detail_dict in enumerate(queryset_array):
            b.mksection(str(idx))
            b.mkentries(detail_dict)
        return b.result()

        
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
        'cfg' : StructureData(
            name='cfg', 
            detailfunc=dict2cfg_detail, 
            qsfunc=dict2cfg_queryset,
            mime='text/plain'
        ),
        'freecfg' : StructureData(
            name='freecfg', 
            detailfunc=dict2freecfg_detail, 
            qsfunc=dict2freecfg_queryset,
            mime='text/plain'
        ),
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
    'freecfg': 'freecfg',
    'ini': 'cfg',
    'xml': 'xml'
}


import re
from configparser import ParsingError

class UploadRecordView(CreateView):
    '''
    Simple form to upload structured data to a model.
    
    The data must fit some loose conditions, outlines in detail in the
    app documentation.

    @param data_types limit the dta types (beyond the ability to process)
    @param file_size_limit in MB (e.g. value = 2 is 2MB)
    @param default for form of input file. Tried if MIME and and extension fail.
    @param key_map a dict to map object field names -> keys from an
    uploaded file. Can be used to remove keys (don't list them).  
    '''
    model_class = None
    data_types = ['cfg', 'freecfg', 'csv', 'json', 'xml']
    # for data type
    default = None
    force_insert = False
    file_size_limit = 2
    key_map = {}
    popnone_normalize = True
    #success_url = self.return_url()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if (self.default and (not (self.default in self.data_types))):
            raise ImproperlyConfigured('{} default not found in data types. default:"{}", valid data types:{}'.format(
                self.__class__.__name__,
                self.default,
                ', '.join(self.data_types),
                ))
             
        if (self.key_map):
            _validate_keymap(self.__class__.__name__, self.model_class, self.key_map)
               
        
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
            extension = None
            try:
                extension = base.rsplit('.', 1)[1]
            except IndexError:
                if (self.default):
                    extension = self.default
                else:
                    raise Http404("Failed to identify uploaded file from mime and no extension or default. mime:'{0}' extension:'{1}'".format(mime, extension))
                
            tpe = _extension_map.get(extension)
            if (not tpe):
                raise Http404("Failed to identify uploaded file from mime or extension. mime:'{0}' extension:'{1}'".format(mime, extension))
        if (not(tpe in self.data_types)):
             raise Http404('File type not accepted.')
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
                        
    def cfg2python(self, uploadfile):
        parser = configparser.ConfigParser()
        parser.read_file(self.binaryToUTF8Iter(uploadfile))
        sections = parser.sections()
        if (len(sections) > 1):
            l = []
            for section_name in sections:
                l.append(self._cfg2dict(parser, section_name))
            return l 
        else:
            return self._cfg2dict(parser, sections[0])
            
    def freecfg2python(self, uploadfile):
        #b = {}
        #key = ''
        #holding = []
        #startRE = re.compile('^(\w+)\s?=\s*(.*)$')
        #commentRE = re.compile('^\s*#')
        #it = self.binaryToUTF8Iter(uploadfile)
        ## parse
        #for line in it:
            #if (line):
                #mo = commentRE.match(line)
                #if (not mo):
                    #mo = startRE.match(line)
                    #if (mo):
                        #key = mo.group(1)
                        #holding = [mo.group(2)]
                        #break   
                    #else:
                        #raise ParsingError('first significant line must contain a key')
        #for line in it:
            #mo = commentRE.match(line)
            #if (mo):
                #continue
            #mo = startRE.match(line)
            #if (mo):
                #value = ''.join(holding)
                #b[key] = value.strip()  
                #key = mo.group(1)
                #holding = [mo.group(2)]
            #else:
                #holding.append(line)
        #b[key] = ''.join(holding)
        #return b
        p = freecfg.Parser(seq_is_dict=False)
        pdata = p.parse_binary_iter(uploadfile)
        # if only one, strip the object_dict out of the list
        if (len(pdata) > 1):
            return pdata
        else:
            return pdata[0]
                          
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
        'freecfg' : StructureData(name='freecfg', detailfunc=freecfg2python, qsfunc=None, mime='text/plain'),
        'csv' : StructureData(name='csv', detailfunc=csv2python, qsfunc=None, mime='text/csv'),
        'json' : StructureData(name='json', detailfunc=json2python, qsfunc=None, mime='application/json'),
        'xml' : StructureData(name='xml', detailfunc=xml2python, qsfunc=None, mime='text/xml')
    }

    def normalize(self, data):
        return data
        
    def save_action(self, data):
        if (self.key_map):
            data = {k:data[v] for k, v in self.key_map.items() if v in data}
        if (self.popnone_normalize):
            data = {k:v for k, v in data.items() if v}
        data = self.normalize(data)
        obj = self.model_class(**data)
        obj.save(force_insert=self.force_insert)
                  
    def success_action(self, form):
        obj = None
        uploadfile = self.request.FILES['data']
        data_type = self.get_type(uploadfile)
        structdata = self._data_type_map[data_type]
        data = structdata.detailfunc(self, uploadfile)
        if isinstance(data, list):
            #?use bulk save?
            #print('data')
            #print(str(data))
            for obj_dict in data:
                self.save_action(obj_dict)
        else:
            #print('data')
            #print(str(data))
            self.save_action(data)
        return obj

     
