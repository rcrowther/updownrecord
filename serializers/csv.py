import csv


from django.db import DEFAULT_DB_ALIAS
#from django.core.serializers import base
from .nonrelational_python import NonrelationalSerializer, NonrelationalDeserializer


class Serializer(NonrelationalSerializer):
    dialect='excel'

    def serialize(self, queryset, model_class, *args, stream=None, fields=None,
                  use_natural_primary_keys=False, progress_output=None, object_count=0, **options):
        self.model_class = model_class
        #! test is model
        return super().serialize(queryset, *args, stream=stream, fields=fields,
                  use_natural_primary_keys=use_natural_primary_keys, progress_output=progress_output, object_count=object_count, **options)

    def start_serialization(self):
        """
        Start serialization -- open the XML document and the root element.
        """
        #self.obj_dict = {} 
        #self.model_class = model_class
        fieldnames = ['pk']
        fieldnames.extend(self.field_names(self.model_class))
        self.writer = csv.DictWriter(self.stream, fieldnames=fieldnames, dialect=self.dialect)
        self.writer.writeheader()

    def end_serialization(self):
        pass
        
    #def start_object(self, obj):
    #    pass
          
    def end_object(self, obj):
        #test object is the model_class
        d = self.get_dump_object(obj)
        #print('dump obj:\n' + str(d))
        obj_dict = d['fields']
        #obj_dict['model'] = do['model']
        obj_dict['pk'] = d['pk']
        self.writer.writerow(obj_dict)

    def getvalue(self):
        # Grandparent super
        return super(NonrelationalSerializer, self).getvalue()
        
#class Deserializer(SingleModelKeyMapDeserializer):
    #dialect = 'excel'
    #has_header = True
    
    #def __init__(self, stream_or_string, model_class, dialect=None, has_header=True, key_map=None, pop_false=True,*args, **options):
        #super().__init__(stream_or_string, model_class, *args, key_map=key_map, pop_false=pop_false, **options)
        #if (dialect):
            #self.dialect = dialect
        #if (has_header):
            #self.has_header = has_header

        #if(self.has_header):
            #self.reader = csv.DictReader(self.stream, dialect=self.dialect)
        #else:
            #field_names = self.local_field_names()
            #field_names.append('pk')
            #self.reader = csv.DictReader(self.stream, fieldnames=field_names, dialect=self.dialect)

    #def __next__(self):
        #for row in self.reader:
            #return self._handle_object(row)
        #raise StopIteration

    #def _handle_object(self, row):
        ##mrow = {self.map_key(k) : v for k, v in row.items()}
        #mrow = {self.map_key(k) : v for k, v in row.items() if (v or (not self.pop_false))}
        #obj = self.model_class(**mrow)
        #return base.DeserializedObject(obj)

class Deserializer(NonrelationalDeserializer):
    dialect = 'excel'
    has_header = True
    
    def __init__(self, stream_or_string, model_class, *args, using=DEFAULT_DB_ALIAS, ignorenonexistent=False, dialect=False, has_header=True, **options):
        self.model_class = model_class
        self.model_path = str(self.model_class._meta)
        if (dialect):
            self.dialect = dialect
        if (has_header):
            self.has_header = has_header
        super().__init__(stream_or_string, *args, using=using, ignorenonexistent=ignorenonexistent, **options)

    def get_object_list(self, stream):
        if(self.has_header):
            return csv.DictReader(self.stream, dialect=self.dialect)
        else:
            field_names = self.field_names(self.model_class)
            field_names.append('pk')
            return csv.DictReader(self.stream, fieldnames=field_names, dialect=self.dialect)

    def model_path_from_data(self, d):
        print('data:\n' + str(d))
        return self.model_path

    def get_pk_from_data(self, d):
        return d.get('pk')

    def fields_from_data(self, d):
        d.pop('pk')
        return d
