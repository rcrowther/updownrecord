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
from .nonrelational_base import NonrelationalSerializer



class Serializer(NonrelationalSerializer):
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
        self._current = OrderedDict()

    def end_object(self, obj):
        self.objects.append(self.get_dump_object(obj))
        self._current = None

    def get_dump_object(self, obj):
        data = OrderedDict([('model', str(obj._meta))])
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

