import io
from xml.dom import pulldom

#from django.apps import apps
from django.conf import settings
from django.core.serializers import base
#? could go in django_menus
#from django.apps import apps

from xml.dom import pulldom
#from xml.sax import handler
#from xml.sax.expatreader import ExpatParser as _ExpatParser
from django.db import DEFAULT_DB_ALIAS #, models

from .nonrelational_base import NonrelationalSerializer, NonrelationalDeserializer
from django.utils.xmlutils import (
    SimplerXMLGenerator, UnserializableContentError,
)

from django.core.serializers.xml_serializer import getInnerText, DefusedExpatParser

#? Things to learn here
#? use xml char stuff for csv and freeconf?
#? check meta
#? type from field
        
class Serializer(NonrelationalSerializer):        
    def indent(self, level):
        if self.options.get('indent') is not None:
            self.xml.ignorableWhitespace('\n' + ' ' * self.options.get('indent') * level)

    def start_serialization(self):
        self.xml = SimplerXMLGenerator(self.stream, self.options.get("encoding", settings.DEFAULT_CHARSET))
        self.xml.startDocument()
        self.xml.startElement("django-objects", {"version": "1.0"})
        
    def end_serialization(self):
        self.indent(0)
        self.xml.endElement("django-objects")
        self.xml.endDocument()
                
    def start_object(self, obj):
        self.verify_object_is_model(obj)
        
        self.indent(1)
        attrs = {'model': self.model_path(obj)}
        obj_pk = obj.pk
        if obj_pk is not None:
            attrs['pk'] = str(obj_pk)
        self.xml.startElement("object", attrs)
          
    def end_object(self, obj):
        self.indent(1)
        self.xml.endElement("object")
                         
    def handle_field(self, obj, field):
        self.indent(2)
        self.xml.startElement('field', {
            'name': field.name,
            'type': self.field_type(field),
        })
        
        if getattr(obj, field.name) is not None:
            try:
                self.xml.characters(field.value_to_string(obj))
            except UnserializableContentError:
                raise ValueError("%s.%s (pk:%s) contains unserializable characters" % (
                    obj.__class__.__name__, field.name, obj.pk))
        else:
            self.xml.addQuickElement("None")
        self.xml.endElement("field")




#? ignore on freeconf and csv (or remove?)
#? mapping as generic function
#? generic filter for field names?
#? generic block on relational fields?
#? generic field to python?
class Deserializer(NonrelationalDeserializer):
    def __init__(self, stream_or_string, *, using=DEFAULT_DB_ALIAS, ignorenonexistent=False, **options):
        super().__init__(stream_or_string, **options)
        self.event_stream = pulldom.parse(self.stream, self._make_parser())
        self.db = using
        self.ignore = ignorenonexistent

    def _make_parser(self):
        """Create a hardened XML parser (no custom/external entities)."""
        return DefusedExpatParser()

    #? update to match JSON and nonrelational_python
    def __next__(self):
        for event, node in self.event_stream:
            if event == "START_ELEMENT" and node.nodeName == "object":
                self.event_stream.expandNode(node)
                return self._handle_object(node)
        raise StopIteration


    def _handle_object(self, node):
        """Convert an <object> node to a DeserializedObject."""
        # Look up the model using the model loading mechanism. If this fails,
        # bail.
        model_path = node.getAttribute("model")
        model_class = self.get_model_class(model_path)

        # Start building a data dictionary from the object.
        data = {}
        if node.hasAttribute('pk'):
            data[model_class._meta.pk.attname] = self.pk_to_python(model_class,
                node.getAttribute('pk'))

        field_names = self.field_names(model_class)
        # Deserialize each field.
        for field_node in node.getElementsByTagName("field"):
            # If the field is missing the name attribute, bail
            field_name = field_node.getAttribute("name")
            if not field_name:
                raise base.DeserializationError("<field> node is missing the 'name' attribute")

            # Get the field from the Model. This will raise a
            # FieldDoesNotExist if, well, the field doesn't exist, which will
            # be propagated correctly unless ignorenonexistent=True is used.
            if self.ignore and field_name not in field_names:
                continue
            field = model_class._meta.get_field(field_name)

            # Do not handle relation fields.
            if(self.field_is_nonrelational(self.ignore, model_class, field)):
                if field_node.getElementsByTagName('None'):
                    value = None
                else:
                    value = field.to_python(getInnerText(field_node).strip())
                data[field.name] = value
                
        obj = base.build_instance(model_class, data, self.db)
        return base.DeserializedObject(obj)
