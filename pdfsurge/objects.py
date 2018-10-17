# -*- coding: utf-8 -*-
from .exceptions import PDFParserException, PDFSurgeStreamError
from .defines import escaped_dict
from .decoders import Filters
from datetime import datetime
import io, re, codecs

__author__ = "Cyril Nicodeme"
__author_email__ = "cyril@pdfshift.io"



def parse_stream(reader, jump=False):
    if not jump:
        reader.read_until_char()

    tok = reader.peek(1).lower()
    if tok in parsers_objects:
        return parsers_objects[tok].parse(reader)
    elif tok == b'>':
        assert reader.read(2) == b'>>'
        raise PDFParserException('Unexpected end of object.')
    elif tok == b'%':
        # Comment
        reader.readline()
    elif tok == b'<':
        if reader.peek(2) == b'<<':
            return DictionaryObject.parse(reader)
        else:
            return StringObject.parse_hex(reader)
    else:
        indirect = IndirectObject.parse(reader)
        if indirect:
            return indirect

        return NumericObject.parse(reader)
    
    raise PDFParserException('Unable to parse the given value.')


class Parser:
    """ Root class for the various PDF Objects """
    @classmethod
    def parse(cls, reader):
        raise NotImplementedError()


class PDFObject(Parser):
    def __init__(self):
        self.properties = {}
        self.stream = None
        self.data = None

    def get_data(self):
        if not self.data:
            filters = self.properties.get('/Filter', None)
            if filters:
                if isinstance(filters, str):
                    filters = (filters, )

                self.data = self.stream
                for filter in filters:
                    self.data = Filters.decode(self.data, filter, self.properties.get('/DecodeParms', {}))
                
        return self.data

    @classmethod
    def parse(cls, reader, endobj=True):
        reader.read_until_char()
        assert reader.peek(2) == b'<<'

        obj = cls()
        obj.properties = parse_stream(reader)
        
        try:
            reader.read_until_char()
            peek = reader.peek(6)
            if peek == b'stream':
                # Stream
                reader.read(6)
                obj.stream = reader.read_until(b'endstream').strip()
                reader.read(9)
                reader.read_until_char()

            if endobj:
                assert reader.read(6) == b'endobj'
        except PDFSurgeStreamError:
            pass

        return obj


class ArrayObject(Parser):
    @classmethod
    def parse(cls, reader):
        """ Returns a list """
        result = []
    
        assert reader.read(1) == b'['
        while True:
            if reader.peek(1) == b']':
                reader.seek(1, io.SEEK_CUR) # We pass the "]" char
                break

            result.append(parse_stream(reader))

        return result


class BooleanObject(Parser):
    @classmethod
    def parse(cls, reader):
        """ Returns a bool """
        value = reader.read(4).lower()
        if value == b'true':
            return True
        elif value == b'fals':
            reader.seek(1, io.SEEK_CUR) # We pass the "e" char from falsE
            return False
        
        raise PDFParserException('Unexpected value. Expected Boolean Object.')

class DictionaryObject(Parser):
    @classmethod
    def parse(cls, reader):
        assert reader.read(2) == b'<<'

        result = {}
        while True:
            reader.read_until_char()
            if reader.peek(2) == b'>>':
                reader.read(2)
                break

            key = parse_stream(reader, jump=True)
            value = parse_stream(reader)
            result[key] = value

        return result


class IndirectObject(Parser):
    @classmethod
    def parse(cls, reader):
        """ Returns a tuple of two values: (idnum, generation) """
        position = reader.tell()
        idnum = reader.read_until_space()
        generation = reader.read_until_space()
        r = reader.read(1)

        try:
            assert r == b'R'
            return (int(idnum), int(generation))
        except (AssertionError, ValueError):
            reader.seek(position, io.SEEK_SET)
            return None


class NameObject(Parser):
    @classmethod
    def parse(cls, reader):
        """ Returns a string starting with "/" """
        assert reader.read(1) == b'/'
        value = reader.read_until((b' ', b'[', b'(', b'<', b'{', b'%', b'>', b'/', b']', b')', b'}'), ignore_eof=True)
        return '/{0}'.format(value.decode('utf-8'))


class NullObject(Parser):
    @classmethod
    def parse(cls, reader):
        """ Returns none """
        value = reader.read(4)
        if value.lower() != b'null':
            raise PDFParserException('Unexpected value. Expected Null Object.')
        
        return None


class NumericObject(Parser):
    """ Returns either an int or a float """
    signs = {b'+': 1, b'-': -1}

    @classmethod
    def parse(cls, reader):
        value = b''
        while True:
            tok = reader.read(1)
            if tok in b'+-.0123456789':
                value += tok
            else:
                reader.seek(-1, io.SEEK_CUR)
                break

        multiplier = 1
        if value[0:1] in (b'+', b'-'):
            multiplier = cls.signs[value[0:1]]
            value = value[1:]

        if value.find(b'.') > -1:
            return float(value) * multiplier
        else:
            return int(value) * multiplier


# @see https://github.com/feliam/miniPDF/blob/4d7b34c74b34838f43f61f64afe76f91899dba27/minipdf/minipdf.py
class PDFString(bytes):
    def __init__(self, value, hexadecimal=False, utf16=False):
        self.is_hexadecimal = hexadecimal
        self.is_utf16 = utf16
        super().__init__(self, value)
    
    def set_hexadecimal(self, value):
        self.is_hexadecimal = value
    
    def get_hexadecimal(self):
        return self.is_hexadecimal
    
    def set_utf16(self, value):
        self.is_utf16 = value

    def get_utf16(self):
        return self.is_utf16


class StringObject(Parser):
    @classmethod
    def parse_hex(cls, reader):
        """ Returns a str """
        assert reader.read(1) == b'<'

        value = reader.read_until(b'>') # Set hexadecimal !
        if len(value) == 1:
            value += '0'
        if len(value) % 2 != 0:
            raise PDFParserException('Invalid Hexadecimal value given.')

        reader.read(1)

        chunks = [value[i:i+2] for i in range(0, len(value), 2)]
        value = ''.join([chr(int(c, base=16)) for c in chunks]).encode('utf-8')

        if value != b'':
            value = re.sub(b'\\\\[0-9]{1,3}', cls.decode_8bit, value)
        
        return value
    
    @classmethod
    def parse(cls, reader):
        """ Returns a str """
        assert reader.read(1) == b'('
        level = 1  # 1 because we already are inside the first "("
        value = b''

        while True:
            tok = reader.read(1)
            if tok == b'(':
                level += 1
            elif tok == b')':
                level -= 1
                if level == 0:
                    break
            elif tok == b'\\':
                tok = reader.read(1)
                if tok in escaped_dict:
                    tok = escaped_dict[tok]
                elif tok.isdigit():
                    # "The number ddd may consist of one, two, or three
                    # octal digits; high-order overflow shall be ignored.
                    # Three octal digits shall be used, with leading zeros
                    # as needed, if the next character of the string is also
                    # a digit." (PDF reference 7.3.4.2, p 16)
                    for i in range(2):
                        subtok = reader.read(1)
                        if not subtok.isdigit():
                            break
                        tok += subtok
                    
                    tok = bytes(int(tok, base=8))
                    # TODO: value.set_utf16(True)
                elif tok in b'\n\r':
                    # When the string is written on multiline.
                    if reader.read(1) not in b'\n\r':
                        reader.seek(-1, io.SEEK_CUR)
                    
                    # We don't add a breakline since it's not escaped
                    continue

            value += tok

        if value:
            if value[0:2] == b'D:':
                value = value[2:].replace(b"'", b'')
                value = value.replace(b'Z', b'')
                if len(value) == 14:
                    value += b'+0000'
                return datetime.strptime(value.decode('utf-8'), "%Y%m%d%H%M%S%z")

        return value

    @classmethod
    def decode_8bit(cls, match):
        value = match.group().replace(b'\\', b'')
        if value == b'000':
            return b''
        return bytes(int(value, base=8))


parsers_objects = {
    b'/': NameObject,
    b'[': ArrayObject,
    b't': BooleanObject,
    b'f': BooleanObject,
    b'(': StringObject,
    b'n': NullObject
}
