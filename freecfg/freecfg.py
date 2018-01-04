import re


class Builder():
    '''
    Builder for freecfg data.
    '''
    b = []
    
    def mkentries(self, data_dict):
        for k, v in data_dict.items():
            self.b.append('{0} = {1}\n'.format(k, v))

    def mksection(self, section_title):
        self.b.append('[{0}]\n'.format(section_title))
            
    def __iter__(self):
        return self.b
        
    def result(self):
        return ''.join(self.b)
        
    def __repr__(self):
        return ''.join(self.b)
        
        
class ParsingError(Exception):
    pass

ignoreRE = re.compile('^\s*(?:#.*)?$') 
sectionRE = re.compile('^\s*\[([^\[]+)\].*$')
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
        self.it = None #self.binaryToUTF8Iter(stream)
        self.linecount = 0
        self.seq_b = {} if (seq_is_dict) else []
        self.dict_b = {}
        self.current_section = ''
        self.current_key = ''
        self.current_value = []
            
    def binaryToUTF8Iter(self, stream):
        for line in stream:
            yield line.decode('utf-8')

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
                    raise ParsingError('line:{} first significant line is key mark, but seq_is_dict=True.'.format(
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
