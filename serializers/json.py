

import datetime
import decimal
import json
import uuid

from django.core.serializers.base import DeserializationError
#from django.core.serializers.python import (
#    Deserializer as PythonDeserializer, Serializer as PythonSerializer,
#)
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.duration import duration_iso_string
from django.utils.functional import Promise
from django.utils.timezone import is_aware

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
        json.dump(self.get_dump_object(obj), self.stream, **self.json_kwargs)
        self._current = None

    def getvalue(self):
        # Grandparent super
        return super(NonrelationalSerializer, self).getvalue()




#def Deserializer(stream_or_string, **options):
    #"""Deserialize a stream or string of JSON data."""
    #if not isinstance(stream_or_string, (bytes, str)):
        #stream_or_string = stream_or_string.read()
    #if isinstance(stream_or_string, bytes):
        #stream_or_string = stream_or_string.decode()
    #try:
        #objects = json.loads(stream_or_string)
        #yield from NonrelationalDeserializer(objects, **options)
    #except (GeneratorExit, DeserializationError):
        #raise
    ##except Exception as ex:
    ##    raise DeserializationError() from ex

class Deserializer(NonrelationalDeserializer):
    def get_object_list(self, stream):
        return json.loads(stream.read())

    def model_path_from_data(self, d):
        return d['model']

    def get_pk_from_data(self, d):
        return d.get('pk')

    def fields_from_data(self, d):
        return d['fields']
