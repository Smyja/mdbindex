"""Beautiful Soup Web scraper."""
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urljoin

from gpt_index.readers.base import BaseReader
from gpt_index.readers.schema.base import Document

logger = logging.getLogger(__name__)
def _substack_reader(soup: Any) -> Tuple[str, Dict[str, Any]]:
    """Extract text from Substack blog post."""
    extra_info = {
        "Title of this Substack post": soup.select_one("h1.post-title").getText(),
        "Subtitle": soup.select_one("h3.subtitle").getText(),
        "Author": soup.select_one("span.byline-names").getText(),
    }
    text = soup.select_one("div.available-content").getText()
    return text, extra_info


def _readthedocs_reader(soup: Any, url: str) -> Tuple[str, Dict[str, Any]]:
    """Extract text from a ReadTheDocs documentation site"""
    links = soup.find_all("a", {"class": "reference internal"})
    rtd_links = []

    for link in links:
        rtd_links.append(link["href"])
    for i in range(len(rtd_links)):
        if not rtd_links[i].startswith("http"):
            rtd_links[i] = urljoin(url, rtd_links[i])
    texts = []
    import requests
    from bs4 import BeautifulSoup

    for doc_link in rtd_links:
        page_link = requests.get(doc_link)
        soup = BeautifulSoup(page_link.text, "html.parser")
        try:
            text = soup.find(attrs={"role": "main"}).get_text()

        except IndexError:
            text = None
        if text:
            texts.append("\n".join([t for t in text.split("\n") if t]))
    return "\n".join(texts), {}


def _readmedocs_reader(soup: Any, url: str,include_url_in_text: bool = True) -> Tuple[str, Dict[str, Any]]:
    """Extract text from a ReadMe documentation site"""
    import requests
    import json
    import logging
    from bs4 import BeautifulSoup
    links = soup.find_all("a")
    docs_links = [link["href"] for link in links if "/docs/" in link["href"]]
    docs_links = list(set(docs_links))
    for i in range(len(docs_links)):
        if not docs_links[i].startswith("http"):
            docs_links[i] = urljoin(url, docs_links[i])
    docs_text = []
    for i, doc_link in enumerate(docs_links):

        try:
            page_link = requests.get(doc_link)
            soup = BeautifulSoup(page_link.text, "html.parser")
            title = soup.title.string.strip() if soup.title else "No title available"
            text = ""
            for element in soup.find_all("main", {"class": "layout__main"}):
                for child in element.descendants:
                    if child.name == "a" and child.has_attr("href"):
                        if include_url_in_text:
                            url = child.get("href")
                            if url is not None and "edit" in url:
                                text += child.text
                        else:
                            text += f"{child.text} (Reference url: {doc_link}{url}) "
                    elif child.string and child.string.strip():
                        text += child.string.strip() + " "
            docs_text.append({'id': i+1, 'doc_link': doc_link, 'title': title, 'text': text})
        except Exception as e:
            logging.error(f"Could not extract text from {doc_link}: {e}")
            continue
    return f"{docs_text}", {}
    



DEFAULT_WEBSITE_EXTRACTOR: Dict[
    str, Callable[[Any, str], Tuple[str, Dict[str, Any]]]
] = {
    "substack.com": _substack_reader,
    "readthedocs.io": _readthedocs_reader,
    "readme.com": _readmedocs_reader,
}


class BeautifulSoupWebReader(BaseReader):
    """BeautifulSoup web page reader.

    Reads pages from the web.
    Requires the `bs4` and `urllib` packages.

    Args:
        website_extractor (Optional[Dict[str, Callable]]): A mapping of website
            hostname (e.g. google.com) to a function that specifies how to
            extract text from the BeautifulSoup obj. See DEFAULT_WEBSITE_EXTRACTOR.
    """

    def __init__(
        self,
        website_extractor: Optional[Dict[str, Callable]] = None,

    ) -> None:
        """Initialize with parameters."""
        self.website_extractor = website_extractor or DEFAULT_WEBSITE_EXTRACTOR
 

    def load_data(
        self, urls: List[str], custom_hostname: Optional[str] = None,include_url_in_text: Optional[bool] = True
    ) -> List[Document]:
        """Load data from the urls.

        Args:
            urls (List[str]): List of URLs to scrape.
            custom_hostname (Optional[str]): Force a certain hostname in the case
                a website is displayed under custom URLs (e.g. Substack blogs)

        Returns:
            List[Document]: List of documents.

        """
        from urllib.parse import urlparse

        import requests
        from bs4 import BeautifulSoup

        documents = []
        for url in urls:
            try:
                page = requests.get(url)
            except Exception:
                raise ValueError(f"One of the inputs is not a valid url: {url}")

            hostname = custom_hostname or urlparse(url).hostname or ""

            soup = BeautifulSoup(page.content, "html.parser")

            data = ""
            extra_info = {"URL": url}
            if hostname in self.website_extractor:
                data, metadata = self.website_extractor[hostname](soup, url,include_url_in_text)
                print(metadata)
                extra_info.update(metadata)

            else:
                data = soup.getText()

            documents.append(Document(data, extra_info=extra_info))

        return documents
