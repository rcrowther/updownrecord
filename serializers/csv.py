import csv

from django.core.serializers import base
from .keymap_base import SingleModelKeyMapSerializer, SingleModelKeyMapDeserializer


#? pk or not - yes
class Serializer(SingleModelKeyMapSerializer):
    dialect='excel'

    def start_serialization(self):
        """
        Start serialization -- open the XML document and the root element.
        """
        self.obj_dict = {} 
        field_names = self.local_field_names()
        field_names.append('pk')
        self.writer = csv.DictWriter(self.stream, fieldnames=field_names, dialect=self.dialect)
        self.writer.writeheader()

    def end_serialization(self):
        pass
        
    def start_object(self, obj):
        if not hasattr(obj, "_meta"):
            raise base.SerializationError("Non-model object (%s) encountered during serialization" % type(obj))
        # self.verify_object(obj)
        self.obj_dict = {} 
        obj_pk = obj.pk
        if obj_pk is not None:
            self.obj_dict = {'pk': str(obj_pk)}
          
    def end_object(self, obj):
        self.writer.writerow(self.obj_dict)
                 
    def handle_field(self, obj, field):
        key = self.map_key(field.name)
        self.obj_dict[key] = field.value_to_string(obj)



class Deserializer(SingleModelKeyMapDeserializer):
    dialect = 'excel'
    has_header = True
    
    def __init__(self, stream_or_string, model_class, dialect=None, has_header=True, key_map=None, pop_false=True,*args, **options):
        super().__init__(stream_or_string, model_class, *args, key_map=key_map, pop_false=pop_false, **options)
        if (dialect):
            self.dialect = dialect
        if (has_header):
            self.has_header = has_header

        if(self.has_header):
            self.reader = csv.DictReader(self.stream, dialect=self.dialect)
        else:
            field_names = self.local_field_names()
            field_names.append('pk')
            self.reader = csv.DictReader(self.stream, fieldnames=field_names, dialect=self.dialect)

    def __next__(self):
        for row in self.reader:
            return self._handle_object(row)
        raise StopIteration

    def _handle_object(self, row):
        #mrow = {self.map_key(k) : v for k, v in row.items()}
        mrow = {self.map_key(k) : v for k, v in row.items() if (v or (not self.pop_false))}
        obj = self.model_class(**mrow)
        return base.DeserializedObject(obj)
