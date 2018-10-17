# -*- coding: utf-8 -*-

__author__ = "Cyril Nicodeme"
__author_email__ = "cyril@pdfshift.io"


class PDFSurgeException(Exception):
    pass


class PDFSurgeStreamError(PDFSurgeException):
    pass


class PDFParserException(PDFSurgeException):
    pass


class PDFSurgeDecoderException(PDFSurgeException):
    pass