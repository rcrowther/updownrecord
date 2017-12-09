import csv
import json
import configparser
from xml.etree.ElementTree import XMLParser
import xml.etree.ElementTree as ET

import io
import collections
import os
from itertools import chain

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
#? use pk or not
#? save ranges too
#? guess or state for upload
#? state or offer for download
#? how about updating too?
#? size limitations
#? Admin protection
#? check charsets
#? Just a parser for csv and JSON?
#? data can be more abstract?
#? Should handle with/without pks
#? allow args (e.g dialect to CSV dictwriter)
#? redirect or something on DownloadView
#? add app name as well as model name to the pk
#? queryset, not 'to'. How to pass as parameter?
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



class DownloadView(View):
    '''
    Offered filenames are the pk of the source record, or for a
    queryset, the pk range. They are not unique identifiers. If you wish
    to prefix the offered filename with the model name, which makes the 
    filename closer to a unique name, set 'model_in_filename=True'.
    @param model_in_filename prefix the filename with the model name
    '''
    #! size limit
    data_type="csv"
    #data_type="json"
    #data_type="cfg"
    #data_type="xml"
    model_class = ChristmasSong
    pk_url_kwarg = 'pk'
    queryset_url_kwarg = None
    queryset = None
    include_pk = True
    #include_pk = False
    model_in_filename = False
    
    #if callable(list_filter):

    def model_name(self):
        return self.model_class._meta.model_name
        
    def model_fieldnames(self):
        '''
        Names of usable model fields.
        This method should reject abstract and foreign fields.
        It also removes the pk field, if not specified in 'include_pk'.
        
        @return model fieldnames to use.
        '''
        opts = self.model_class._meta
        fields = [f.name for f in chain(opts.concrete_fields, opts.private_fields)]
        if (not self.include_pk):
            fields.remove(opts.pk.name)
        return fields
        
    def obj_to_dict(self, instance, fields=None):
        """
        Return a dict containing the data in ``instance``.
        """
        opts = instance._meta
        pk_name = opts.pk.name
        # maintain some order, even if not critical
        data = collections.OrderedDict()
        for f in chain(opts.concrete_fields, opts.private_fields):
            if (fields and (f.name not in fields)):
                continue
            if ((f.name == pk_name) and (not self.include_pk)):
                continue
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
      
    def destination_filename(self, pk, extension, to=None):
        modelstr = ''
        if (self.model_in_filename):
            modelstr = '{}_'.format(self.model_class._meta.model_name)
        tostr = ''
        if (to):
            tostr = '-{}'.format(pk)
        filename = '{0}{1}{2}.{3}'.format(
            modelstr, 
            str(pk),
            tostr, 
            extension
        )
        return filename
            
    def get(self, request, *args, **kwargs):
        pk = int(kwargs[self.pk_url_kwarg])
        structdata = self._data_type_map[self.data_type]
        if (self.queryset_url_kwarg):
            selector = int(kwargs[self.queryset_url_kwarg])
            if (not isinstance(selector, dict)):
                raise ImproperlyConfigured(
                'Queryset selector must be a dict'
                )
            qs = self.model_class.objects.filter(**selector)
            data_dict = [self.obj_to_dict(obj) for obj in qs]
            data_text = structdata.qsfunc(self, data_dict)
        else:
            obj = self.model_class.objects.get(pk=pk)
        #print(str(obj))
            data_dict = self.obj_to_dict(obj)
            #print(str(data_dict))
            data_text = structdata.detailfunc(self, data_dict)
        print('data_text:')
        print(str(data_text))
        dstfilename = self.destination_filename(pk, structdata.name)
        # set content and type
        response = HttpResponse(data_text, content_type=structdata.mime)
        # Add the treat-as-file header
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(dstfilename)
        return response
    
    


# class factory?
# UploadRecordView(   model=???, data_type=None)

#FileTypeData = collections.namedtuple('FileTypeData', ['name', 'mime', 'extension'])
    
class UploadRecordForm(forms.Form):
    data = forms.FileField(label='Data')


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



class UploadRecordSave(CreateView):
    '''
    '''
    form_class = UploadRecordForm
    fields = ['data']
    model_class = ChristmasSong
    data_types = ['csv', 'json', 'cfg']
    
    #success_url = self.return_url()
    #def handle_uploaded_file(self, f):
        #with open('some/file/name.txt', 'wb+') as destination:
            #for chunk in f.chunks():
                #destination.write(chunk)
    #? x
    def model_fieldnames(self):
        fields = [f.name for f in self.model_class._meta.get_fields()]
        fields.remove(self.model_class._meta.pk.name)
        return fields
        
                
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
              raise ValidationError("Failed to identify uploaded file from mime or extension mime:'{0}' extension:'{1}'".format(mime, extension))
        return tpe
        
    def binaryToUTF8Iter(self, fileUploadObject):
        for line in fileUploadObject:
            yield line.decode('utf-8')
            
    def binaryToUTF8Str(self, fileUploadObject):
        #! protect
        s = fileUploadObject.read()
        return s.decode('utf-8')
        
    def json2dict(self, data):
        decoder = json.JSONDecoder(strict=True, object_pairs_hook=collections.OrderedDict())
        return decoder.decode(self.binaryToUTF8Str(s))
        
    def csv2dict(self, data):
        # if CSV has headers, this reads ok
        reader = csv.DictReader(self.binaryToUTF8Iter(data))
        # Only need first line
        r = reader.__next__()
        #print('csv out:')
        #print(str(r))
        return r

    def cfg2dict(self, data):
        b = {}
        config = configparser.ConfigParser()
        config.read('example.ini')
        for instance in config.sections():
           ib = {}
           for field in model_fieldnames():
              ib[field] = config[instance][field]
           b[instance] = ib
        return b

    def cfg2dictInstance(self, uploadfile):
        b = {}
        #s = ''.join(uploadfile)
        config = configparser.ConfigParser()
        #config.read_string(s)
        config.read_file(self.binaryToUTF8Iter(uploadfile))
        print('model_fieldnames')
        print(str(self.model_fieldnames()))
        for field in self.model_fieldnames():
            b[field] = config[field]
        return b


    def xml2dictInstance(self, uploadfile):
        b = {}
        root = ET.fromstringlist(self.binaryToUTF8Iter(uploadfile))
        for child in root:
            b[child.tag] = child.text
        return b
                
    _data_type_map = {
        'csv' : StructureData(name='csv', detailfunc=csv2dict, qsfunc=None, mime='text/csv'),
        'json' : StructureData(name='json', detailfunc=json2dict, qsfunc=None, mime='application/json'),
        'cfg' : StructureData(name='cfg', detailfunc=cfg2dictInstance, qsfunc=None, mime='text/plain'),
        'xml' : StructureData(name='xml', detailfunc=xml2dictInstance, qsfunc=None, mime='text/xml')
    }    
    
    def fail_action(self, form):
        print('fail')
        print(form)

    def success_action(self, form):
        obj = None
        uploadfile = self.request.FILES['data']
        data_type = self.get_type(uploadfile)
        #print(str(uploadfile.content_type))
        #UploadedFile.charset¶
        #for line in data:
        #    print(line)
        structdata = self._data_type_map[data_type]
        data_dict = structdata.detailfunc(self, uploadfile)
        print('data_dict')
        print(str(data_dict))
        obj = self.model_class(**data_dict)
        #print(str(obj))
        #obj.save()
        return obj

     
