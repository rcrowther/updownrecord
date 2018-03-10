from ..freecfg import Writer, DictReader
from .nonrelational_python import NonrelationalSerializer, NonrelationalDeserializer



class Serializer(NonrelationalSerializer):
    """Convert a queryset to JSON."""
    internal_use_only = False

    def start_serialization(self):
        self.writer = Writer(self.stream)

    def end_object(self, obj):
        # self._current has the field data
        # needs to be broken up for freeconfig
        do = self.get_dump_object(obj)
        self.writer.mksection(do['model'])
        self.writer.mkentry('pk', do['pk'])
        for fname, fval in do['fields'].items():
            self.writer.mkentry(fname, fval)
        self._current = None

    def getvalue(self):
        # Grandparent super
        return super(NonrelationalSerializer, self).getvalue()



class Deserializer(NonrelationalDeserializer):
    def get_object_list(self, stream):
        return DictReader(stream)

    def model_path_from_data(self, d):
        return d.title

    def get_pk_from_data(self, d):
        return d.entries.get('pk')

    def fields_from_data(self, d):
        entries = d.entries
        entries.pop('pk')
        return entries
