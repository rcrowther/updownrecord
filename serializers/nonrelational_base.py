import re

from django.core.serializers import base
from django.apps import apps



class UnserializableContentError(ValueError):
    pass
    
    
class UtilityMixin():
    def ensure_string(self, stream_or_string, encoding):
        if not isinstance(stream_or_string, (bytes, str)):
            stream_or_string = stream_or_string.read()
        if isinstance(stream_or_string, bytes):
            stream_or_string = stream_or_string.decode(encoding)
        return stream_or_string
         
    def field_names(self, model_class):
      return {f.name for f in model_class._meta.concrete_model._meta.local_fields if f.serialize}

    def field_type(self, field):
        return field.get_internal_type()

    def model_path(self, obj):
        return str(obj._meta)
        
    def verify_object_from_model_class(self, model_class, obj):
        if not (obj._meta.model == model_class):
            raise base.SerializationError("Object {} given to a serialiser handling class {}".format( 
            type(obj), 
            model_class._meta.object_name
            ))
                
                
# NB: if ever these need altering, the code is mostly
# django.core.serializers.base.py, with the relational handling 
# overridden to error.
class NonrelationalSerializer(UtilityMixin, base.Serializer):
    """
    Abstract serializer base class.
    """
    encoding = 'utf-8'

    # some helpers
    def _verify_no_control_characters(self, content):
        if content and re.search(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]', content):
            # Fail loudly when content has control chars
            # See http://www.w3.org/International/questions/qa-controls
            raise UnserializableContentError("Control characters are not supported in this serializer")

    def escape(data, entities={}):
        """Escape strings in a string of data.
        Also checks for control characters, which will throw an 
        exception.
        
        You pass a dictionary as the entities parameter.  The keys and 
        values must be strings; each key will be replaced with its 
        value.
        """
        self._verify_no_control_characters(data)
        if entities:
            for key, value in entities.items():
                data = data.replace(key, value)
        return data

    def unescape(data, entities={}):
        """Unescape strings in a string of data.
        
        You pass a dictionary as the entities parameter.  The keys and 
        values must be strings; each key will be replaced with its 
        value.
        """
        if entities:
            for key, value in entities.items():
                data = data.replace(key, value)
        return data

    def verify_object_is_model(self, obj):
        if not hasattr(obj, "_meta"):
            raise base.SerializationError("Non-model object (%s) encountered during serialization" % type(obj))

    ## mechanism
    def serialize(self, queryset, *args, stream=None, fields=None,
                  use_natural_primary_keys=False, progress_output=None, object_count=0, **options):
        # NB: I do not know why the super() call can not do this, but 
        # it will not. Not in my rig, anyway. This code line replicates 
        # the super() line from a Django I have downloaded. R.C.
        stream = stream if stream is not None else self.stream_class()
        # This is new, an assertion of stringification and decoding.
        # While expensive, some parsers can not handle byte input.
        if ('encoding' in options):
            self.encoding = options.pop('encoding')
        string = self.ensure_string(stream, self.encoding)
        return super().serialize(queryset, *args, stream=stream, fields=fields, use_natural_foreign_keys=False,
                  use_natural_primary_keys=use_natural_primary_keys, progress_output=progress_output, object_count=object_count, **options)
        
    def handle_fk_field(self, obj, field):
        """
        Called to handle a ForeignKey field.
        """
        raise base.SerializationError("Non-relational serializer recieved object {} with a foreign key field {}".format(
            type(obj), 
            field.name
        ))

    def handle_m2m_field(self, obj, field):
        """
        Called to handle a ManyToManyField.
        """
        raise base.SerializationError("Non-relational serializer recieved object {} with a 'many to many' field {}".format(
            type(obj), 
            field.name
        ))




class NonrelationalDeserializer(UtilityMixin, base.Deserializer):
    ignore = False
    encoding = 'utf-8'
    
    def __init__(self, stream_or_string, **options):
        # This is new, an assertion of stringification and decoding.
        # While expensive, some parsers can not handle byte input.
        if ('encoding' in options):
            self.encoding = options.pop('encoding')
        string = self.ensure_string(stream_or_string, self.encoding)
        super().__init__(string, **options)

    ## helpers
    def get_model_class(self, model_path):
        if not model_path:
            raise base.DeserializationError(
                "Model path must exist, but given '{}'".format(
                model_path))
        try:
            return apps.get_model(model_path)
        except (LookupError, TypeError):
            raise base.DeserializationError(
                "Model path can not be found: path: {}".format(
                model_path))

    def pk_to_python(self, model_class, pk_str):
        return model_class._meta.pk.to_python(pk_str)

    def field_is_nonrelational(self, ignore, model_class, field):
        if (not field.remote_field):
            return True
        else:
            if (ignore):
                return False
            elif isinstance(field.remote_field, models.ManyToManyRel):
                    raise base.DeserializationError("Model contains a (not parsable) Many to Many field: model:{}: field:{}".format(
                        model_class._meta,
                        field_name
                    ))
            elif isinstance(field.remote_field, models.ManyToOneRel):
                    raise base.DeserializationError("Model contains a (not parsable) Many to One field: model:{}: field:{}".format(
                        model_class._meta,
                        field_name
                    ))
