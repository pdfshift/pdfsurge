# -*- coding: utf-8 -*-

from .exceptions import PDFSurgeDecoderException
from .utils import lzw
from io import BytesIO
import zlib, struct, math

__author__ = "Cyril Nicodeme"
__author_email__ = "cyril@pdfshift.io"


class Filters(object):
    @staticmethod
    def decode(data, filter, parameters=None):
        """
        Decode the given data based on the provided filter,
        sing parameters when provided.
        """

        if not data:
            # There is no need to process an empty set of data
            return data

        if filter == '/ASCII85Decode' or filter == '/A85':
            return ASCII85Decoder.decode(data)
        elif filter == '/ASCIIHexDecode' or filter == '/AHx':
            return ASCIIHexDecoder.decode(data)
        elif filter == '/CCITTFaxDecode' or filter == '/CCF':
            return CCITTFaxDecoder.decode(data, parameters)
        elif filter == '/DCTDecode' or filter == '/DCT':
            return DCTDecoder.decode(data, parameters)
        elif filter == '/FlateDecode' or filter == '/Fl':
            return FlateDecoder.decode(data, parameters)
        elif filter == '/LZWDecode' or filter == '/LZW':
            return LZWDecoder.decode(data, parameters)
        elif filter == '/RunLengthDecode' or filter == '/RL':
            return RunLengthDecode.decode(data)
        elif filter == '/Crypt':
            return Crypt.decode(data, parameters)
        elif filter == '/JBIG2Decode':
            return JBIG2Decode.decode(data, parameters)
        elif filter == '/JPXDecode':
            return JPXDecoder.decode(data)
        else:
            raise NotImplementedError('Filter {0} not supported. Please open a ticket or a Pull Request.'.format(filter))
    
    @staticmethod
    def encode(data, filter, parameters=None):
        """
        Encode the data using the given filter. 
        """

        # For simplification, we only allow the long for of the filter, not the short.
        if filter == '/ASCII85Decode':
            return ASCII85Decoder.encode(data)
        elif filter == '/ASCIIHexDecode':
            return ASCIIHexDecoder.encode(data)
        elif filter == '/CCITTFaxDecode':
            return CCITTFaxDecoder.encode(data, parameters)
        elif filter == '/Crypt':
            return Crypt.encode(data, parameters)
        elif filter == '/DCTDecode':
            return DCTDecoder.encode(data, parameters)
        elif filter == '/FlateDecode':
            return FlateDecoder.encode(data, parameters)
        elif filter == '/JBIG2Decode':
            return JBIG2Decode.encode(data, parameters)
        elif filter == '/JPXDecode':
            return JPXDecoder.encode(data)
        elif filter == '/LZWDecode':
            return LZWDecoder.encode(data, parameters)
        elif filter == '/RunLengthDecode':
            return RunLengthDecode.encode(data)
        else:
            raise NotImplementedError('Filter {0} not implemented.'.format(filter))


class DCTDecoder(object):
    @classmethod
    def decode(cls, data, parameters):
        """ Nothing to do here """
        return data
    
    @classmethod
    def encode(cls, data, parameters):
        pass


class JPXDecoder(object):
    @classmethod
    def decode(cls, data):
        """ Nothing to do here """
        return data
    
    @classmethod
    def encode(cls, data):
        pass


class JBIG2Decode(object):
    @classmethod
    def decode(cls, data, parameters):
        raise NotImplementedError('Decoding {0} is not implemented.'.format(cls.__name__))
    
    @classmethod
    def encode(cls, data, parameters):
        raise NotImplementedError('Encoding {0} is not implemented.'.format(cls.__name__))


class Crypt(object):
    @classmethod
    def decode(cls, data, parameters):
        raise NotImplementedError('Decoding {0} is not implemented.'.format(cls.__name__))
    
    @classmethod
    def encode(cls, data, parameters):
        raise NotImplementedError('Encoding {0} is not implemented.'.format(cls.__name__))


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
# The following code has been taken from PDFMiner
# http://pypi.python.org/pypi/pdfminer/
#
# Copyright (c) 2004-2010 Yusuke Shinyama <yusuke at cs dot nyu dot edu>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
# KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


_ascii85decoder_b85chars = [chr(x) for x in range(0,0xff)]
_ascii85decoder_b85chars2 = [(a + b) for a in _ascii85decoder_b85chars for b in _ascii85decoder_b85chars]


class ASCII85Decoder(object):
    """
    In ASCII85 encoding, every four bytes are encoded with five ASCII
    letters, using 85 different types of characters (as 256**4 < 85**5).
    When the length of the original bytes is not a multiple of 4, a special
    rule is used for round up.
    
    The Adobe's ASCII85 implementation is slightly different from
    its original in handling the last characters.

    7.4.3     ASCII85Decode Filter
    The ASCII85Decode filter decodes data that has been encoded in ASCII base-85 
    encoding and produces binary data. The following paragraphs describe the process 
    for encoding binary data in ASCII base-85; the ASCII85Decode filter reverses this 
    process. The ASCII base-85 encoding shall use the ASCII characters ! through u and
    the character z, with the 2-character sequence ~> as its EOD marker. The ASCII85Decode
    filter shall ignore all white-space characters. Any other characters, and any character
    sequences that represent impossible combinations in the ASCII base-85 encoding shall 
    cause an error.
    """

    @classmethod
    def decode(cls, data):
        '''
        Method to decode datas using ASCII85

        @param data: A PDF data
        @return: A tuple (status,statusContent), where statusContent is the decoded PDF data in case status = 0 or an error in case status = -1
        '''
        n = b = 0
        out = b''
        try:
            for c in data:
                if b'!' <= c and c <= b'u':
                    n += 1
                    b = b*85+(ord(c)-33)
                    if n == 5:
                        out += struct.pack('>L', b)
                        n = b = 0
                elif c == b'z':
                    assert n == 0
                    out += b'\0\0\0\0'
                elif c == b'~':
                    if n:
                        for _ in range(5-n):
                            b = b*85+84
                        out += struct.pack('>L', b)[:n-1]
                    break
        except:
            raise PDFSurgeDecoderException('Unspecified error in ASCII85Decoder while decoding.')

        return out

    @classmethod
    def encode(cls, data):
        """ Encode data in base85 format """
        l = len(data)
        r = l % 4
        if r:
            data += '\0' * (4 - r)
        longs = len(data) >> 2
        words = struct.unpack('>%dL' % (longs), data)

        out = ''.join(_ascii85decoder_b85chars[(word // 52200625) % 85] +
                      _ascii85decoder_b85chars2[(word // 7225) % 7225] +
                      _ascii85decoder_b85chars2[word % 7225]
                      for word in words)

        # Trim padding
        olen = l % 4
        if olen:
            olen += 1
        olen += l // 4 * 5
        return out[:olen]


class RunLengthDecode(object):
    @classmethod
    def decode(cls, data):
        """
        RunLength decoder (Adobe version) implementation based on PDF Reference
        version 1.4 section 3.3.4:
            The RunLengthDecode filter decodes data that has been encoded in a
            simple byte-oriented format based on run length. The encoded data
            is a sequence of runs, where each run consists of a length byte
            followed by 1 to 128 bytes of data. If the length byte is in the
            range 0 to 127, the following length + 1 (1 to 128) bytes are
            copied literally during decompression. If length is in the range
            129 to 255, the following single byte is to be copied 257 - length
            (2 to 128) times during decompression. A length value of 128
            denotes EOD.
        """
        decoded = []
        i = 0
        while i < len(data):
            length = ord(data[i])
            if length == 128:
                break
            if length >= 0 and length < 128:
                run = data[i+1:(i+1)+(length+1)]
                decoded.append(run)
                i = (i+1) + (length+1)
            if length > 128:
                run = data[i+1]*(257-length)
                decoded.append(run)
                i = (i+1) + 1
        return b''.join(decoded)
    
    @classmethod
    def encode(cls, data):
        out = BytesIO()
        for c in data:
            out.write(b"\x00" + c)
        return out.getvalue()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
# The following code has been taken from PDFPy2
# https://github.com/mstamy2/PyPDF2/
#
# The 3-Clause BSD License
#
# Copyright (c) 2006-2008, Mathieu Fenniak
# Some contributions copyright (c) 2007, Ashish Kulkarni <kulkarni.ashish@gmail.com>
# Some contributions copyright (c) 2014, Steve Witham <switham_github@mac-guyver.com>
# 
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
# 
# * Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
# * The name of the author may not be used to endorse or promote products
# derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class ASCIIHexDecoder(object):
    """
    ASCIIHexDecode filter: PDFReference v1.4 section 3.3.1
    For each pair of ASCII hexadecimal digits (0-9 and A-F or a-f), the
    ASCIIHexDecode filter produces one byte of binary data. All white-space
    characters are ignored. A right angle bracket character (>) indicates
    EOD. Any other characters will cause an error. If the filter encounters
    the EOD marker after reading an odd number of hexadecimal digits, it
    will behave as if a 0 followed the last digit.
    """
    @classmethod
    def decode(cls, data):
        retval = b""
        char = b""
        x = 0
        while True:
            c = data[x]
            if c == b">":
                break
            elif c.isspace():
                x += 1
                continue
            char += c
            if len(char) == 2:
                retval += chr(int(char, base=16))
                char = b""
            x += 1
        assert char == b""
        return retval

    @classmethod
    def encode(cls, data):
        try:
            return data.encode('hex')
        except Exception:
            raise PDFSurgeDecoderException('Error in hexadecimal conversion.')


class CCITTFaxDecoder(object):
    @classmethod
    def decode(cls, data, parameters):
        if parameters:
            if parameters.get("/K", 1) == -1:
                CCITTgroup = 4
            else:
                CCITTgroup = 3
        
        width = parameters.get("/Columns")
        height = parameters.get("/Height")
        imgSize = len(data)
        tiff_header_struct = '<' + '2s' + 'h' + 'l' + 'h' + 'hhll' * 8 + 'h'
        tiffHeader = struct.pack(
            tiff_header_struct,
            b'II',  # Byte order indication: Little endian
            42,  # Version number (always 42)
            8,  # Offset to first IFD
            8,  # Number of tags in IFD
            256, 4, 1, width,  # ImageWidth, LONG, 1, width
            257, 4, 1, height,  # ImageLength, LONG, 1, length
            258, 3, 1, 1,  # BitsPerSample, SHORT, 1, 1
            259, 3, 1, CCITTgroup,  # Compression, SHORT, 1, 4 = CCITT Group 4 fax encoding
            262, 3, 1, 0,  # Thresholding, SHORT, 1, 0 = WhiteIsZero
            273, 4, 1, struct.calcsize(tiff_header_struct),  # StripOffsets, LONG, 1, length of header
            278, 4, 1, height,  # RowsPerStrip, LONG, 1, length
            279, 4, 1, imgSize,  # StripByteCounts, LONG, 1, size of image
            0  # last IFD
        )
        
        return tiffHeader + data
    
    @classmethod
    def encode(cls, data, parameters):
        raise NotImplementedError('Encoding {0} is not implemented.'.format(cls.__name__))


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
# The following code has been inspired by both PyPDF2 (mentionned above)
# And MiniPDF
# https://github.com/feliam/miniPDF
#
# At the time of the writing, they didn't had a Licence
# but they still deserve a mention :)
#
# Some contributions copyright (c) 2007, Felipe Andres Manzano <felipe.andres.manzano@gmail.com>
# 
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Predictor(object):
    """
    7.4.4.4   LZW and Flate Predictor Functions
    LZW and Flate encoding compress more compactly if their input data is highly 
    predictable. One way of increasing the predictability of many continuous-tone 
    sampled images is to replace each sample with the difference between that sample
    and a predictor function applied to earlier neighboring samples. If the predictor 
    function works well, the postprediction data clusters toward 0.

    1  No prediction (the default value)
    2  TIFF Predictor 2
    10 PNG prediction (on encoding, PNG None on all rows)
    11 PNG prediction (on encoding, PNG Sub on all rows)
    12 PNG prediction (on encoding, PNG Up on all rows)
    13 PNG prediction (on encoding, PNG Average on all rows)
    14 PNG prediction (on encoding, PNG Paeth on all rows)
    15 PNG prediction (on encoding, PNG optimum)
    """
    @classmethod
    def encode(cls, data, predictor, columns, colors, bits):
        # TODO: To change, implementing and improving predictors 2, 10-15 ; and filter bytes 0 -> 4

        output = b''
        # PNG prediction
        if predictor >= 10 and predictor <= 15:
            # PNG prediction can vary from row to row
            for row in range(math.ceil(len(data) / columns)):
                rowdata = [x for x in data[(row * columns):((row + 1) * columns)]]
                filterByte = predictor - 10
                rowdata = [filterByte] + rowdata
                if filterByte == 0:
                    pass
                elif filterByte == 1:
                    for i in range(len(rowdata) - 1, 1, -1):
                        if rowdata[i] < rowdata[i - 1]:
                            rowdata[i] = rowdata[i] + 256 - rowdata[i - 1]
                        else:
                            rowdata[i] = rowdata[i] - rowdata[i - 1]
                else:
                    raise PDFSurgeDecoderException('Unsupported filter bype {0} on {1}.'.format(filterByte, cls.__name__))
                output += (''.join([chr(x) for x in rowdata]))
            return output
        else:
            raise PDFSurgeDecoderException('Unsupported predictor on {0}.'.format(cls.__name__))
    
    @classmethod
    def decode(cls, decoded, predictor, columns, colors, bits):
        def decode_row(rowdata, prev_rowdata):
            if predictor == 1:
                return rowdata
            if predictor == 2:
                #TIFF_PREDICTOR
                bpp = (bits + 7) / 8
                for i in range(bpp+1, rowlength):
                    rowdata[i] = (rowdata[i] + rowdata[i-bpp]) % 256
            # PNG prediction
            elif predictor >= 10 and predictor <= 15:
                filterByte = rowdata[0]
                if filterByte == 0:
                    pass
                elif filterByte == 1:
                    # prior 
                    bpp = (bits + 7) / 8
                    for i in range(bpp+1, rowlength):
                        rowdata[i] = (rowdata[i] + rowdata[i-1]) % 256
                elif filterByte == 2:
                    # up
                    for i in range(1, rowlength):
                        rowdata[i] = (rowdata[i] + prev_rowdata[i]) % 256
                elif filterByte == 3:
                    # average 
                    bpp = (bits + 7) / 8
                    for i in range(1, bpp):
                        rowdata[i] = (rowdata[i] + prev_rowdata[i]/2) % 256
                    for j in range(i, rowlength):
                        rowdata[j] = (rowdata[j] + (rowdata[j-bpp] + prev_rowdata[j])/2) % 256
                elif filterByte == 4:
                    # paeth filtering 
                    bpp = (bits + 7) / 8;
                    for i in range(1, bpp):
                        rowdata[i] = rowdata[i] + prev_rowdata[i];
                    for j in range(i, rowlength):
                        # fetch pixels 
                        a = rowdata[j-bpp]
                        b = prev_rowdata[j]
                        c = prev_rowdata[j-bpp]

                        # distances to surrounding pixels 
                        pa = abs(b - c)
                        pb = abs(a - c)
                        pc = abs(a + b - 2*c)

                        # pick predictor with the shortest distance 
                        if pa <= pb and pa <= pc :  
                            pred = a
                        elif pb <= pc:
                            pred = b
                        else:
                            pred = c
                        rowdata[j] = rowdata[j] + pred
                else:
                    raise PDFSurgeDecoderException("Unsupported PNG filter {0}".format(filterByte))

                return rowdata

        rowlength = columns + 1
        assert len(decoded) % rowlength == 0
        if predictor == 1 :
            return decoded

        output = BytesIO()

        # PNG prediction can vary from row to row
        prev_rowdata = (0,) * rowlength
        for row in range(0, math.ceil(len(decoded) / rowlength)):
            rowdata = decode_row([x for x in decoded[(row*rowlength):((row+1)*rowlength)]], prev_rowdata)
            if predictor in [1,2]:
                output.write(b''.join([bytes([x]) for x in rowdata[0:]]))
            else:
                output.write(b''.join([bytes([x]) for x in rowdata[1:]]))
            prev_rowdata = rowdata

        return output.getvalue()


class FlateDecoder(object):
    @classmethod
    def decode(cls, data, parameters):
        decoded = None
        try:
            decoded = zlib.decompress(data)
        except Exception:
            raise PDFSurgeDecoderException('Error while decompressing the data in FlateDecoder.')
        
        predictor = parameters.get('/Predictor', 1)
        columns = parameters.get('/Columns', 1)
        colors = parameters.get('/Colors', 1)
        bits = parameters.get('/BitsPerComponent', 8)

        if colors < 1:
            colors = 1
        
        if bits not in [1, 2, 4, 8, 16]:
            bits = 8
        
        if predictor != 1:
            return Predictor.decode(decoded, predictor, columns, colors, bits)
        
        return decoded

    
    @classmethod
    def encode(cls, data, parameters):
        predictor = parameters.get('/Predictor', 1)
        columns = parameters.get('/Columns', 1)
        colors = parameters.get('/Colors', 1)
        bits = parameters.get('/BitsPerComponent', 8)

        if colors < 1:
            colors = 1
        
        if bits not in [1, 2, 4, 8, 16]:
            bits = 8
        
        if predictor != 1:
            data = Predictor.encode(data, predictor, columns, colors, bits)
        
        try:
            return zlib.compress(data)
        except Exception:
            raise PDFSurgeDecoderException('Error while compressing the data in FlateDecoder.')


class LZWDecoder(object):
    """
    7.4.4.2   Details of LZW Encoding
    LZW (Lempel-Ziv-Welch) is a variable-length, adaptive compression method
    that has been adopted as one of the standard compression methods in the 
    Tag Image File Format (TIFF) standard. 

    Data encoded using the LZW compression method shall consist of a sequence 
    of codes that are 9 to 12 bits long. Each code shall represent a single 
    character of input data (0-255), a clear-table marker (256), an EOD marker
    (257), or a table entry representing a multiple-character sequence that has
    been encountered previously in the input (258 or greater).
    """
    @classmethod
    def decode(cls, data, parameters):
        assert parameters.get('/EarlyChange', 1) == 1

        decoded = None
        try:
            decoded = lzw.decompress(data)
        except Exception:
            raise PDFSurgeDecoderException('Error while decompressing the data in LZWDecoder.')

        predictor = parameters.get('/Predictor', 1)
        columns = parameters.get('/Columns', 1)
        colors = parameters.get('/Colors', 1)
        bits = parameters.get('/BitsPerComponent', 8)

        if colors < 1:
            colors = 1

        if bits not in [1, 2, 4, 8, 16]:
            bits = 8

        if predictor != 1:
            return Predictor.decode(decoded, predictor, columns, colors, bits)

        return decoded
    
    @classmethod
    def encode(cls, data, parameters):
        assert parameters.get('/EarlyChange', 1) == 1

        predictor = parameters.get('/Predictor', 1)
        columns = parameters.get('/Columns', 1)
        colors = parameters.get('/Colors', 1)
        bits = parameters.get('/BitsPerComponent', 8)

        if colors < 1:
            colors = 1

        if bits not in [1, 2, 4, 8, 16]:
            bits = 8

        if predictor != 1:
            data = Predictor.encode(data, predictor, columns, colors, bits)

        try:
            return ''.join(lzw.compress(data))
        except:
            raise PDFSurgeDecoderException('Error while compressing the data in LZWDecoder.')
