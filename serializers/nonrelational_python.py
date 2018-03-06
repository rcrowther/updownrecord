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
#from .nonrelational_base import NonrelationalSerializer
from updownrecord.serializers import nonrelational_base
from django.core.serializers.base import DeserializationError



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
        #obj_pk = obj.pk
        #if obj_pk is not None:
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


#def NonrelationalDeserializer(object_list, *, using=DEFAULT_DB_ALIAS, ignorenonexistent=False, **options):
    #field_names_cache = {}  # model_class: <list of field_names>

    #for d in object_list:
        ## Look up the model and starting build a dict of data for it.
        #try:
            ##model_class = _get_model(d["model"])
            #model_class = self.get_model_class(d["model"])
        #except base.DeserializationError:
            #if ignorenonexistent:
                #continue
            #else:
                #raise
        #data = {}
        #if 'pk' in d:
            #try:
                ##data[model_class._meta.pk.attname] = model_class._meta.pk.to_python(d.get('pk'))
                #data[model_class._meta.pk.attname] = self.pk_to_python(model_class, d.get('pk'))
            #except Exception as e:
                #raise base.DeserializationError.WithData(e, d['model'], d.get('pk'), None)
        ##m2m_data = {}

        #if model_class not in field_names_cache:
            ##field_names_cache[model_class] = {f.name for f in model_class._meta.get_fields()}
            #field_names_cache[model_class] = self.field_names(model_class)
        #field_names = field_names_cache[model_class]

        ## Handle each field
        #for (field_name, field_value) in d["fields"].items():

            #if ignorenonexistent and field_name not in field_names:
                ## skip fields no longer on model
                #continue

            #field = model_class._meta.get_field(field_name)

            #if(self.field_is_nonrelational(self.ignore, model_class, field)):
            ## Handle M2M relations
            ##if field.remote_field and isinstance(field.remote_field, models.ManyToManyRel):
                ##model = field.remote_field.model
                ##if hasattr(model._default_manager, 'get_by_natural_key'):
                    ##def m2m_convert(value):
                        ##if hasattr(value, '__iter__') and not isinstance(value, str):
                            ##return model._default_manager.db_manager(using).get_by_natural_key(*value).pk
                        ##else:
                            ##return model._meta.pk.to_python(value)
                ##else:
                    ##def m2m_convert(v):
                        ##return model._meta.pk.to_python(v)

                ##try:
                    ##m2m_data[field.name] = []
                    ##for pk in field_value:
                        ##m2m_data[field.name].append(m2m_convert(pk))
                ##except Exception as e:
                    ##raise base.DeserializationError.WithData(e, d['model'], d.get('pk'), pk)

            ### Handle FK fields
            ##elif field.remote_field and isinstance(field.remote_field, models.ManyToOneRel):
                ##model = field.remote_field.model
                ##if field_value is not None:
                    ##try:
                        ##default_manager = model._default_manager
                        ##field_name = field.remote_field.field_name
                        ##if hasattr(default_manager, 'get_by_natural_key'):
                            ##if hasattr(field_value, '__iter__') and not isinstance(field_value, str):
                                ##obj = default_manager.db_manager(using).get_by_natural_key(*field_value)
                                ##value = getattr(obj, field.remote_field.field_name)
                                ### If this is a natural foreign key to an object that
                                ### has a FK/O2O as the foreign key, use the FK value
                                ##if model._meta.pk.remote_field:
                                    ##value = value.pk
                            ##else:
                                ##value = model._meta.get_field(field_name).to_python(field_value)
                            ##data[field.attname] = value
                        ##else:
                            ##data[field.attname] = model._meta.get_field(field_name).to_python(field_value)
                    ##except Exception as e:
                        ##raise base.DeserializationError.WithData(e, d['model'], d.get('pk'), field_value)
                ##else:
                    ##data[field.attname] = None

            ## Handle all other fields
           ##else:
                #try:
                    #data[field.name] = field.to_python(field_value)
                #except Exception as e:
                    #raise base.DeserializationError.WithData(e, d['model'], d.get('pk'), field_value)

        #obj = base.build_instance(model_class, data, using)
        #yield base.DeserializedObject(obj)


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
                    raise base.DeserializationError.WithData(e, model_path, pk, field_value)

        obj = base.build_instance(model_class, data, self.db)
        return base.DeserializedObject(obj)
