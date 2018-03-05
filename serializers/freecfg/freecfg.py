import re
import io
import collections

from django.conf import settings



class Builder():
    '''
    Builder for freecfg data.
    '''
    def __init__(self):
        self.b = []
            
    def mkentries(self, data_dict):
        for k, v in data_dict.items():
            self.b.append('{0} = {1}\n'.format(k, v))

    def mksection(self, section_title):
        self.b.append('[{0}]\n'.format(section_title))
            
    def __iter__(self):
        return self.b
        
    def __str__(self):
        return ''.join(self.b)
        
        
        
class Writer():
    '''
    Builder for freecfg data.
    '''
    stream_class = io.StringIO

    def __init__(self, stream=None):
        self.stream = stream if stream is not None else self.stream_class()

    def mkentries(self, data_dict):
        for k, v in data_dict.items():
            self.stream.write('{0} = {1}\n'.format(k, v))

    def mkentry(self, key, value):
        self.stream.write('{0} = {1}\n'.format(key, value))
            
    def mksection(self, section_text):
        self.stream.write('[{0}]\n'.format(section_text))

    def getvalue(self):
        """
        Return the build (or None if the output stream is
        not seekable).
        """
        if callable(getattr(self.stream, 'getvalue', None)):
            return self.stream.getvalue()
            
    def __str__(self):
        return self.getvalue()
        
        
        
class ParsingError(Exception):
    pass

ignoreRE = re.compile('^\s*(?:#.*)?$') 
sectionRE = re.compile('^\s*\[([^\]]+)\].*$')
keyRE = re.compile('^\s*(\w+)\s?=\s*(.*)$')



class Parser():
    '''
    Parse input as 'freecfg'
    Freecfg is like the cfg/ini format. But the parser is unusual. It 
    can not handle escapes, and whitespace-strips all key/value
    entries and section marks.
    
    Section headers can be anything within square brackets, including 
    multiple words. The parser will work with input with no section 
    headers.
    
    Comments are inital hash/pound, and valid anywhere.
    
    Keys must adhere to regex '\w+' i.e '[^a-zA-Z0-9\_]'. Values can be
    any length, including paragraphs.
    
    @param seq_is_dict If True, returns a dict of dicts with section 
    header text as keys. If False, the return is a list of dicts.
    @return A list or dict of dicts
    '''
    def __init__(self, seq_is_dict=True):
        self.seq_is_dict = seq_is_dict
        self.it = None
        self.linecount = 0
        self.seq_b = {} if (seq_is_dict) else []
        self.dict_b = {}
        self.current_section = ''
        self.current_key = ''
        self.current_value = []
            
    def binaryToUTF8Iter(self, stream):
        for line in stream:
            yield line.decode(settings.DEFAULT_CHARSET)

    def get_line(self):
        self.linecount += 1
        #print(str(self.linecount))
        return next(self.it)

    def kv_not_empty(self):
        return bool(self.current_key)
        
    def kv_open(self, new_key_name, partial_new_value):
        self.current_key = new_key_name
        self.current_value = [partial_new_value]

    def kv_close(self):
        # only if exists
        if (self.kv_not_empty()):
            value = ''.join(self.current_value)
            self.dict_b[self.current_key] = value.strip()

    def section_close(self):
        self.kv_close()
        if (self.seq_is_dict):
            #! check key not exists
            section_key = self.current_section.strip()
            if (section_key in self.seq_b):
                raise ParsingError('line:{} Section header is repeated (and parser is set to seq_is_dict=True). Header text:"{}"'.format(
                    self.linecount,
                    section_key
                ))              
            self.seq_b[section_key] = self.dict_b
        else:
            #print('append seq_b')
            self.seq_b.append(self.dict_b)
                    
    def section_open(self, new_section_name):
        self.current_section = new_section_name
        self.dict_b = {}
        # When a section is opened,
        # we need to empty lingering kvs
        self.current_key = ''
        
    def _parse(self): 
        line = ''   
        # skip whitespace and comments
        while(True):
            line = self.get_line()
            mo = ignoreRE.match(line)
            if (not mo):
                break
        
        # now on significant line
        # initialize
        mo = sectionRE.match(line)
        if (mo):
            self.section_open(mo.group(1))
        else:
            mo = keyRE.match(line)
            if (mo):   
                if (self.seq_is_dict):         
                    raise ParsingError('line:{} first significant line is key/value mark, but seq_is_dict=True.'.format(
                        self.linecount
                    ))
                self.kv_open(mo.group(1), mo.group(2))         
            else:
                raise ParsingError('line:{} First significant line is not a section or key mark.'.format(
                    self.linecount
                ))
                
        # process body repetitively                       
        for line in self.it:      
            mo = keyRE.match(line)
            if (mo):
                self.kv_close()
                self.kv_open(mo.group(1), mo.group(2))
                continue
            mo = sectionRE.match(line)
            if (mo):
                self.section_close()
                self.section_open(mo.group(1))
                continue  
            mo = ignoreRE.match(line)
            if (mo):
                continue 
            else:
                self.current_value.append(line)
                
        # finish open data
        self.section_close()
        return self.seq_b

    def parse_binary_iter(self, stream):
        self.it = self.binaryToUTF8Iter(stream)
        return self._parse()

    def parse_text_iter(self, it):
        self.it = it
        return self._parse()
        
    def parse_text(self, txt):
        self.it = iter(txt.splitlines())
        return self._parse()


SECTION = 1
ENTRY = 0
Entry = collections.namedtuple('Entry', 'key value')
Section = collections.namedtuple('Section', 'data')
class Reader():
    '''
    Parse input as 'freecfg'
    Freecfg is like the cfg/ini format. But the parser is unusual. It 
    can not handle escapes, and whitespace-strips all key/value
    entries and section marks.
    
    Section headers can be anything within square brackets, including 
    multiple words. The parser will work with input with no section 
    headers.
    
    Comments are inital hash/pound, and valid anywhere.
    
    Keys must adhere to regex '\w+' i.e '[^a-zA-Z0-9\_]'. Values can be
    any length, including paragraphs.
    
    @param seq_is_dict If True, returns a dict of dicts with section 
    header text as keys. If False, the return is a list of dicts.
    @return A list or dict of dicts
    '''
    def __init__(self, stream_or_string, encoding=settings.DEFAULT_CHARSET):
        if isinstance(stream_or_string, bytes):
            stream_or_string = stream_or_string.decode(encoding)
        if isinstance(stream_or_string, str):
            stream = io.StringIO(stream_or_string)
        else:
            stream = stream_or_string
        self.it = self.streamToIter(stream)
        self.linecount = 0
        self.line = None
        self.mo = None    
        #prime
        self.get_line()        

    def streamToIter(self, stream):
        for line in stream:
            yield line
            
    def __iter__(self):
        return self
        
    def get_line(self):
        while (True):
            self.linecount += 1
            #print(str(self.linecount))
            self.line = next(self.it)
            mo = ignoreRE.match(self.line)
            if (not mo):
                break

    def section(self):
        self.mo = sectionRE.match(self.line)
        return bool(self.mo)

    def keyline(self):
        self.mo = keyRE.match(self.line)
        return bool(self.mo)        
        
    def get_value(self, builder):
        #print('get value:' + str(builder))
        while(True):
            self.get_line()
            #print('get line:' + self.line)
            if (self.section() or self.keyline()):
                break
            builder.append(self.line)
        return ''.join(builder)
      
    def __next__(self):
        if (self.section()):
            title = self.mo.group(1)
            self.get_line()            
            return Section(title)
        elif (self.keyline()):
            key = self.mo.group(1)
            value = self.get_value([self.mo.group(2)])
            return Entry(key, value)
        raise ParsingError('parsing error, unrecognised line:{}\n"{}"'.format(
            self.linecount,
            self.line
        ))


#? messy logic
#? not detecting initial kvs
SectionData = collections.namedtuple('SectionData', 'title data')
class DictReader():
  
    def __init__(self, stream_or_string, encoding=settings.DEFAULT_CHARSET):
        self.reader = Reader(stream_or_string, encoding)
        self.event = None
        self.kv_cache = {}
        self.last_section_returned = False
        #prime
        try:
            self.event = self.reader.__next__()
        except StopIteration:
            # Will set iterator to return instant exception on __next__()
            self.last_section_returned = True

    def __iter__(self):
        return self
        
    def readKeyValues(self):
        self.kv_cache = {}
        while(True):
            self.event = self.reader.__next__()
            if isinstance(self.event, Entry):
                #print(str())
                self.kv_cache[self.event.key] = self.event.value
                continue
           
    def __next__(self):
        if isinstance(self.event, Section):
            title = self.event.data
            try:
                self.readKeyValues()
            except StopIteration:
                if(not self.last_section_returned):
                    self.last_section_returned = True
                else:
                    raise StopIteration
            return SectionData(title=title, data=self.kv_cache)
        raise StopIteration

