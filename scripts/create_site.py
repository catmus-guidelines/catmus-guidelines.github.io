import glob
import os
import sys

import lxml.etree as ET
import lxml.html as lhtml
import yaml

from marko import Markdown
from jinja2 import Environment, FileSystemLoader
from bs4 import BeautifulSoup
import git
import datetime


def write_to_log(message):
    with open("logs/log.txt", "a") as log_file:
        log_file.write("\n" + message)


def write_tree(tree, path):
    with open(path, "w") as debug:
        debug.write(ET.tostring(tree).decode('utf8'))


def write_file(string, path):
    with open(path, "w") as out_file:
        out_file.write(string)

def last_update():
    return datetime.datetime.today().strftime('%Y-%m-%d')

def get_last_commit():
    repo = git.Repo(search_parent_directories=True)
    return repo.head.object.hexsha[:10]
     
def first_letter_uppercase(string):
    return string[0].upper() + string[1:]

func_dict = {
    "first_letter_uppercase": first_letter_uppercase,
    "get_last_commit": get_last_commit,
    "last_update": last_update,
}


def create_index(yaml_list, title, template):
    """
    This function creates the index of characters using the set of md files that has been validated 
    before. This index takes the form of a table of characters with the group, name, label, transcription,
    images, and corresponding chars.
    
    :param yaml_list: the dict to be used to create the table
    :param title: page title
    :param template: the root template to be used
    :return: None
    """
    try:
        os.mkdir("html/characters")
    except FileExistsError:
        pass
    
    # Let's create the table
    table = ET.Element("table")
    thead = ET.SubElement(table, 'thead')
    trhead = ET.SubElement(thead, 'tr')
    for item in ['Group', 'Char', 'Name',  'Examples' , 'Label', 'Corresponding characters']:
        td = ET.SubElement(trhead, 'th')
        td.text = item
    tbody = ET.SubElement(table, 'tbody')
    for yaml_dict in yaml_list:
        tr = ET.SubElement(tbody, "tr")
        for item in ['group', 'char', 'name', 'examples', 'label', 'corresp']:
            try:
                if isinstance(yaml_dict[item], str):
                    value = yaml_dict[item]
                elif isinstance(yaml_dict[item], list):
                    if isinstance(yaml_dict[item][0], dict):
                        value = "\u00A0".join(it['transcription'] for it in yaml_dict[item])
                    else:
                        value = ""
            except KeyError:
                value = ''
            td = ET.SubElement(tr, "td")
            if item == 'corresp':
                td.set('class', 'indexchars')
                td.text = value
            elif item == 'name':
                ref = ET.SubElement(td, 'a')
                ref.set('href', f"{yaml_dict['abspath']}/{yaml_dict['html_path']}")
                ref.text = value
            elif item == 'examples':
                if len(yaml_dict[item]) > 2:
                    example_list = yaml_dict[item][:2]
                elif len(yaml_dict[item]) == 1:
                    example_list = yaml_dict[item]
                else:
                    example_list = []
                for example in example_list:
                    span = ET.SubElement(td, "span")
                    span.set("class", "image")
                    img = ET.SubElement(span, 'img')
                    img.set('src', f"{yaml_dict['abspath']}/{example}")
                
            else:
                td.text = value
    
    # Let's build the homepage
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template(template)
    # https://saidvandeklundert.net/2020-12-24-python-functions-in-jinja/
    template.globals.update(func_dict)
    yaml_dict['title'] = title
    html_string = template.render(yaml_dict)


    # We insert the created table
    converted_doc = "<div>" + ET.tostring(table).decode() + "</div>"
    to_insert = ET.fromstring(converted_doc)
    parser = ET.HTMLParser(recover=True)
    html_index = ET.fromstring(html_string, parser=parser)
    main_div = html_index.xpath("//div[@class='chrome:main']")[0]
    main_div.append(to_insert)
    
    # We use BeautifulSoup to manage the script element
    soup = BeautifulSoup(ET.tostring(html_index), 'html.parser')
    soup = soup.prettify()
    with open(f"html/characters/index_of_characters.html", "w") as index:
        index.write(soup)

def create_pages(yaml_dict, title, template, md_source, out_dir, lang, index_page=False):
    """
    This function creates an HTML page out of an markdown document, using marko transformation and jinja HTML templating.
    
    :param yaml_dict: The dictionnary that will be used by the templating dict
    :param title: the page title
    :param template: the path to the root template
    :param md_source: the path to the md source
    :param out_dir: path to out dir
    :param lang: lang for localisation
    :param index_page: Whether the page created is the index or not.
    :return: None
    """
    try:
        os.mkdir("html/guidelines")
    except FileExistsError:
        pass
    try:
        os.mkdir(f"html/guidelines/{lang}")
    except FileExistsError:
        pass
    if index_page is True:
        lang_dir = ""
        if lang == "fr":
            suffix = f"-{lang}"
        else:
            suffix = ""
    else:
        suffix = ""
        lang_dir = f"{lang}/"
    # Let's build the homepage
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template(template)
    # https://saidvandeklundert.net/2020-12-24-python-functions-in-jinja/
    template.globals.update(func_dict)
    yaml_dict['lang'] = lang
    yaml_dict['title'] = title
    html_string = template.render(yaml_dict)
    
    
    with open(md_source, "r") as index_page:
        md_doc = index_page.read()

    markdown = Markdown(extensions=['footnote'])
    converted_doc = markdown.convert(md_doc)
    converted_doc = converted_doc.replace("<hr />", "")
    converted_doc = "<div>" + converted_doc + "</div>"
    to_insert = ET.fromstring(converted_doc)

    parser = ET.HTMLParser(recover=True)
    html_index = ET.fromstring(html_string, parser=parser)
    main_div = html_index.xpath("//div[@class='chrome:main']")[0]
    main_div.append(to_insert)
    soup = BeautifulSoup(ET.tostring(html_index), 'html.parser')
    soup = soup.prettify()
    with open(f"{out_dir}/{lang_dir}{md_source.split('/')[-1].replace('.md', '')}{suffix}.html", "w") as index:
        index.write(soup)



def create_character_page(file_and_class:tuple, surrounding_files:tuple, pages_dictionnary:dict) -> dict:
    """
    This function takes a md file and produces html files. For now there is no localisation of the characters 
    table. It is english-only.
    :param file_and_class: the filename and class
    :param surrounding_files: the file describing the next and previous char (by alph. order)
    :param pages_dictionnary: the dictionnary that contains some metadata (path to github repo and pages for instance)
    :return: a dictionnary containing the information about the character
    """
    
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
    ## Metadata management

    # GFM extension of marko parses tables too.
    markdown = Markdown(extensions=['footnote'])
    converted_doc = markdown.convert(transformed)
    converted_doc = converted_doc.replace("<hr />", "")
    converted_doc = "<div>" + converted_doc + "</div>"
    parser = ET.HTMLParser(recover=True)
    character_description = ET.fromstring(converted_doc)
    character_description.set("class", "natural_language_desc")
    yaml_data = python_dict
    
    # Next and previous chars management
    previous_file, next_file = surrounding_files
    next_and_previous = ET.Element("div")
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
    # The template is hardcoded.
    template = env.get_template('templates/char_template.html')
    # https://saidvandeklundert.net/2020-12-24-python-functions-in-jinja/
    template.globals.update(func_dict)
    
    
    # Render template with YAML data and save to HTML file
    yaml_data['class'] = classe
    yaml_data['path'] = path
    yaml_data = {**yaml_data, **pages_dictionnary}
    output = template.render(yaml_data)
    
    # We add next and previous char link
    character_table = ET.fromstring(output, parser=parser)
    description_div = character_table.xpath("//div[@id='description']")
    description_div[0].append(character_description)
    next_previous_div = character_table.xpath("//div[@id='next_previous']")[0]
    next_previous_div.append(next_and_previous)
    
    # And script element
    script_element = lhtml.Element("script")
    script_element.set('src', '../assets/js/accordian.js')
    # head_node[0].append(script_element)

    # BeautifulSoup is used to manage the script element and create a working HTML file
    soup = BeautifulSoup(ET.tostring(character_table), 'html.parser')
    soup = soup.prettify()
    
    # Let's create the dirs
    try:
        os.mkdir("html")
    except FileExistsError:
        pass

    try:
        os.mkdir("html/characters")
    except FileExistsError:
        pass
    html_path = f"html/characters/{filename}.html"
    
    # And write the file.
    with open(html_path, 'w') as file:
        file.write(soup)
        # file.write(ET.tostring(soup, encoding='utf-8').decode())
    yaml_data['html_path'] = html_path
    return yaml_data


def create_site():
    pages = []
    files = glob.glob("data/characters/punctuations/*.md")
    
    # Let's sort the files so that we can add a next/previous link
    files.sort(key=lambda x: x.split("/")[-1])
    for index, file in enumerate(files):
        filename = file.split("/")[-1].replace(".md", "")
        classe = file.split("/")[-2]
        pages.append((filename, classe))

    pages_as_dict = dict()
    for page in pages:
        nom_fichier, classe = page
        try:
            pages_as_dict[classe].append(nom_fichier)
        except KeyError:
            pages_as_dict[classe] = [nom_fichier]

    
    # We create a dynamic absolute path to use it on local build or online
    if sys.argv[1] == "local":
        abspath = "/home/mgl/Bureau/Travail/projets/HTR/CatMus/website"
    else:
        abspath = sys.argv[1]
    pages_as_dict = {"classes": pages_as_dict,
                     "abspath": abspath}

    all_chars = []
    for index, file in enumerate(files):
        try:
            next_file = files[index + 1]
        except IndexError:
            next_file = None
        try:
            previous_file = files[index - 1]
        except IndexError:
            previous_file = None
            
        new_char = create_character_page((file, classe), (previous_file, next_file), pages_as_dict)
        all_chars.append(new_char)

    # Create guidelines pages

    # Create french index age that is the default page (to be modified if needed)
    # create_pages(yaml_dict=pages_as_dict,
    #              title='Présentation',
    #              template='templates/index.html',
    #              md_source=f"data/guidelines/fr/index.md",
    #              out_dir=".",
    #              lang="fr",
    #              index_page=True)
    # Create english index page
    create_pages(yaml_dict=pages_as_dict,
                 title='Présentation',
                 template='templates/index.html',
                 md_source=f"data/guidelines/en/index.md",
                 out_dir=".",
                 lang="en",
                 index_page=True)
    

    # Create 404
    current_dict = pages_as_dict
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template("templates/404.html")
    template.globals.update(func_dict)
    output = template.render(current_dict)
    soup = BeautifulSoup(output, 'html.parser')
    soup = soup.prettify()
    with open("404.html", 'w') as file:
        file.write(soup)
        
        
    # Create searchpage
    current_dict = pages_as_dict
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template("templates/in"
                                "dex.html")
    current_dict['title'] = "Search results"
    template.globals.update(func_dict)
    output = template.render(current_dict)
    soup = BeautifulSoup(output, 'html.parser')
    soup = soup.prettify()
    with open("search.html", 'w') as file:
        file.write(soup)
        

    # Now create each page in the target languages
    for lang in ['en']:
        for name, title in {'abreviations': "Abréviations",
                            'ligatures': "Ligatures",
                            'chiffres': "Chiffres",
                            'segmentation': "Segmentation linguistique",
                            'generalites': "Principes généraux",
                            'ponctuation': "Ponctuation",
                            'majuscules': "Majuscules",
                            'ramistes': "Distinction des « u » et des « v », des « i » et des « j »",
                            'lettres_generalites': "Généralités"}.items():
            create_pages(yaml_dict=pages_as_dict,
                         title=title,
                         template='templates/index.html',
                         md_source=f"data/guidelines/{lang}/{name}.md",
                         out_dir=f"html/guidelines",
                         lang=lang)

    # Finally, create the index of characters using the info gathered before
    create_pages(yaml_dict=pages_as_dict,
                 title=title,
                 template='templates/404.html',
                 md_source=f"data/guidelines/{lang}/{name}.md",
                 out_dir=f"html/guidelines",
                 lang=lang)
    


if __name__ == '__main__':
    create_site()
    