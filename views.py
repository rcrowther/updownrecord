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
#? use pk or not
#? save ranges too
#? headers in CSV
#? guess or state for upload
#? state or offer for download
#? how about updating too?
#? size limitations
#? Admin protection
#? check charsets
#? XML
#? Just a parser for csv and JSON?
#? data can be more abstract?
#? Should handle with/without pks

StructureData = collections.namedtuple('StructureData', ['name', 'structfunc', 'mime'])



class DownloadView(View):
    #! size limit
    #data_type="csv"
    #data_type="json"
    #data_type="cfg"
    data_type="xml"
    model_class = ChristmasSong
    model_in_filename = False
    
    def model_name(self):
        return self.model_class._meta.model_name
        
    def model_to_dict(self, instance, fields=None):
        """
        Return a dict containing the data in ``instance``.
        """
        opts = instance._meta
        pk_name = opts.pk.name
        data = {}
        for f in chain(opts.concrete_fields, opts.private_fields):
            if fields and f.name not in fields:
                continue
            if f.name == pk_name:
                continue
            data[f.name] = f.value_from_object(instance)
        return data
        
    def dict2csv(self, data_dict):
        #print(str(data_dict))
        fields = [f.name for f in self.model_class._meta.get_fields()]
        fields.remove(self.model_class._meta.pk.name)
        print(str(fields))
        strB = io.StringIO()
        writer = csv.DictWriter(strB, fieldnames=fields)
        #{'gift': 'Turtle doves'}

        # Only need first line
        writer.writerow(data_dict)
        writer.writerow({'gift': 'Dogs a baying'})
        print('strB:')
        #print(str(strB. getvalue()))

        print('csv out:')
        #strB.flush()
        r = strB.getvalue()
        strB.close()
        print(str(r))
        return ''.join(r)

        
    def dict2json(self, data_dict):
        encoder = json.JSONEncoder(ensure_ascii=False)
        return encoder.encode(data_dict)

    def dict2cfg(self, data_dict):
        r = None
        config = configparser.ConfigParser()
        config['DEFAULT'] = data_dict
        with io.StringIO() as configfile:
            config.write(configfile)
            r = configfile.getvalue()
        return r

    def dict2xml(self, data_dict):
        b = []
        b.append('<?xml version = "1.0" encoding = "UTF-8"?>')
        #! put the id as an attribute
        b.append('<{}>'.format( self.model_name()))
        for k, v in data_dict.items():
            b.append('<{0}>{1}</{0}>'.format(k, v))
        b.append('</{}>'.format( self.model_name()))
        return ''.join(b)


    _data_type_map = {
        'csv' : StructureData(name='csv', structfunc=dict2csv, mime='text/csv'),
        'json' : StructureData(name='json', structfunc=dict2json, mime='application/json'),
        'cfg' : StructureData(name='cfg', structfunc=dict2cfg, mime='text/plain'),
        'xml' : StructureData(name='xml', structfunc=dict2xml, mime='text/xml'),
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
        pk = int(kwargs['pk'])
        obj = self.model_class.objects.get(pk=pk)
        #print(str(obj))
        data_dict = self.model_to_dict(obj)
        print(str(data_dict))
        structdata = self._data_type_map[self.data_type]
        data_text = structdata.structfunc(self, data_dict)
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

class UploadRecordCreate(CreateView):
    form_class = UploadRecordForm
    fields = ['data']
    model_class = ChristmasSong
    data_types = ['csv', 'json', 'cfg']
    
    #success_url = self.return_url()
    #def handle_uploaded_file(self, f):
        #with open('some/file/name.txt', 'wb+') as destination:
            #for chunk in f.chunks():
                #destination.write(chunk)
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
        #print(str(data))
        fields = [f.name for f in self.model_class._meta.get_fields()]
        fields.remove(self.model_class._meta.pk.name)
        #print(str(fields))
        reader = csv.DictReader(self.binaryToUTF8Iter(data), fieldnames=fields)
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
        'csv' : StructureData(name='csv', structfunc=csv2dict, mime='text/csv'),
        'json' : StructureData(name='json', structfunc=json2dict, mime='application/json'),
        'cfg' : StructureData(name='cfg', structfunc=cfg2dictInstance, mime='text/plain'),
        'xml' : StructureData(name='xml', structfunc=xml2dictInstance, mime='text/xml')
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
        data_dict = structdata.structfunc(self, uploadfile)
        print('data_dict')
        print(str(data_dict))
        obj = self.model_class(**data_dict)
        #print(str(obj))
        #obj.save()
        return obj

     
