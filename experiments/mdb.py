from bs4 import BeautifulSoup
import requests
import logging
import json
import os

url = 'https://docs.mindsdb.com/sitemap.xml'
response = requests.get(url)
soup = BeautifulSoup(response.text, 'xml')

docs_links = []
for url in soup.find_all('url'):
    loc = url.find('loc').text
    docs_links.append(loc)
docs_text = []
for i, doc_link in enumerate(docs_links[:2]):
    try:
        page_link = requests.get(doc_link)
        soup = BeautifulSoup(page_link.text, "html.parser")
        title = soup.title.string.strip() if soup.title else "No title available" #page title
        text = ""
        source_links=[]
        # div = soup.find('div', class_='flex flex-row pt-9 gap-12 items-stretch')
        for element in soup.find('div', class_='flex flex-row pt-9 gap-12 items-stretch'):
            for child in element.descendants:
                if child.name == "a" and child.has_attr("href"):
                    url = child.get("href")
                    if url is not None and "edit" in url:
                        text += child.get_text()
                    else:
                        if url.startswith("/") or "#" in url:
                            text += f"{child.get_text()} (Reference url: {doc_link}{url}) "
                            source_links.append(url)
                        else:
                            text += f"{child.get_text()} "
                elif child.name == "div" and "gray-frame" in child.get("class", []):
                    codeblock = child.find('code')
                    markdown = f"```{os.linesep}{codeblock.text}{os.linesep}```"
                    text += markdown
                elif child.string and child.string.strip():
                    text += child.string.strip() + " "

        docs_text.append({'id': i+1, 'page_link': doc_link, 'title': title, 'text': text, 'source_links': source_links})
    except Exception as e:
        logging.error(f"Could not extract text from {doc_link}: {e}")
        continue

# write docs_text to a JSON file
with open('do_text.json', 'w') as f:
    json.dump(docs_text, f)