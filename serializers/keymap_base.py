from django.core.serializers import base
from django.core.exceptions import ImproperlyConfigured

      

class MultiModelMixin():
    # model_name->field_name->custom key
    key_map = {}

    def model_name(self, obj):
        if not hasattr(obj, "_meta"):
            raise base.SerializationError("Non-model object (%s) encountered during serialization" % type(obj))
        return str(obj._meta)
     
    def local_field_names(self, obj):
        concrete_model = obj._meta.concrete_model
        return [field.name for field in concrete_model._meta.local_fields]

    def field_names(self, obj):
        return [field.name for field in obj._meta.fields]
        
    def map_key(self, model_name, original_key):
        '''
        Map original field key to custom key.
        @return new key. If fails, original key.
        '''
        if (not model_name in self.key_map):
            return original_key
        return self.key_map[model_name][original_key] if (original_key in self.key_map[model_name]) else original_key



class SingleModelMixin():
    # field_name->custom key
    key_map = {}
    model_class = None

    def _verify_keymap(self):
        fieldnames = self.field_names()
        for k in self.key_map.keys():
            if k not in fieldnames:
                raise ImproperlyConfigured('{} key_map attribute states key not declared as model field name. key:"{}", model:{}'.format(
                    self.__class__.__name__,
                    k,
                    self.model_class._meta.object_name
                    ))

    def _verify_model_exists(self):
        if (not self.model_class):
            raise ImproperlyConfigured('{} must have a model attribute.'.format(
                self.__class__.__name__
                ))

    def model_name(self):
        return str(self.model_class._meta)
                         
    def local_field_names(self):
        concrete_model = self.model_class._meta.concrete_model
        return [field.name for field in concrete_model._meta.local_fields]
                    
    def field_names(self):
        return [field.name for field in self.model_class._meta.fields]

    def map_key(self, original_key):
        '''
        Map original field key to custom key.
        @return new key. If fails, original key.
        '''
        return self.key_map[original_key] if (original_key in self.key_map) else original_key


class BaseMixin():
    pop_false = True
    
    def pop_false(self, object_dict):
        return {k : v for k, v in object_dict.items() if (not(v is None))}
    
    
    
class KeyMapSerializer(MultiModelMixin, BaseMixin, base.Serializer):
    def serialize(self, queryset, *args, key_map=None, pop_false=True, **options):
        #print(str(self.__class__.__mro__))
        if (key_map):
            self.key_map = key_map
        if (pop_false):
            self.pop_false = pop_false
        #print(str(super(base.Serializer, self).__class__))
        #return super(base.Serializer, self).serialize(queryset, *args, **options)
        return super().serialize(queryset, **options)



class KeyMapDeserializer(MultiModelMixin, BaseMixin, base.Deserializer):
    #ignore_unknown_fields = False
    #pop_false
    
    def __init__(self, stream_or_string, key_map=None, pop_false=True, **options):
        if (key_map):
            self.key_map = key_map
        if (pop_false):
            self.pop_false = pop_false
        super().__init__(stream_or_string,  **options)


class SingleModelKeyMapSerializer(SingleModelMixin, KeyMapSerializer):
    def serialize(self, queryset, model_class, *args, key_map=None, pop_false=True, **options):
        if (model_class):
            self.model_class = model_class
        self._verify_model_exists()
        self._verify_keymap()
        return super().serialize(queryset, *args, key_map=key_map, pop_false=pop_false, **options)
   
   
class SingleModelKeyMapDeserializer(SingleModelMixin, KeyMapDeserializer):
    def __init__(self, stream_or_string, model_class, key_map=None, pop_false=True, **options):
        super().__init__(stream_or_string, key_map=key_map, pop_false=pop_false, **options)
        if (model_class):
            self.model_class = model_class
        self._verify_model_exists()
        self._verify_keymap()

