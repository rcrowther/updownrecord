"""
A Python "serializer". Doesn't do much serializing per se -- just converts to
and from basic Python data types (lists, dicts, strings, etc.). Useful as a basis for
other serializers.
"""
from collections import OrderedDict

from django.apps import apps
from django.core.serializers import base
from django.db import DEFAULT_DB_ALIAS, models
from django.utils.encoding import is_protected_type
from updownrecord.serializers import nonrelational_base
from django.core.serializers.base import DeserializationError




# NB: if ever these need altering, the code for Serializer is like
# django.core.serializers.python.py, with no relational handling. The
# code for Deserializer is not similar at all, Django Deserializer uses 
# a generator method, this uses a class which complements the Srializer. 
class NonrelationalSerializer(nonrelational_base.NonrelationalSerializer):
    """
    Serialize a QuerySet to basic Python objects.
    """
    internal_use_only = True

    def start_serialization(self):
        self._current = None
        self.objects = []

    def end_serialization(self):
        pass

    def start_object(self, obj):
        self.verify_object_is_model(obj)
        self._current = OrderedDict()

    def end_object(self, obj):
        self.objects.append(self.get_dump_object(obj))
        self._current = None

    def get_dump_object(self, obj):
        data = OrderedDict([('model', self.model_path(obj))])
        if not self.use_natural_primary_keys or not hasattr(obj, 'natural_key'):
            data["pk"] = self._value_from_field(obj, obj._meta.pk)
        data['fields'] = self._current
        return data

    def _value_from_field(self, obj, field):
        value = field.value_from_object(obj)
        # Protected types (i.e., primitives like None, numbers, dates,
        # and Decimals) are passed through as is. All other values are
        # converted to string first.
        return value if is_protected_type(value) else field.value_to_string(obj)

    def handle_field(self, obj, field):
        self._current[field.name] = self._value_from_field(obj, field)

    def getvalue(self):
        return self.objects



class NonrelationalDeserializer(nonrelational_base.NonrelationalDeserializer):
    """
    Deserialize a stream to Django Model instances.
    Requires a get_object_list() method to return a list of Python dicts 
    used as data for generating Models. The dicts must have the form
    {model: pk: fields:}. The 'pk' attribute is otional.
    If no parser can return the dicts, then this class can not be 
    implemented.
    """
    field_names_cache = {}  # model_class: <list of field_names>

    def __init__(self, stream_or_string, *, using=DEFAULT_DB_ALIAS, ignorenonexistent=False, **options):
        super().__init__(stream_or_string, **options)
        ol = self.get_object_list(self.stream)
        self.data_it = ol.__iter__() 
        self.db = using
        self.ignore = ignorenonexistent
        
    def get_object_list(self, stream):
        raise NotImplementedError('subclasses of NonrelationalDeserializer must provide a get_object_list() method')
      
    def model_path_from_data(self, d):
        raise NotImplementedError('subclasses of NonrelationalDeserializer must provide a model_from_data() method')

    def get_pk_from_data(self, d):
        raise NotImplementedError('subclasses of NonrelationalDeserializer must provide a get_pk_from_data() method')

    def fields_from_data(self, d):
        raise NotImplementedError('subclasses of NonrelationalDeserializer must provide a fields_from_data() method')
      
    def __next__(self):
        d = self.data_it.__next__()
        
        # Look up the model using the model loading mechanism.
        model_path = None
        try:
            model_path = self.model_path_from_data(d)
            model_class = self.get_model_class(model_path)
        except base.DeserializationError:
            if self.ignore:
                return self.__next__()
            else:
                raise

        # Start building a data dictionary from the object.
        data = {}
        pk = self.get_pk_from_data(d)
        if (pk):
            try:
                data[model_class._meta.pk.attname] = self.pk_to_python(model_class, pk)
            except Exception as e:
                raise base.DeserializationError.WithData(e, model_path, pk, None)
        if model_class not in self.field_names_cache:
            self.field_names_cache[model_class] = self.field_names(model_class)
        field_names = self.field_names_cache[model_class]

        # Handle each field
        for (field_name, field_value) in self.fields_from_data(d).items():
            if self.ignore and field_name not in field_names:
                continue
            field = model_class._meta.get_field(field_name)

            # Do not handle relation fields.
            if(self.field_is_nonrelational(self.ignore, model_class, field)):
                try:
                    data[field.name] = field.to_python(field_value)
                except Exception as e:
                    raise base.DeserializationError("{}: ({}:pk={}) field:'{}': field_value:'{}'".format(
                        e, 
                        model_path, 
                        pk, 
                        field_name,
                        field_value
                    ))

        obj = base.build_instance(model_class, data, self.db)
        return base.DeserializedObject(obj)
