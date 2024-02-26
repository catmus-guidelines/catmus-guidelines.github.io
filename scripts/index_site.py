import glob
import uuid
import re
import lxml.etree as ET
import json

def create_id():
    id = f"id_{str(uuid.uuid4()).split('-')[0]}"
    return id

def index(xpath):
    """
    This function indexes the pages of a site and add UUID to each node (node)
    :return: None
    """
    index = list()
    spaces_replacement = re.compile(r"\s+")
    for html_page in glob.glob("html/guidelines/*/*.html"):
        title = html_page.split("/")[-1].replace(".html", "")
        parsed = ET.parse(html_page)
        searched_nodes = parsed.xpath(xpath)
        if len(searched_nodes) > 0:
            for node in searched_nodes:
                id = create_id()
                node.set("id", id)
                par_dict = dict()
                par_dict['id'] = id
                par_dict['url'] = html_page
                paragraph_text = re.sub(spaces_replacement, ' ',  ''.join(node.itertext()))
                par_dict['node'] = paragraph_text
                par_dict['title'] = title
                index.append(par_dict)
        with open(html_page, "w") as output_html_with_id:
            output_html_with_id.write(ET.tostring(parsed).decode('utf-8'))
    
    with open("json/index.json", "w") as index_file:
        index_file.write(json.dumps(index, indent=4))



if __name__ == '__main__':
    index("//node()[self::p or self::ul or self::ol]")