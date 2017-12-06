import csv
import json
import collections
from itertools import chain
import io

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
#? save ranges too?
#? headers in CSV?
#? do init files?
StructureData = collections.namedtuple('StructureData', ['name', 'structfunc', 'mime'])

class DownloadView(View):
    #! size limit
    #data_type="csv"
    data_type="json"
    model_class = ChristmasSong
        
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

                
    _data_type_map = {
        'csv' : StructureData(name='csv', structfunc=dict2csv, mime='text/csv'),
        'json' : StructureData(name='json', structfunc=dict2json, mime='application/json')
    }
        
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
        dstfilename = '{0}-{1}.{2}'.format(
            self.model_class._meta.model_name, 
            str(pk), 
            structdata.name
        )
        # set content and type
        response = HttpResponse(data_text, content_type=structdata.mime)
        # Add the treat-as-file header
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(dstfilename)
        return response
    
    
# get the data
#interperate as csv etc.
#form a model
#save

# class factory?
# UploadRecordView(   model=???, data_type=None)
    
class UploadRecordForm(forms.Form):
    data = forms.FileField(label='Data')
    
class UploadRecordCreate(CreateView):
    # guess or state
    # encoding = CSV, JSON
    # what to do with wrong values?
    form_class = UploadRecordForm
    fields = ['data']
    model_class = ChristmasSong
    data_types = ['csv', 'json']
    

    #success_url = self.return_url()
    #def handle_uploaded_file(self, f):
        #with open('some/file/name.txt', 'wb+') as destination:
            #for chunk in f.chunks():
                #destination.write(chunk)
    
    def verify_type(self, fileUploadObject):
        mime = fileUploadObject.content_type
        # application/octet-stream
        mimesplit = mime.split('/')
        #if (mimesplit[0] != 'text'):
        #    raise ValidationError("Uploaded data must be text mime:'{}'".format(mime))
        #if (not(mimesplit[1] in self.data_types)):
        #    raise ValidationError("Uploaded data must be from '{0}' mime:'{1}'".format(','.join(self.data_types), mime))            
        return mimesplit[1]
        
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

    _data_type_map = {
        'csv' : StructureData(name='csv', structfunc=csv2dict, mime='text/csv'),
        'json' : StructureData(name='json', structfunc=json2dict, mime='application/json')
    }    
    def fail_action(self, form):
        print('fail')
        print(form)

    def success_action(self, form):
        obj = None
        #try:
        data = self.request.FILES['data']
        print('sucess:')
        data_type = self.verify_type(data)
        print(str(data.content_type))
        #UploadedFile.charset¶
        #for line in data:
        #    print(line)
        structdata = self._data_type_map[data_type]
        data_dict = structdata.structfunc(self, data)
        #d = self.csv2dict(data)
        obj = self.model_class(**data_dict)
        print(str(obj))
        #obj.save()
        #except Exception as err:
            #! fix
            #! write error message
            #err.__traceback__.print_tb()
        #    traceback.print_tb(err.__traceback__, limit=1)
        return obj

     
