import csv

from django.db import DEFAULT_DB_ALIAS
from django.core.exceptions import ImproperlyConfigured

from .nonrelational_python import NonrelationalSerializer, NonrelationalDeserializer


class Serializer(NonrelationalSerializer):
    dialect='excel'
    model_class = None
        
    def serialize(self, queryset, *args, stream=None, fields=None, model_class=None,
                  use_natural_primary_keys=False, progress_output=None, object_count=0, **options):
        if (model_class is not None): 
            self.model_class = model_class
        if (self.model_class is None): 
            raise ImproperlyConfigured('Must have a "model_class" attibute.')  
        #! test is model
        return super().serialize(queryset, *args, stream=stream, fields=fields,
                  use_natural_primary_keys=use_natural_primary_keys, progress_output=progress_output, object_count=object_count, **options)

    def start_serialization(self):
        """
        Start serialization -- open the XML document and the root element.
        """
        fieldnames = ['pk']
        fieldnames.extend(self.field_names(self.model_class))
        self.writer = csv.DictWriter(self.stream, fieldnames=fieldnames, dialect=self.dialect)
        self.writer.writeheader()

    def end_serialization(self):
        pass

    def start_object(self, obj):
        self.verify_object_from_model_class(self.model_class, obj)
        super().start_object(obj)

    def end_object(self, obj):
        # test object is the model_class
        self.verify_object_from_model_class(self.model_class, obj)
        d = self.get_dump_object(obj)
        obj_dict = d['fields']
        obj_dict['pk'] = d['pk']
        self.writer.writerow(obj_dict)

    def getvalue(self):
        # Grandparent super
        return super(NonrelationalSerializer, self).getvalue()
        


class Deserializer(NonrelationalDeserializer):
    dialect = 'excel'
    has_header = True
    model_class = None
    
    def __init__(self, stream_or_string, *args, using=DEFAULT_DB_ALIAS, model_class=None, ignorenonexistent=False, dialect=False, has_header=True, **options):
        if (model_class is not None): 
            self.model_class = model_class
        if (self.model_class is None): 
            raise ImproperlyConfigured('Must have a "model_class" attribute.')        
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
        return self.model_path

    def get_pk_from_data(self, d):
        return d.get('pk')

    def fields_from_data(self, d):
        d.pop('pk')
        return d
