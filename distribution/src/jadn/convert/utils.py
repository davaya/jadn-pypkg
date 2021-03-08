"""
Conversion utilities
"""
from typing import Callable, Tuple, Union
from lxml.etree import Element, tostring  # pylint: disable=E0611
from lxml.html import builder


class Doc:
    """
    Base class generating html/xml documents using context managers
    """
    # Context vars
    parent: Union[None, 'Doc.Tag']
    # Class vars
    init: str
    value: None

    def __init__(self, init: str = None, **kwargs):
        # Context vars
        self.parent = None
        # Class Vars
        self.init = init or ''
        self.value = None

    def getvalue(self, pretty: bool = False) -> str:
        return tostring(self.value, pretty_print=pretty, doctype=self.init).decode()

    def context(self) -> Tuple['Doc', Callable]:
        return self, self.tag

    def tag(self, name: str, text: str = None, **kwargs) -> 'Doc.Tag':
        tmp = self.__class__.Tag(self, name, text, **kwargs)
        (self.parent or self).value.append(tmp.value)
        return tmp

    class Tag:
        """
        Base class for html/xml elements using context managers
        """
        # Context vars
        doc: 'Doc'
        parent: Union[None, 'Tag']
        # Class vars
        value: None

        def __init__(self, doc: 'Doc', name: str, text: str = None, **kwargs):
            # Context vars
            self.doc = doc
            self.parent = None
            # Class Vars
            self.value = None

        def __enter__(self):
            self.parent = self.doc.parent
            self.doc.parent = self

        def __exit__(self, exc_type, exc_val, exc_tb):
            (self.parent or self.doc).value.append(self.value)
            self.doc.parent = self.parent


class DocHTML(Doc):
    """
    class generating html documents using context managers
    """
    # Context vars
    parent: Union[None, 'Tag']
    # Class vars
    init: str
    value: builder.HTML

    def __init__(self, init: str = None, **kwargs):
        super().__init__(init, **kwargs)
        self.value = builder.HTML(**kwargs)

    def getvalue(self, pretty: bool = False) -> str:
        return tostring(self.value, method='html', pretty_print=pretty, doctype=self.init).decode()

    class Tag(Doc.Tag):
        # Context vars
        doc: 'DocHTML'
        parent: Union[None, 'Tag']
        # Class vars
        value: builder.E

        def __init__(self, doc: 'DocHTML', name: str, text: str = None, **kwargs):
            super().__init__(doc, name, text, **kwargs)
            if cls := kwargs.pop('klass', None):
                kwargs['class'] = cls
            child = (text, ) if text else ()
            self.value = getattr(builder, name.upper())(*child, **kwargs)


class DocXML(Doc):
    """
    Base class generating xml documents using context managers
    """
    # Context vars
    parent: Union[None, 'DocXML.Tag']
    # Class vars
    init: str
    value: Element

    def __init__(self, init: str = None, **kwargs):
        super().__init__(init, **kwargs)
        self.value = builder.HTML(**kwargs)

    class Tag(Doc.Tag):
        # Context vars
        doc: 'DocXML'
        parent: Union[None, 'Tag']
        # Class vars
        value: Element

        def __init__(self, doc: 'DocXML', name: str, text: str = None, **kwargs):
            super().__init__(doc, name, text, **kwargs)
            if cls := kwargs.pop('klass', None):
                kwargs['class'] = cls
            self.value = Element(name, attrib=kwargs)
            if text:
                self.value.text = text

        def __enter__(self):
            self.parent = self.doc.parent
            self.doc.parent = self

        def __exit__(self, exc_type, exc_val, exc_tb):
            (self.parent or self.doc).value.append(self.value)
            self.doc.parent = self.parent


__all__ = [
    'DocHTML',
    'DocXML'
]
