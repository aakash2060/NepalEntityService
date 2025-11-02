"""Wikipedia Nepali politicians scraper."""

import wikipedia
from bs4 import BeautifulSoup

from nes.models import Person

skip_tags = {"sup", "cite"}


def is_bad_anchor(element):
    """Check if the given element is a reference anchor."""
    for elem in (
        element,
        element.parent,
        element.parent.parent,
        element.parent.parent.parent,
    ):
        if elem.name in skip_tags:
            return True
        if "reference-text" in elem.get("class", []):
            return True

    if any(
        x.name in skip_tags for x in (element, element.parent, element.parent.parent)
    ):
        return True

    if element["href"].startswith("#"):
        return True
    if "action=edit" in element["href"]:
        return True

    return False


def clean_content(content):
    """Convert wiki notation headers to markdown."""
    import re

    # Convert wiki headers (== Header ==) to markdown (## Header)
    content = re.sub(r"={6}\s*(.+?)\s*={6}", r"###### \1", content)
    content = re.sub(r"={5}\s*(.+?)\s*={5}", r"##### \1", content)
    content = re.sub(r"={4}\s*(.+?)\s*={4}", r"#### \1", content)
    content = re.sub(r"={3}\s*(.+?)\s*={3}", r"### \1", content)
    content = re.sub(r"={2}\s*(.+?)\s*={2}", r"## \1", content)

    return content


def traverse_politician_page(name, href):
    """Traverse a politician page by processing the href and making a Wikipedia lookup."""
    # Remove /wiki/ prefix and replace _ with spaces
    page_title = href.replace("/wiki/", "").replace("_", " ")

    try:
        page = wikipedia.page(page_title)
        return Person(
            id=page.pageid,
            names={"en": page.title},
            attributes={"url": page.url},
            summary=page.summary,
            description=clean_content(page.content),
        )
    except wikipedia.exceptions.DisambiguationError as e:
        # Try the first option if disambiguation
        page = wikipedia.page(e.options[0])
        return Person(
            id=page.pageid,
            names={"en": page.title},
            attributes={"url": page.url},
            summary=page.summary,
            description=clean_content(page.content),
        )
    except wikipedia.exceptions.PageError as e:
        return None


def get_nepali_politician_page_links():
    """Get all politician links from Wikipedia page after section A until References."""
    page = wikipedia.page("List of Nepalese politicians")
    html = page.html()
    soup = BeautifulSoup(html, "html.parser")

    # Find element with id="A"
    a_element = soup.find(id="A")
    if not a_element:
        return []

    # Find References element to stop at
    references_element = soup.find(id="References")

    # Get all <a> tags after the element with id="A" until References
    links = []
    for element in a_element.find_all_next("a", href=True):
        # Stop if we reach the References section
        if (
            references_element
            and element.find_parent()
            and references_element in element.find_parents()
        ):
            break

        if is_bad_anchor(element):
            continue

        links.append({"name": element["title"], "href": element["href"]})

    return links


if __name__ == "__main__":
    links = get_nepali_politician_page_links()
    print(f"Found {len(links)} politician links")

    for link in links[:5]:  # Process first 5 links
        person = traverse_politician_page(link["name"], link["href"])
        if person:
            print(f"Successfully loaded: {person.names['en']}")
        else:
            print(f"Failed to load: {link['name']}")
