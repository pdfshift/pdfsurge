# -*- coding: utf-8 -*-

__author__ = "Cyril Nicodeme"
__author_email__ = "cyril@pdfshift.io"

from .exceptions import PDFSurgeException
from .stream import StreamReader
from .objects import PDFObject, parse_stream
from .defines import layouts, pagemodes
from io import BytesIO
import io, zlib, struct


class PDFSurge:
    @classmethod
    def read_from_file(cls, path):
        return cls(open(path, 'rb'))

    def __init__(self, stream):
        self.reader = StreamReader(stream)

        self.metadata = None
        self.root = None
        self._pages = None
        self._cache = {}

        self.reader.seek(0)
        if self.reader.read(5) != b'%PDF-':
            raise PDFSurgeException('Invalid file given. PDF is not starting with "%PDF-".')

        self.version = float(self.reader.read_until_space())

        self.reader.seek(0, io.SEEK_END)
        if self.reader.read_until(b'%%EOF', reverse=True) == 0:
            raise PDFSurgeException('Invalid file given. EOF not found.')

        # Locating startxref
        self.reader.read_until(b'startxref', reverse=True)
        self.reader.seek(9, io.SEEK_CUR)
        startxref = int(self.reader.read_until_space().strip())

        self.xref = {}
        self._compressed_objs = {}
        self.trailer = {}
        # Reading the xref table
        while True: # Might have multiple xref tables
            self.reader.seek(startxref, 0)
            xref = self.reader.read_until_space()
            if xref[0:4] == b'xref':
                while True:
                    num = self.reader.read_until_space()
                    size = self.reader.read_until_space()
                    num, size = int(num), int(size)
                    for i in range(0, size):
                        self.reader.read_until_char()
                        offset = self.reader.read_until_space()
                        generation = self.reader.read_until_space()
                        self.reader.read_until_space() # Reference ; "f" or "n"

                        offset, generation = int(offset), int(generation)

                        if num not in self.xref:
                            self.xref[num] = {}

                        self.xref[num][generation] = offset
                        num = num + 1

                    pos = self.reader.tell()
                    if self.reader.read_until_space() == b'trailer':
                        break
                    else:
                        # The trailer is not finished, so we continue
                        # But first, we go back at the beginning of the line
                        self.reader.seek(pos, io.SEEK_SET)

                trailer = parse_stream(self.reader)
            elif xref.isdigit():
                self.reader.read_until_space() # cur_generation
                assert self.reader.read(3) == b'obj'

                obj = PDFObject.parse(self.reader)
                trailer = obj.properties
                if '/Type' not in trailer or trailer['/Type'] != '/XRef':
                    raise PDFSurgeException('Not a valid 1.5+ XRef table!')

                stream_data = BytesIO(obj.get_data())
                idrange = trailer.get('/Index', [0, trailer.get('/Size')])
                entry_sizes = trailer.get('/W')
                assert len(entry_sizes) == 3

                def _pairs(array):
                    i = 0
                    while True:
                        yield array[i], array[i + 1]
                        i += 2
                        if (i + 1) >= len(array):
                            break
                
                def _convertToInt(d, size):
                    if size > 8:
                        raise PDFSurgeException("Invalid size in _convertToInt")

                    assert isinstance(d, bytes)
                    d = b"\x00\x00\x00\x00\x00\x00\x00\x00" + d
                    d = d[-8:]
                    return struct.unpack(">q", d)[0]
                
                def _get_entry(i):
                    """
                    Reads the correct number of bytes for each entry. See the
                    discussion of the W parameter in PDF spec table 17.
                    """
                    if entry_sizes[i] > 0:
                        d = stream_data.read(entry_sizes[i])
                        return _convertToInt(d, entry_sizes[i])
                    
                    # PDF Spec Table 17: A value of zero for an element in the
                    # W array indicates...the default value shall be used

                    # First value defaults to 1
                    return 1 if i == 0 else 0

                def _used_before(num, generation):
                    # We move backwards through the xrefs, don't replace any.
                    return generation in self.xref.get(num, []) or num in self._compressed_objs

                last_end = 0
                for start, size in _pairs(idrange):
                    assert start >= last_end
                    last_end = start + size
                
                    for num in range(start, start + size):
                        xref_type = _get_entry(0)
                        if xref_type == 0:
                            # Linked list of free objects
                            obj_num = _get_entry(1)
                            generation = _get_entry(2)
                            self._compressed_objs[num] = (obj_num, generation, 0)

                        elif xref_type == 1:
                            offset = _get_entry(1)
                            generation = _get_entry(2)

                            if num not in self.xref:
                                self.xref[num] = {}
                            
                            if not _used_before(num, generation):
                                self.xref[num][generation] = offset
                        elif xref_type == 2:
                            # Compressed objects!
                            obj_num = _get_entry(1)
                            obj_idx = _get_entry(2)
                            generation = 0  # PDF spec table 18, generation is 0

                            if not _used_before(num, generation):
                                self._compressed_objs[num] = (obj_num, obj_idx, 2)
                        else:
                            raise PDFSurgeException('Unknow xref type {0}'.format(xref_type))
            else:
                raise PDFSurgeException('Invalid XRef table!')

            for k in trailer:
                if k not in self.trailer:
                    self.trailer[k] = trailer[k]

            if '/Prev' in trailer:
                startxref = int(trailer['/Prev'])
                continue

            break

    def get_version(self):
        return self.version
    
    def set_version(self, version):
        self.version = version
    
    def get_metadata(self):
        if not self.metadata:
            # Reading the INFO object
            if '/Info' in self.trailer:
                info = self.trailer['/Info']
                try:
                    self.metadata = self.get_object(info).properties
                except PDFSurgeException:
                    pass
        
        return self.metadata
    
    def add_metadata(self, key, value):
        pass

    def get_root(self):
        if self.root is None:
            self.root = self.get_object(self.trailer['/Root'])
            assert self.root.properties.get('/Type') == '/Catalog'
        
        return self.root
    
    def set_root_property(self, prop, value):
        self.get_root()
        self.root[prop] = value
    
    def get_pages(self):
        if not self._pages:
            self._pages = []
            assert '/Pages' in self.get_root().properties
            pages = self.get_object(self.get_root().properties['/Pages'])
            self._get_pages(pages)

        return len(self._pages)
    
    def _get_pages(self, obj):
        if obj.properties.get('/Type') == '/Pages':
            for page in obj.properties.get('/Kids'):
                p = self.get_object(page)
                self._get_pages(p)
        elif obj.properties.get('/Type') == '/Page':
            self._pages.append(obj)
        else:
            raise PDFSurgeException('Unexpected type {0} for pages'.format(obj.properties.get('/Type')))
    
    def get_object(self, path):
        idnum, generation = path[:2]

        if self._cache.get(idnum, {}).get(generation, None):
            return self._cache[idnum][generation]

        if idnum in self.xref and generation in self.xref[idnum]:
            index = self.xref[idnum][generation]
            self.reader.seek(index, io.SEEK_SET)

            cur_num = self.reader.read_until_space()
            cur_generation = self.reader.read_until_space()

            assert int(cur_num) == idnum
            assert int(cur_generation) == generation
            assert self.reader.read(3) == b'obj'

            obj = PDFObject.parse(self.reader)
            if idnum not in self._cache:
                self._cache[idnum] = {}
            
            self._cache[idnum][generation] = obj
            return obj
        elif idnum in self._compressed_objs:
            indirect = self._compressed_objs[idnum]
            obj = self.get_object((indirect[0], 0))  # "generation" is always 0
            assert obj.properties.get('/Type') == '/ObjStm'
            assert indirect[1] < obj.properties.get('/N')
            data = StreamReader(BytesIO(obj.get_data()))
            for i in range(obj.properties.get('/N')):
                obj_num = data.read_until_space()
                obj_offset = data.read_until_space()

                if int(obj_num) != idnum:
                    continue
                assert i == indirect[1]  # object index

                data.seek(obj.properties.get('/First') + int(obj_offset), io.SEEK_SET)

                obj = PDFObject.parse(data, endobj=False)
                if idnum not in self._cache:
                    self._cache[idnum] = {}
                
                self._cache[idnum][0] = obj
                return obj

        raise PDFSurgeException('Object {0} with generation {1} was not found'.format(idnum, generation))
    
    def is_encrypted(self):
        return '/Encrypt' in self.trailer
    
    def get_page_mode(self):
        if '/PageMode' in self.get_root():
            return self.get_root()['/PageMode']
        
        return None
    
    def set_page_mode(self, mode):
        """
        Accepted PageMode are
            /UseNone         Do not show outlines or thumbnails panels
            /UseOutlines     Show outlines (aka bookmarks) panel
            /UseThumbs       Show page thumbnails panel
            /FullScreen      Fullscreen view
            /UseOC           Show Optional Content Group (OCG) panel
            /UseAttachments  Show attachments panel
        """
        if mode in pagemodes:
            raise PDFSurgeException('Invalid PageMode. Must be one of {0}'.format(', '.join(pagemodes)))

        self.set_root_property('/PageMode', mode)
    
    def get_page_layout(self):
        if '/PageLayout' in self.get_root():
            return self.get_root()['/PageLayout']
        
        return None
    
    def set_page_layout(self, layout):
        """
        Accepted layouts are:
             /NoLayout        Layout explicitly not specified
             /SinglePage      Show one page at a time
             /OneColumn       Show one column at a time
             /TwoColumnLeft   Show pages in two columns, odd-numbered pages on the left
             /TwoColumnRight  Show pages in two columns, odd-numbered pages on the right
             /TwoPageLeft     Show two pages at a time, odd-numbered pages on the left
             /TwoPageRight    Show two pages at a time, odd-numbered pages on the right
        """
        if layout in layouts:
            raise PDFSurgeException('Invalid PageLayout. Must be one of {0}'.format(', '.join(layouts)))

        self.set_root_property('/PageLayout', layout)
    
    def get_links(self, callback):
        pass

    def remove_links(self):
        pass

    def get_images(self, callback):
        pass

    def remove_images(self):
        pass
    
    def get_texts(self, lbd):
        pass

    def remove_text(self):
        pass
    
    def grayscale(self):
        pass
    
    def encrypt(self):
        pass

    def set_watermark(self):
        pass

    def write(self, stream):
        if 'b' not in stream.mode:
            raise PDFSurgeException('Stream must be in binary mode.')

    
    # @see https://stackoverflow.com/a/25835284/330867 for grayscale
