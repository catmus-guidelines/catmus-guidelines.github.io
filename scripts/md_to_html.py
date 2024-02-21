import glob
import os
import lxml.etree as ET
import lxml.html as lhtml
from lxml.html import builder as E
import re
import yaml
from marko.ext.gfm import gfm
from jinja2 import Environment, FileSystemLoader
from bs4 import BeautifulSoup




def write_to_log(message):
    with open("logs/log.txt", "a") as log_file:
        log_file.write("\n" + message)


def write_tree(tree, path):
    with open(path, "w") as debug:
        debug.write(ET.tostring(tree).decode('utf8'))


def write_file(string, path):
    with open(path, "w") as out_file:
        out_file.write(string)
        


def htmlify(file_and_class, surrounding_files, full_dict):
    """
    This function takes a md file and returns a TEI-like document (not fully compliant though)
    :param path: path to the md file
    :return: None; creates a TEI file
    """
    # TODO: get back to endnotes
    path, classe = file_and_class
    # Getting the path to output file
    with open(path, "r") as input_file:
        as_text = input_file.read()

    filename = path.split("/")[-1].replace(".md", "")

    ## Metadata management; yaml-xml conversion
    metadata_as_yaml = as_text.split("---")[1]
    python_dict = yaml.load(metadata_as_yaml, Loader=yaml.SafeLoader)
    # We remove the metadata from the text file
    transformed = as_text.replace(metadata_as_yaml, "")
    print(transformed)
    ## Metadata management

    # GFM extension of marko parses tables too.
    converted_doc = gfm.convert(transformed)
    converted_doc = converted_doc.replace("<hr />", "")
    converted_doc = "<div>" + converted_doc + "</div>"
    parser = ET.HTMLParser(recover=True)
    character_description = ET.fromstring(converted_doc)
    character_description.set("class", "natural_language_desc")
    yaml_data = python_dict
    
    # Next and previous files
    previous_file, next_file = surrounding_files
    next_and_previous = ET.Element("div")
    print(surrounding_files)
    if previous_file != None:
        previous_file_path = previous_file.split("/")[-1].replace(".md", "")
        out_previous_file_path = f"{previous_file_path}.html"
        span = ET.Element("span")
        span.set("class", "previous")
        previous = ET.Element("a")
        previous.set("href", out_previous_file_path)
        previous.text = f"Previous character: {previous_file_path}"
        next_and_previous.append(span)
        span.append(previous)
    if next_file != None:
        next = ET.Element("a")
        next_file_path = next_file.split("/")[-1].replace(".md", "")
        out_next_file_path = f"{next_file_path}.html"
        next.set("href", out_next_file_path)
        next.text = f"Next character: {next_file_path}"
        span = ET.Element("span")
        span.set("class", "next")
        next_and_previous.append(span)
        span.append(next)
    
        
    

    # Load Jinja2 template from file
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template('templates/char_template.html')

    # Render template with YAML data and save to HTML file
    yaml_data['class'] = classe
    yaml_data['path'] = path
    yaml_data = {**yaml_data, **full_dict}
    print(yaml_data)
    output = template.render(yaml_data)
    character_table = ET.fromstring(output, parser=parser)
    character_table_body = character_table.xpath("//body")
    description_div = character_table.xpath("//div[@id='description']")
    description_div[0].append(character_description)
    next_previous_div = character_table.xpath("//div[@id='next_previous']")[0]
    next_previous_div.append(next_and_previous)
    
    head_node = character_table.xpath("//head")
    script_element = lhtml.Element("script")
    script_element.set('src', '../assets/js/accordian.js')
    # head_node[0].append(script_element)

    soup = BeautifulSoup(ET.tostring(character_table), 'html.parser')
    soup = soup.prettify()
    
    try:
        os.mkdir("html")
    except FileExistsError:
        pass
    with open(f"html/{filename}.html", 'w') as file:
        file.write(soup)
        # file.write(ET.tostring(soup, encoding='utf-8').decode())


if __name__ == '__main__':
    pages = []
    files = glob.glob("data/characters/punctuations/*.md")
    files.sort(key=lambda x:x.split("/")[-1])
    files_dict = {}
    for index, file in enumerate(files):
        filename = file.split("/")[-1].replace(".md", "")
        classe = file.split("/")[-2]
        print(file)
        pages.append((filename, classe))

    pages_as_dict = dict()
    for page in pages:
        nom_fichier, classe = page
        try:
            pages_as_dict[classe].append(nom_fichier)
        except KeyError:
            pages_as_dict[classe] = [nom_fichier]
    pages_as_dict = {"classes": pages_as_dict}

    for index, file in enumerate(files):
        try:
            next_file = files[index + 1]
        except IndexError:
            next_file = None
        try:
            previous_file = files[index - 1]
        except IndexError:
            previous_file = None
        htmlify((file, classe), (next_file, previous_file), pages_as_dict)
    references = ""
    references_global = ""
    for classe, examples in pages_as_dict.items():
        for page in pages:
            nom_fichier, classe = page
            references += f"<li><a href=\"html/{nom_fichier}.html\">{nom_fichier}</a></li>"
        references_global += f"<li>{classe}<ul>{references}<ul></li>"
    html_string = f"<!DOCTYPE html><html><body><ul>{references_global}<ul></body></html>"
    with open("index.html", "w") as index:
        index.write(html_string)
        
    