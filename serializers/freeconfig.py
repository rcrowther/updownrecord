from django.apps import apps
from django.core.serializers import base

from .keymap_base import KeyMapSerializer, KeyMapDeserializer
from .freecfg import Writer, DictReader



class Serializer(KeyMapSerializer):

    def start_serialization(self):
        self.obj_dict = {} 
        self.writer = Writer(self.stream)

    def end_serialization(self):
        pass
        
    def start_object(self, obj):
        if not hasattr(obj, "_meta"):
            raise base.SerializationError("Non-model object (%s) encountered during serialization" % type(obj))
        self.writer.mksection(str(obj._meta))
        self.obj_dict = {} 
        obj_pk = obj.pk
        if obj_pk is not None:
            self.obj_dict = {'pk': str(obj_pk)}
          
    def end_object(self, obj):
        self.writer.mkentries(self.obj_dict)
                 
    def handle_field(self, obj, field):
        key = self.map_key(self.model_name(obj), field.name)
        self.obj_dict[key] = field.value_to_string(obj)



class Deserializer(KeyMapDeserializer):
    def __init__(self, stream_or_string, key_map=None, pop_false=True,*args, **options):
        super().__init__(stream_or_string, key_map=key_map, pop_false=pop_false, **options)
        self.reader = DictReader(self.stream)

    def __next__(self):
        for event in self.reader:
            return self._handle_object(event)
        raise StopIteration

    def _handle_object(self, event):
        mdata = {self.map_key(event.title, k) : v for k, v in event.data.items() if (v or (not self.pop_false))}
        model = apps.get_model(event.title)
        obj = model(**mdata)
        return base.DeserializedObject(obj)
