
#from .freeconfig import Serializer, Deserializer
#from .csv import Serializer, Deserializer

"""
To add the serialisers for general use, add this to the settings file::

    SERIALIZATION_MODULES = {
        "nonrel_csv": "updownrecord.serializers.csv",
        "nonrel_freecfg": "updownrecord.serializers.freecfg",
        "nonrel_json": "updownrecord.serializers.json",
        "nonrel_xml": "updownrecord.serializers.xml",
    }

Now you can use code like,

from django.core import serializers
data = serializers.serialize('nonrel_freecfg', SomeModel.objects.all())

for o in serializers.deserialize("nonrel_freecfg", data):
    print(str(o.object))
"""
