# -*- coding: utf-8 -*-

__author__ = "Cyril Nicodeme"
__author_email__ = "cyril@pdfshift.io"

layouts = ('/NoLayout', '/SinglePage', '/OneColumn', '/TwoColumnLeft', '/TwoColumnRight', '/TwoPageLeft', '/TwoPageRight')
pagemodes = ('/UseNone', '/UseOutlines', '/UseThumbs', '/FullScreen', '/UseOC', '/UseAttachments')

escaped_dict = {
    b'n': b'\n',
    b'r': b'\r',
    b't': b'\t',
    b'b': b'\b',
    b'f': b'\f',
    b'c': b'\c',
    b'(': b'(',
    b')': b')',
    b'/': b'/',
    b'\\': b'\\',
    b' ': b' ',
    b'%': b'%',
    b'<': b'<',
    b'>': b'>',
    b'[': b'[',
    b']': b']',
    b'#': b'#',
    b'_': b'_',
    b'&': b'&',
    b'$': b'$'
}