import glob
import os
import lxml.etree as ET
import re
import yaml
from marko.ext.gfm import gfm

tei_ns = "https://tei-c.org/ns/1-0/"
ns_decl = {"tei": tei_ns}



def write_to_log(message):
    with open("logs/log.txt", "a") as log_file:
        log_file.write("\n" + message)


def write_tree(tree, path):
    with open(path, "w") as debug:
        debug.write(ET.tostring(tree).decode('utf8'))


def xmlify(path):
    """
    This function takes a md file and returns a TEI-like document (not fully compliant though)
    :param path: path to the md file
    :return: None; creates a TEI file
    """
    # TODO: get back to endnotes

    # Getting the path to output file
    with open(path, "r") as input_file:
        as_text = input_file.read()

    filename = file.split("/")[-1].replace(".md", "")

    ## Metadata management; yaml-xml conversion
    metadata_as_yaml = as_text.split("---")[1]
    python_dict = yaml.load(metadata_as_yaml, Loader=yaml.SafeLoader)
    metadata = ET.Element("metadata")
    for key, values in python_dict.items():
        new_element = ET.Element(key)
        if type(values) is list:
            print(values)
            new_element.text = ",".join(values)
        else:
            new_element.text = str(values)
        metadata.append(new_element)
    metadata_as_xml = ET.tostring(metadata, pretty_print=True, encoding='utf8').decode()
    # We remove the metadata from the text file
    transformed = as_text.replace(metadata_as_yaml, "")
    ## Metadata management

    # GFM extension of marko parses tables too.
    converted_doc = gfm.convert(transformed)
    parser = ET.HTMLParser(recover=True)
    tree = ET.parse(converted_doc, parser=parser)
    write_tree(tree, f"html/{filename}.html")


    with open(f"../../data/to_tei/{dir_name}/{lesson_name}.xml", "w") as output_file:
        # TODO: single asterisks are not rendered and break the HTML. After ET recovery, they are lost. I suppose the same
        # TODO: happens with other chars. It's annoying.
        # TODO: Another problem with regexp lesson: last urls disapear.
        # TODO: linebreaks in code are removed by lxml. 
        output_file.write(ET.tostring(lesson_as_xml_tree, pretty_print=True).decode('utf-8'))


if __name__ == '__main__':
    for file in glob.glob("data/characters/punctuations/*.md"):
        print(file)
        xmlify(file)