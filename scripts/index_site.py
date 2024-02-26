import glob
import uuid
import re
import lxml.etree as ET

def index():
    index = list()
    spaces_replacement = re.compile(r"\s+")
    for html_page in glob.glob("html/guidelines/*/*.html"):
        title = html_page.split("/")[-1].replace(".html", "")
        parsed = ET.parse(html_page)
        paragraphs = parsed.xpath("//p")
        if len(paragraphs) > 0:
            for paragraph in paragraphs:
                par_dict = dict()
                par_dict['id'] = str(uuid.uuid4())
                par_dict['url'] = html_page
                paragraph_text = re.sub(spaces_replacement, ' ', paragraph.text)
                par_dict['par'] = paragraph_text
                par_dict['title'] = title
            index.append(par_dict)
    print(index)
        



if __name__ == '__main__':
    index()