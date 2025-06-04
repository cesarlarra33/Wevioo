import sys
import re
import json
from typing import List, Tuple
from collections import defaultdict
from pathlib import Path
import datetime


def parse_doctags_file(path: str) -> Tuple[List[Tuple[str, int, int]], str]:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(r"<text><loc_(\d+)><loc_(\d+)><loc_(\d+)><loc_(\d+)>(.*?)</text>")
    elements = []
    for match in pattern.finditer(content):
        x1 = int(match.group(1))
        y1 = int(match.group(2))
        text = match.group(5).strip()
        if text:
            elements.append((text, y1, x1))

    return elements, content


def group_lines(elements: List[Tuple[str, int, int]], y_tolerance: int = 5):
    lines = defaultdict(list)
    for text, y, x in elements:
        found = False
        for key in lines:
            if abs(key - y) <= y_tolerance:
                lines[key].append((x, text))
                found = True
                break
        if not found:
            lines[y].append((x, text))

    sorted_lines = []
    for y in sorted(lines):
        line = sorted(lines[y], key=lambda t: t[0])
        sorted_lines.append([text for _, text in line])
    return sorted_lines


def extract_key_value_pairs(lines: List[List[str]]) -> List[dict]:
    key_values = []
    for line in lines:
        if len(line) >= 2:
            key_values.append({"key": line[0], "value": " ".join(line[1:])})
        elif len(line) == 1:
            key_values.append({"key": line[0], "value": ""})
    return key_values


def parse_otsl_table(content: str) -> List[dict]:
    otsl_match = re.search(r"<otsl>(.*?)</otsl>", content, re.DOTALL)
    if not otsl_match:
        return []

    table_content = otsl_match.group(1)
    headers = re.findall(r"<ched>(.*?)", table_content)
    headers = [h.strip() for h in headers if h.strip()]

    rows = re.findall(r"<nl>(.*?)(?=<nl>|</otsl>)", table_content, re.DOTALL)
    table_data = []

    for row in rows:
        cells = re.findall(r"<fcel>(.*?)(?=<fcel>|<ecel>|$)", row, re.DOTALL)
        cleaned = [c.strip() for c in cells if c.strip()]
        if cleaned:
            table_data.append(cleaned)

    if not table_data:
        return []

    max_len = max(len(row) for row in table_data)
    padded = [row + [""] * (max_len - len(row)) for row in table_data]

    result = []
    for row in padded:
        if headers and len(headers) == len(row):
            result.append(dict(zip(headers, row)))
        else:
            result.append({f"col{i+1}": cell for i, cell in enumerate(row)})

    return result


def is_date(s: str) -> bool:
    s = s.strip()
    for fmt in ("%d/%m/%y", "%d/%m/%Y"):
        try:
            datetime.datetime.strptime(s, fmt)
            return True
        except ValueError:
            continue
    return False


def fallback_parse_transactions_from_texts(text_blocks: List[Tuple[str, int, int]]) -> List[dict]:
    transactions = []
    current = []

    sorted_texts = sorted(text_blocks, key=lambda t: (t[1], t[2]))
    for text, y, x in sorted_texts:
        if is_date(text):
            if current:
                transactions.append(current)
                current = []
        current.append(text)

    if current:
        transactions.append(current)

    # Convert to structured dicts
    result = []
    for tx in transactions:
        result.append({f"col{i+1}": cell for i, cell in enumerate(tx)})

    return result


def extract_section_headers(content: str) -> List[str]:
    return re.findall(r"<section_header_level_1>.*?<loc_\d+><loc_\d+><loc_\d+><loc_\d+>(.*?)</section_header_level_1>", content)


def extract_page_footers(content: str) -> List[str]:
    return re.findall(r"<page_footer><loc_\d+><loc_\d+><loc_\d+><loc_\d+>(.*?)</page_footer>", content)


def extract_picture_blocks(content: str) -> List[str]:
    return re.findall(r"<picture><loc_\d+><loc_\d+><loc_\d+><loc_\d+><(.*?)></picture>", content)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("=== Usage : python3 doctags_to_json.py fichier.txt")
        sys.exit(1)

    txt_file = Path(sys.argv[1])
    if not txt_file.exists():
        print(f"=== Fichier introuvable : {txt_file}")
        sys.exit(1)

    output_json = Path("json") / (txt_file.stem + ".json")
    output_json.parent.mkdir(parents=True, exist_ok=True)

    print(f"=== Lecture de : {txt_file}")
    elements, content = parse_doctags_file(str(txt_file))
    grouped_lines = group_lines(elements)
    key_value_data = extract_key_value_pairs(grouped_lines)
    transactions = parse_otsl_table(content)

    if not transactions:
        print("=== Aucune balise <otsl> trouvée, tentative de récupération des transactions par fallback...")
        transactions = fallback_parse_transactions_from_texts(elements)

    sections = extract_section_headers(content)
    footers = extract_page_footers(content)
    logos = extract_picture_blocks(content)

    structured = {
        "metadata": key_value_data,
        "sections": sections,
        "footers": footers,
        "logos": logos,
        "transactions": transactions,
    }

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(structured, f, indent=2, ensure_ascii=False)

    print(f"=== Export JSON terminé : {output_json}")
