
#from xml.etree.ElementTree import XMLParser
#import xml.etree.ElementTree as ET

from django.conf import settings

from django.core.serializers import base
from django.utils.xmlutils import (
    SimplerXMLGenerator, UnserializableContentError,
)

#def _validate_keymap(class_name, model_class, key_map):
    #fieldnames = [f.name for f in model_class._meta.fields]
    #for k in key_map.keys():
        #if k not in fieldnames:
            #raise ImproperlyConfigured('{} key_map attribute states db key not declared as model field name. key:"{}", model:{}'.format(
                #class_name,
                #k,
                #model_class._meta.object_name
                #))
#? do an indent thing. Can be general?
#? pk or not
class Serializer(base.Serializer):
    key_map = {}

    def __init__(self):
        #self.xml = SimplerXMLGenerator(self.stream, self.options.get("encoding", settings.DEFAULT_CHARSET))
        pass
        #if (self.key_map):
        #    _validate_keymap(self.__class__.__name__, self.model_class, self.key_map)


    #? Dry
    def model_name(self, obj):
        if not hasattr(obj, "_meta"):
            raise base.SerializationError("Non-model object (%s) encountered during serialization" % type(obj))
        return str(obj._meta)
        
    def indent(self, level):
        if self.options.get('indent') is not None:
            self.xml.ignorableWhitespace('\n' + ' ' * self.options.get('indent') * level)

    def start_serialization(self):
        """
        Start serialization -- open the XML document and the root element.
        """
        #self.stream.write('<?xml version = "1.0" encoding = "UTF-8"?>\n')
        #self.stream.write('<queryset>\n')
        self.xml = SimplerXMLGenerator(self.stream, self.options.get("encoding", settings.DEFAULT_CHARSET))
        self.xml.startDocument()
        self.xml.startElement("django-objects", {"version": "1.0"})

    def end_serialization(self):
        #self.stream.write('</queryset>\n')
        self.indent(0)
        self.xml.endElement("django-objects")
        self.xml.endDocument()
        
    def start_object(self, obj):
        if not hasattr(obj, "_meta"):
            raise base.SerializationError("Non-model object (%s) encountered during serialization" % type(obj))
        self.indent(1)
        self.xml.startElement("object", {'model': self.model_name(obj) })
        #self.stream.write('<object model="{}">\n'.format(self.model_name(obj)))
        obj_pk = obj.pk
        if obj_pk is not None:
            #self.stream.write('<field name="pk">{}</field>\n'.format(obj_pk))
            #self.xml.addQuickElement("field", contents=, attrs={'name': 'pk'})
            self.xml.startElement('field', {
                'name': 'pk'
            })
            self.xml.characters(str(obj_pk))
            self.xml.endElement("field")

    def end_object(self, obj):
        #self.stream.write('</object>\n')
        self.indent(1)
        self.xml.endElement("object")
        
    def handle_field(self, obj, field):
        #? DRY
        field_name = field.name
        k = self.key_map[fn] if (field_name in self.key_map) else field_name
        self.indent(2)
        self.xml.startElement('field', {
            'name': field_name
        })
        if getattr(obj, field_name) is not None:
            try:
                #? investigate this parser function
                #? does what?
                self.xml.characters(field.value_to_string(obj))
                #v = field.value_from_object(obj)
                #self.stream.write('<field name="{0}">{1}</field>\n'.format(k, v))
            except UnserializableContentError:
                raise ValueError("%s.%s (pk:%s) contains unserializable characters" % (
                    obj.__class__.__name__, fn, obj.pk))
        else:
            #self.stream.write('<field name="{0}">None</field>\n'.format(k))
            self.xml.addQuickElement("None")
        self.xml.endElement("field")


#from xml.etree.ElementTree import XMLParser
#import xml.etree.ElementTree as ET

from xml.dom import pulldom
#? could go in django_menus
from django.apps import apps

class Deserializer(base.Deserializer):
    def __init__(self, stream_or_string, **options):
        super().__init__(stream_or_string, **options)
        self.dom = pulldom.parse(self.stream)
        self.ignore = False

    def __next__(self):
        for event, node in self.dom:
            if event == "START_ELEMENT" and node.nodeName == "object":
                self.dom.expandNode(node)
                return self._handle_object(node)
        raise StopIteration

    def _handle_object(self, node):
        """Convert an <object> node to a DeserializedObject."""
        # Look up the model using the model loading mechanism. If this fails,
        # bail.
        Model = self._get_model_from_node(node, "model")

        # Start building a data dictionary from the object.
        data = {}
        field_names = {f.name for f in Model._meta.get_fields()}
        # Do the pk
        #obj_pk = obj.pk
        #    if obj_pk is not None:
        #        data['pk'] = str(obj_pk)
        for field_node in node.getElementsByTagName("field"):
            field_name = field_node.getAttribute("name")
            # If the field is missing the name attribute, bail
            if not field_name:
                raise base.DeserializationError("<field> node is missing the 'name' attribute")

            # Get the field from the Model. This will raise a
            # FieldDoesNotExist if, well, the field doesn't exist, which will
            # be propagated correctly unless ignorenonexistent or map is used.
            if self.ignore and field_name not in field_names:
                continue
            field = Model._meta.get_field(field_name)

            # Relation fields error or ignore
            if (field.remote_field and 
            (isinstance(field.remote_field, models.ManyToManyRel)
            or isinstance(field.remote_field, models.ManyToOneRel))
            ):
                if self.ignore:
                    continue
                else:
                    if field.remote_field and isinstance(field.remote_field, models.ManyToManyRel):
                        raise base.DeserializationError("<field> node is a (not parsable) Many to Many field")
                    else:
                        raise base.DeserializationError("<field> node is a (not parsable) Many to One foreign key field")
            else:
                #print('node:'  + str(field_node.childNodes))
                c = field_node.firstChild
                if (c):
                    value = field.to_python(c.data.strip())
                else:
                    value = None
                data[field.name] = value
        
        obj = Model(**data)
        return base.DeserializedObject(obj)

          
    def _get_model_from_node(self, node, attr):
        """
        Look up a model from a <object model=...> or a <field rel=... to=...>
        node.
        """
        model_identifier = node.getAttribute(attr)
        if not model_identifier:
            raise base.DeserializationError(
                "<%s> node is missing the required '%s' attribute"
                % (node.nodeName, attr))
        try:
            return apps.get_model(model_identifier)
        except (LookupError, TypeError):
            raise base.DeserializationError(
                "<%s> node has invalid model identifier: '%s'"
                % (node.nodeName, model_identifier))
