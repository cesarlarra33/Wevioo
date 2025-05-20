import sys
import re
from typing import List, Tuple
from collections import defaultdict
import pandas as pd
from pathlib import Path


def parse_doctags_file(path: str) -> Tuple[List[Tuple[str, int, int]], str]:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Extraire tous les <text> avec position
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


def lines_to_key_value_df(lines: List[List[str]]) -> pd.DataFrame:
    key_values = []
    for line in lines:
        if len(line) >= 2:
            key_values.append([line[0], " ".join(line[1:])])
        elif len(line) == 1:
            key_values.append([line[0], ""])
    return pd.DataFrame(key_values, columns=["Clé", "Valeur"])


def parse_otsl_table(content: str) -> pd.DataFrame:
    otsl_match = re.search(r"<otsl>(.*?)</otsl>", content, re.DOTALL)
    if not otsl_match:
        return pd.DataFrame()

    table_content = otsl_match.group(1)

    # Extraire les headers
    headers = re.findall(r"<ched>(.*?)", table_content)
    headers = [h.strip() for h in headers if h.strip()]

    # Extraire les lignes
    rows = re.findall(r"<nl>(.*?)(?=<nl>|</otsl>)", table_content, re.DOTALL)
    table_data = []
    for row in rows:
        cells = re.findall(r"<fcel>(.*?)(?=<fcel>|<ecel>|$)", row, re.DOTALL)
        cleaned = [c.strip() for c in cells if c.strip()]
        if cleaned:
            table_data.append(cleaned)

    if not table_data:
        return pd.DataFrame()

    max_len = max(len(row) for row in table_data)
    padded = [row + [""] * (max_len - len(row)) for row in table_data]

    # Utilise les headers s’ils sont présents et correspondent au nombre de colonnes
    if headers and len(headers) == max_len:
        return pd.DataFrame(padded, columns=headers)
    else:
        return pd.DataFrame(padded)


def extract_section_headers(content: str) -> List[str]:
    return re.findall(r"<section_header_level_1>.*?<loc_\d+><loc_\d+><loc_\d+><loc_\d+>(.*?)</section_header_level_1>", content)


def extract_page_footers(content: str) -> List[str]:
    return re.findall(r"<page_footer><loc_\d+><loc_\d+><loc_\d+><loc_\d+>(.*?)</page_footer>", content)


def extract_picture_blocks(content: str) -> List[str]:
    return re.findall(r"<picture><loc_\d+><loc_\d+><loc_\d+><loc_\d+><(.*?)></picture>", content)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("=== Usage : python3 doctags_parser.py fichier.txt")
        sys.exit(1)

    txt_file = Path(sys.argv[1])
    if not txt_file.exists():
        print(f"=== Fichier introuvable : {txt_file}")
        sys.exit(1)

    output_csv = Path("csv") / (txt_file.stem + ".csv")
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    print(f"=== Lecture de : {txt_file}")
    elements, content = parse_doctags_file(str(txt_file))
    grouped_lines = group_lines(elements)
    df_header = lines_to_key_value_df(grouped_lines)

    df_otsl = parse_otsl_table(content)
    sections = extract_section_headers(content)
    footers = extract_page_footers(content)
    logos = extract_picture_blocks(content)

    # Construire DataFrames supplémentaires
    df_sections = pd.DataFrame(sections, columns=["Titre de Section"])
    df_footers = pd.DataFrame(footers, columns=["Pied de page"])
    df_logos = pd.DataFrame(logos, columns=["Bloc d’image identifié"])

    # Sauvegarde complète
    with open(output_csv, "w", encoding="utf-8", newline="") as f:
        f.write("=== En-tête :\n")
        df_header.to_csv(f, index=False)
        f.write("\n=== Titres de section :\n")
        df_sections.to_csv(f, index=False)
        f.write("\n=== Logos détectés :\n")
        df_logos.to_csv(f, index=False)
        f.write("\n=== Pieds de page :\n")
        df_footers.to_csv(f, index=False)
        f.write("\n=== Transactions (otsl) :\n")
        df_otsl.to_csv(f, index=False)

    print(f"\n=== Export terminé dans : {output_csv}")
