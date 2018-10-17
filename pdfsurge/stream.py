# -*- coding: utf-8 -*-

__author__ = "Cyril Nicodeme"
__author_email__ = "cyril@pdfshift.io"

from pdfsurge.exceptions import PDFSurgeStreamError
import io


class StreamReader:
    def __init__(self, stream):
        if not isinstance(stream, io.BytesIO) and 'b' not in stream.mode:
            raise PDFSurgeStreamError('Stream object must be opened in binary mode.')

        self.stream = stream
    
    def read(self, length=1):
        tok = self.stream.read(length)
        if not tok:
            raise PDFSurgeStreamError('Unexpected end of stream')

        return tok
    
    def seek(self, pos, cur=None):
        if cur is None:
            cur = io.SEEK_SET

        return self.stream.seek(pos, cur)

    def readline(self, maxlength=1024):
        return self.stream.readline(maxlength)
    
    def tell(self):
        return self.stream.tell()
    
    def peek(self, length=1):
        pos = self.stream.tell()
        tok = self.read(length)
        self.seek(pos, io.SEEK_SET)

        return tok
    
    def around(self, length):
        pos = self.stream.tell()
        self.seek(length * -1, io.SEEK_CUR)
        c = self.read(length * 2)
        self.seek(pos, io.SEEK_SET)
        return c

    def read_until_space(self, blocking=False):
        chars = b''
        while True:
            x = self.read(1)
            if not x: # EOF
                break
            if x.isspace():
                if len(chars) > 0 or blocking:
                    break
                continue
            chars += x

        return chars

    def read_until(self, value, reverse=False, ignore_eof=True):
        length = 0
        is_list = False

        if isinstance(value, (tuple, list)) and len(value) > 0:
            is_list = True
            length = len(value[0])
            if not all(length == len(rest) for rest in value):
                raise AttributeError('Each items of the list for the parameter values on "read_until" must have the same char length.')
        else:
            length = len(value)

        if length == 0:
            return 0

        if reverse:
            self.seek(length * -1, io.SEEK_CUR)
            position = (length * -1)  -1
        else:
            position = ((length + 1) * -1) + 1

        initial = self.tell()

        while True:
            v = self.read(length)
            if v == b'\r':
                if self.read(1) == b'\n' and ignore_eof:
                    v = b' '
                else:
                    self.seek(-1, io.SEEK_CUR)
            if ignore_eof and v == b'\n':
                v = b' '

            if is_list:
                if v in value:
                    break
            elif v == value:
                break

            if not reverse:
                if not self.read(1):
                    # EOF
                    return 0
            try:
                self.seek(position, io.SEEK_CUR)
            except IOError:
                return 0

        self.seek(length * -1, io.SEEK_CUR)
        final = self.tell()

        if initial == final:
            content = None
        else:
            self.seek(min(initial, final))
            content = self.read(max(initial, final) - min(initial, final))

        self.seek(final)  # Because in reverse, final is before!
        return content
    
    def read_until_char(self):
        while self.read(1).isspace():
            continue

        self.seek(-1, io.SEEK_CUR)
