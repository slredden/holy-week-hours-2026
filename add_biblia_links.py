"""
One-off script to add Biblia.com NIV hyperlinks to scripture references
in the Holy Week prayer guide HTML file.
"""

import re

INPUT = "Holy Week Hours_ Daily Prayer Schedule & Readings _ Claude_files/saved_resource.html"

BOOK_MAP = {
    "1 Corinthians": "1Cor",
    "1 Peter": "1Pet",
    "Lamentations": "Lam",
    "Hebrews": "Heb",
    "Exodus": "Exod",
    "Matthew": "Matt",
    "Isaiah": "Isa",
    "Psalm": "Ps",
    "Psalms": "Ps",
    "John": "John",
    "Job": "Job",
}

BASE = "https://biblia.com/bible/niv"


def strip_letter_suffix(v):
    """Remove trailing letter from verse number, e.g. '9a' -> '9', '31b' -> '31'."""
    return re.sub(r'[a-z]$', '', v.strip())


def parse_verse_range(verse_str):
    """
    Parse a verse range string like '1–11', '1–2, 12–19', '(5–10)', '13–53:12'
    into a (start, end) tuple of strings suitable for URL use.
    Cross-chapter end like '53:12' is returned as-is (caller handles).
    """
    # Remove parentheses
    s = re.sub(r'[()]', '', verse_str)
    # Split on comma to handle non-contiguous ranges; take first and last numbers
    parts = [p.strip() for p in s.split(',') if p.strip()]
    if not parts:
        return None, None

    # First part gives start verse; last part gives end verse
    first_part = parts[0]
    last_part = parts[-1]

    # Extract start from first part (before –)
    first_split = re.split(r'–', first_part)
    start = strip_letter_suffix(first_split[0])

    # Extract end from last part (after – if present, else same as start of last)
    last_split = re.split(r'–', last_part)
    if len(last_split) > 1:
        end = strip_letter_suffix(last_split[-1])
    else:
        end = strip_letter_suffix(last_split[0])

    return start, end


def ref_to_url(book_abbr, chapter, verse_str):
    """Build a Biblia.com URL from components."""
    if not verse_str:
        return f"{BASE}/{book_abbr}.{chapter}"

    # Check for cross-chapter end like '53:12'
    cross_match = re.search(r'(\d+):(\d+[a-z]?)$', verse_str)
    if cross_match:
        # e.g. '52:13–53:12' or just '53:12' as end
        # Get start verse from the first part
        start_match = re.match(r'(\d+[a-z]?)', verse_str)
        start = strip_letter_suffix(start_match.group(1)) if start_match else ''
        end_chapter = cross_match.group(1)
        end_verse = strip_letter_suffix(cross_match.group(2))
        if start:
            return f"{BASE}/{book_abbr}.{chapter}.{start}-{end_chapter}.{end_verse}"
        else:
            return f"{BASE}/{book_abbr}.{chapter}.{end_chapter}.{end_verse}"

    start, end = parse_verse_range(verse_str)
    if not start:
        return f"{BASE}/{book_abbr}.{chapter}"
    if start == end:
        return f"{BASE}/{book_abbr}.{chapter}.{start}"
    return f"{BASE}/{book_abbr}.{chapter}.{start}-{end}"


def parse_single_ref(ref_text):
    """
    Parse a single scripture reference like 'John 12:1–11' or 'Psalm 70'
    into a Biblia.com URL. Returns None if unparseable.
    """
    ref_text = ref_text.strip()

    # Match book name (may start with digit), chapter, optional verse range
    m = re.match(
        r'^((?:\d\s+)?[A-Za-z]+(?:\s+[A-Za-z]+)*)\s+(\d+)(?::(.+))?$',
        ref_text
    )
    if not m:
        return None, ref_text

    book_name = m.group(1).strip()
    chapter = m.group(2)
    verse_str = m.group(3)  # may be None

    book_abbr = BOOK_MAP.get(book_name)
    if not book_abbr:
        return None, ref_text

    url = ref_to_url(book_abbr, chapter, verse_str)
    return url, ref_text


def make_link(url, text):
    return f'<a href="{url}" target="_blank" rel="noopener">{text}</a>'


def process_ref_content(inner_html):
    """
    Given the inner HTML of a reading-ref span, add Biblia.com hyperlinks
    to the scripture reference(s). Any <em> notes are left outside the link.

    Returns the new inner HTML.
    """
    # Separate the scripture reference text from any trailing <em>...</em>
    # Pattern: text node(s) optionally followed by one or more <em>...</em>
    em_pattern = re.compile(r'(<em>.*?</em>)', re.DOTALL)
    em_parts = em_pattern.split(inner_html)

    # em_parts alternates: [text, <em>...</em>, text, <em>...</em>, ...]
    # The first element is the raw reference text (possibly with " or " separating refs)
    ref_text_raw = em_parts[0].strip()
    em_suffix = ''.join(em_parts[1:])  # keep <em> parts verbatim

    # Handle multi-reference with ' or ' (e.g. "Lamentations 3:1–9, 19–24 or Job 14:1–14")
    if ' or ' in ref_text_raw:
        sub_refs = [r.strip() for r in ref_text_raw.split(' or ')]
        linked = []
        for sr in sub_refs:
            url, text = parse_single_ref(sr)
            if url:
                linked.append(make_link(url, text))
            else:
                linked.append(text)
        new_ref = ' or '.join(linked)
        return new_ref + (' ' + em_suffix.strip() if em_suffix.strip() else '')

    # Handle multi-reference with '; ' (e.g. "Hebrews 4:14–16; 5:7–9")
    if '; ' in ref_text_raw:
        # The second part may be just chapter:verse without a book name
        sub_refs = [r.strip() for r in ref_text_raw.split('; ')]
        # Carry forward the book from the first ref if subsequent refs lack one
        first_url, first_text = parse_single_ref(sub_refs[0])
        # Extract book from first ref for context
        book_m = re.match(r'^((?:\d\s+)?[A-Za-z]+(?:\s+[A-Za-z]+)*)\s+\d+', sub_refs[0])
        book_name = book_m.group(1) if book_m else ''

        linked = []
        if first_url:
            linked.append(make_link(first_url, first_text))
        else:
            linked.append(first_text)

        for sr in sub_refs[1:]:
            # If sr doesn't start with a book name, prepend the carried book
            if re.match(r'^\d+:', sr):
                sr_full = f"{book_name} {sr}"
            else:
                sr_full = sr
            url, text = parse_single_ref(sr_full)
            if url:
                linked.append(make_link(url, text))
            else:
                linked.append(sr)

        new_ref = '; '.join(linked)
        return new_ref + (' ' + em_suffix.strip() if em_suffix.strip() else '')

    # Single reference
    url, text = parse_single_ref(ref_text_raw)
    if url:
        linked = make_link(url, text)
    else:
        linked = ref_text_raw

    if em_suffix.strip():
        return linked + ' ' + em_suffix.strip()
    return linked


def process_html(html):
    """Find all reading-ref spans and add links to their content."""
    pattern = re.compile(
        r'(<span class="reading-ref">)(.*?)(</span>)',
        re.DOTALL
    )

    def replace_span(m):
        open_tag = m.group(1)
        inner = m.group(2)
        close_tag = m.group(3)
        new_inner = process_ref_content(inner)
        return open_tag + new_inner + close_tag

    return pattern.sub(replace_span, html)


def main():
    with open(INPUT, 'r', encoding='utf-8') as f:
        html = f.read()

    new_html = process_html(html)

    with open(INPUT, 'w', encoding='utf-8') as f:
        f.write(new_html)

    # Report what changed
    original_spans = re.findall(r'<span class="reading-ref">.*?</span>', html, re.DOTALL)
    new_spans = re.findall(r'<span class="reading-ref">.*?</span>', new_html, re.DOTALL)
    linked = sum(1 for s in new_spans if '<a href=' in s)
    print(f"Processed {len(new_spans)} reading-ref spans, added links to {linked}.")
    unlinked = [s for s in new_spans if '<a href=' not in s]
    if unlinked:
        print("WARNING - spans without links:")
        for s in unlinked:
            print(" ", s)


if __name__ == '__main__':
    main()
