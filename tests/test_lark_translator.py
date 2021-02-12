from lark_translator import __version__, Translator, format_infix_spaces
import xml.etree.ElementTree as ET
from pprint import pprint
from os import path

current_dir = path.dirname(__file__)

def test_version():
    assert __version__ == '0.1.0'

def test_translate_acl():
    tr = Translator({
        "acl_string": path.join(current_dir, "grammars", "fipa_acl_str.lark"),
        "acl_python": path.join(current_dir, "grammars", "fipa_acl_py.lark")
    }, start="acl_communicative_act")

    in_msg = """(inform
        :sender ( agent-identifier :name i :addresses ( sequence iiop://foo.com/acc ) userparam value )
        :receiver ( set ( agent-identifier :name j ) )
        :in-reply-to q543
        :reply-by 20210214T083000000Z
        :content
            "weather (today, raining)"
        :language Prolog)
    """

    out_msg = tr.translate(in_msg, "acl_string", "acl_python")

    back_msg = tr.translate(out_msg, "acl_python", "acl_string", format_infix_spaces)

def test_translate_json():
    tr = Translator({
        "json": path.join(current_dir, "grammars", "json.lark"),
        "json_xml": path.join(current_dir, "grammars", "json-xml.lark")
    }, start="value")

    simple_obj = tr.translate("""
        <object><property name="test">Hello!</property></object>
    """, "json_xml", "json")

    assert simple_obj == '{"test":"Hello!"}'

    with open("tests/test.json", encoding='utf8') as f:
        in_json = f.read()
    
    out_xml = tr.translate(in_json, "json", "json_xml")

    root_element = ET.fromstring(out_xml)
    assert root_element.tag == "list"
    new_xml = ET.tostring(root_element, encoding='unicode')

    back_json = tr.translate(new_xml, "json_xml", "json")