#!/usr/bin/env python3
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional, Union, TextIO, BinaryIO
from .helper import StrFormat


def Feed2List(
    fp: Optional[Union[TextIO, BinaryIO]],
    *, keys: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    ''' Parse RSS or Atom feed and return list of entries. '''
    def parse_without_namespace(file: Union[TextIO, BinaryIO]) -> ET.Element:
        ns = {}
        xml_iter = ET.iterparse(file, ('start-ns', 'start'))
        for event, elem in xml_iter:
            if event == 'start-ns':
                ns['{' + elem[1]] = elem[0] + ':' if elem[0] else ''
            elif event == 'start':
                tag = elem.tag.split('}')
                elem.tag = ''.join(ns[x] for x in tag[:-1]) + tag[-1]
        return xml_iter.root

    if not fp:
        return []
    # detect feed format (RSS / Atom)
    root = parse_without_namespace(fp)
    fp.close()
    if root.tag == 'rss':  # RSS
        selector = 'channel/item'
        date_fields = ['pubDate', 'lastBuildDate']
    elif root.tag == 'feed':  # Atom
        selector = 'entry'
        date_fields = ['updated', 'published']
    else:
        raise NotImplementedError('Unrecognizable feed format')

    # parse XML
    result = []
    for item in root.findall(selector):
        obj = {}  # type: Dict[str, Any]
        for child in item:
            tag = child.tag
            # Filter keys that are clearly not wanted by user
            if keys and tag not in keys:
                continue
            value = (child.text or '').strip()
            # For date-fields, create and return date
            if tag in date_fields:
                value = StrFormat.to_date(value)
            # Return dict if has attributes or string without attribs
            attr = child.attrib
            if attr:
                if value:
                    attr[''] = value
                value = attr
            # Auto-create list type if duplicate keys are used
            try:
                prev_val = obj[tag]
                if not isinstance(prev_val, list):
                    obj[tag] = [prev_val]
                obj[tag].append(value)
            except KeyError:
                obj[tag] = value
        # Each entry has a key-value-dict. Value may be string or attrib-dict.
        # Value may also be a list of mixed string and attrib-dict values.
        result.append(obj)
    return result
