# -*- coding: utf-8 -*-

__author__ = "Cyril Nicodeme"
__author_email__ = "cyril@pdfshift.io"

from .exceptions import PDFSurgeException
from .reader import StreamReader
from .parsers import parse_stream
import io, zlib


class PDFSurge:
    @classmethod
    def read_from_file(cls, path):
        return cls(open(path, 'rb'))

    def __init__(self, stream):
        self.reader = StreamReader(stream)

        self.metadata = None
        self.root = None

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
                # xref == cur_num
                self.reader.read_until_space() # cur_generation
                assert self.reader.read(3) == b'obj'

                obj = PDFObject.read(self.reader)
                trailer = obj.properties
                assert trailer['/type'] == '/XRef'
                if '/Type' not in trailer or trailer['/Type'] != '/XRef':
                    raise PDFSurgeException('Not a valid 1.5+ XRef table!')
                
                # Process the table!
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
    
    def get_root(self):
        if self.root is None:
            self.root = self.get_object(self.trailer['/Root'])
        
        return self.root
    
    def get_pages(self):
        assert '/Pages' in self.get_root().properties
        pages = self.get_object(self.get_root().properties['/Pages'])
        assert '/Count' in pages.properties
        return pages.properties['/Count']
    
    def get_object(self, path):
        idnum, generation = path
        if idnum not in self.xref or generation not in self.xref[idnum]:
            raise PDFSurgeException('Object {0} with generation {1} was not found'.format(idnum, generation))

        index = self.xref[idnum][generation]
        self.reader.seek(index, io.SEEK_SET)

        cur_num = self.reader.read_until_space()
        cur_generation = self.reader.read_until_space()

        assert int(cur_num) == idnum
        assert int(cur_generation) == generation
        assert self.reader.read(3) == b'obj'

        return PDFObject.read(self.reader)
    
    # @see https://stackoverflow.com/a/25835284/330867 for grayscale


class PDFObject:
    def __init__(self):
        self.properties = {}
        self.stream = None

    @classmethod
    def read(cls, reader):
        reader.read_until_char()
        assert reader.peek(2) == b'<<'

        obj = cls()
        obj.properties = parse_stream(reader)

        reader.read_until_char()
        peek = reader.peek(6)
        if peek == b'stream':
            # Stream
            reader.read(6)
            obj.stream = reader.read_until(b'endstream').strip()
            reader.read(9)
            reader.read_until_char()

        assert reader.peek(6) == b'endobj'
        return obj


"""
TODO :
    Document 2.pdf
    /Type/Encoding/Differences
        => Essayer de grouper toutes les "/Type/Encoding/Differences" ensembles ?

For the second line:
% 0xE2E3CFD3
"""