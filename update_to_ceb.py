"""
Replaces all Biblia.com NIV scripture links with Common English Bible (CEB) links.
CEB passage lookup format: https://www.commonenglishbible.com/explore/passage-lookup/?query={reference}
"""

import re
import urllib.parse

FILES = [
    "index.html",
    "Holy Week Hours_ Daily Prayer Schedule & Readings _ Claude_files/saved_resource.html",
]

BIBLIA_PATTERN = re.compile(
    r'href="https://biblia\.com/bible/niv/[^"]*"(.*?)>([^<]+)</a>',
    re.DOTALL,
)

CEB_BASE = "https://www.commonenglishbible.com/explore/passage-lookup/"


def link_text_to_ceb_url(text):
    ref = text
    ref = ref.replace("\u2013", "-")            # em-dash → hyphen
    ref = re.sub(r"(\d)[a-z]\b", r"\1", ref)   # strip letter suffixes (9a→9, 31b→31)
    ref = ref.replace("(", "").replace(")", "") # strip parentheses
    return f"{CEB_BASE}?query={urllib.parse.quote_plus(ref)}"


def process(html):
    def replace(m):
        attrs = m.group(1)   # e.g. ' target="_blank" rel="noopener"'
        text  = m.group(2)   # e.g. "Psalm 36:5–11"
        url   = link_text_to_ceb_url(text)
        return f'href="{url}"{attrs}>{text}</a>'

    return BIBLIA_PATTERN.sub(replace, html)


for path in FILES:
    with open(path, encoding="utf-8") as f:
        html = f.read()

    new_html = process(html)

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_html)

    ceb_count   = new_html.count("commonenglishbible.com")
    biblia_left = new_html.count("biblia.com")
    print(f"{path}")
    print(f"  CEB links:          {ceb_count}")
    print(f"  Remaining biblia:   {biblia_left}")
