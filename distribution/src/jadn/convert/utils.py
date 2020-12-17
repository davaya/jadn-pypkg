"""
Conversion utilities
"""
from typing import Dict, List, NoReturn, Tuple, Union


class Tag:
    """
    Tag element
    """
    name: str
    contents: Union[str, List['Tag']]
    attrs: Dict[str, str]
    _escapes: Dict[str, str] = {}
    _self_closing: Tuple[str, ...] = ()

    def __init__(self, name: str, value: Union[str, 'Tag', List['Tag']] = None, **attrs: Union[int, float, str, None]):
        self.name = name.lower()
        self.attrs = {**attrs}
        if self.name in self._self_closing and value:
            raise ValueError('Self closing tag should not have a value')
        if isinstance(value, str):
            self.contents = self._escape_value(value)
        elif isinstance(value, list):
            self.contents = value
        elif isinstance(value, Tag):
            self.contents = [value]
        else:
            self.contents = []

    def __str__(self) -> str:
        attrs = ' '.join(f'{k}="{v}"' if v else k for k, v in self.attrs.items())
        attrs = f' {attrs}' if attrs else ''
        if self._is_self_closing(self.name):
            return f'<{self.name}{attrs} />'

        value = self.contents if isinstance(self.contents, str) else ''.join(f'{v}' for v in self.contents)
        return f'<{self.name}{attrs}>{value}</{self.name}>'

    def append(self, *value: 'Tag') -> NoReturn:
        if self.name in self._self_closing:
            raise ValueError('Self closing tag should not have a value')
        if isinstance(self.contents, str):
            raise ValueError('Cannot add to string content')
        self.contents.extend(value)

    def prepend(self, *value: 'Tag') -> NoReturn:
        if self.name in self._self_closing:
            raise ValueError('Self closing tag should not have a value')
        if isinstance(self.contents, str):
            raise ValueError('Cannot add to string content')
        self.contents = [*value, *self.contents]

    def _escape_value(self, val: str) -> str:
        return ''.join(self._escapes.get(c, c) for c in val)

    def _is_self_closing(self, tag: str) -> bool:
        return tag in self._self_closing


class HtmlTag(Tag):
    """
    HTML Tag element
    """
    _escapes = {
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&apos;'
    }
    _self_closing = ('area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr')


# TODO: fill in escape and self_closing vars
class XmlTag(Tag):
    """
    XML Tag element
    """
    _escapes = {}
    _self_closing = ()
