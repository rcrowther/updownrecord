import json

from django.core.serializers.base import DeserializationError
from django.core.serializers.json import DjangoJSONEncoder

from .nonrelational_python import NonrelationalSerializer, NonrelationalDeserializer


#NB Exact copy from Django, except for inheritance
class Serializer(NonrelationalSerializer):
    """Convert a queryset to JSON."""
    internal_use_only = False

    def _init_options(self):
        self._current = None
        self.json_kwargs = self.options.copy()
        self.json_kwargs.pop('stream', None)
        self.json_kwargs.pop('fields', None)
        if self.options.get('indent'):
            # Prevent trailing spaces
            self.json_kwargs['separators'] = (',', ': ')
        self.json_kwargs.setdefault('cls', DjangoJSONEncoder)

    def start_serialization(self):
        self._init_options()
        self.stream.write("[")

    def end_serialization(self):
        if self.options.get("indent"):
            self.stream.write("\n")
        self.stream.write("]")
        if self.options.get("indent"):
            self.stream.write("\n")

    def end_object(self, obj):
        # self._current has the field data
        indent = self.options.get("indent")
        if not self.first:
            self.stream.write(",")
            if not indent:
                self.stream.write(" ")
        if indent:
            self.stream.write("\n")
        d = self.get_dump_object(obj)

        json.dump(self.get_dump_object(obj), self.stream, **self.json_kwargs)
        self._current = None

    def getvalue(self):
        # Grandparent super
        return super(NonrelationalSerializer, self).getvalue()



class Deserializer(NonrelationalDeserializer):
    def get_object_list(self, stream):
        return json.loads(stream.read())

    def model_path_from_data(self, d):
        return d['model']

    def get_pk_from_data(self, d):
        return d.get('pk')

    def fields_from_data(self, d):
        return d['fields']
