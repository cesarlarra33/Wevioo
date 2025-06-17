import os
import json
import argparse
import yaml
import re
from datetime import datetime

def load_yaml(yaml_path):
    with open(yaml_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def load_ocr_json(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def normalize_value(field_name, value, normalisation):
    rules = normalisation.get(field_name, {})

    if rules.get('supprimer_espaces'):
        value = value.replace(' ', '')

    if rules.get('convertir_en_float'):
        value = value.replace(',', '.')
        try:
            return float(value)
        except ValueError:
            return None

    return value

def normalize_date(date_str, normalisation):
    try:
        format_src = normalisation['date']['format_source']
        format_dst = normalisation['date']['format_cible']
        dt = datetime.strptime(date_str, format_src)
        return dt.strftime(format_dst)
    except:
        return date_str

def extract_field(words, field_name, field_conf, normalisation):
    anchor_sequence = field_conf.get('anchor_sequence')
    anchor_text = field_conf.get('anchor')
    direction = field_conf.get('direction', 'right')
    regex = field_conf.get('regex', '.+')
    offset = field_conf.get('offset', 0)
    concat = field_conf.get('concat', False)
    concat_until = field_conf.get('concat_until')
    max_x = field_conf.get('max_x')
    min_x = field_conf.get('min_x')
    min_y = field_conf.get('min_y')
    max_y = field_conf.get('max_y')
    tol_x = field_conf.get('tolerance_x', 5)
    tol_y = field_conf.get('tolerance_y', 50)
    page_constraint = field_conf.get('page')  # Nouveau

    if page_constraint is not None:
        words = [w for w in words if w['page'] == page_constraint]

    print(f"\n🔍 Extraction du champ : {field_name}")
    
    if not anchor_text and not anchor_sequence:
        print(f"🔎 Pas d’ancre définie → recherche directe dans la zone min_x:{min_x}, max_x:{max_x}, min_y:{min_y}, max_y:{max_y}")
        
        # Tous les mots dans la zone, sans filtrer par regex
        all_candidates_in_zone = [
            w for w in words
            if (min_x is None or w['x'] >= min_x) and (max_x is None or w['x'] <= max_x)
            and (min_y is None or w['y'] >= min_y) and (max_y is None or w['y'] <= max_y)
        ]
        print(f"🟡 Tous les mots candidats dans la zone : {[w['text'] for w in all_candidates_in_zone]}")
        
        # Maintenant on applique la regex
        regex_matched_candidates = [w for w in all_candidates_in_zone if re.search(regex, w['text'])]
        print(f"🟢 Mots qui matchent la regex : {[w['text'] for w in regex_matched_candidates]}")
        
        if regex_matched_candidates:
            value = " ".join(w['text'] for w in regex_matched_candidates)
            print(f"✅ Valeur extraite (sans ancre) : {value}")
            return normalize_value(field_name, value, normalisation)
        else:
            print("❌ Aucune valeur trouvée dans la zone après filtrage regex")
        return None

    def match_and_collect(w):
        if min_x is not None and w['x'] < min_x:
            print(f"❌ {w['text']} rejeté (x trop petit : {w['x']} < {min_x})")
            return False
        if max_x is not None and w['x'] > max_x:
            print(f"❌ {w['text']} rejeté (x trop grand : {w['x']} > {max_x})")
            return False
        if min_y is not None and w['y'] < min_y:
            print(f"❌ {w['text']} rejeté (y trop petit : {w['y']} < {min_y})")
            return False
        if max_y is not None and w['y'] > max_y:
            print(f"❌ {w['text']} rejeté (y trop grand : {w['y']} > {max_y})")
            return False

        if re.search(regex, w['text']):
            return True
        else:
            print(f"❌ {w['text']} rejeté (ne matche pas la regex : {regex})")
            return False
    
    def find_anchor_word():
        if anchor_sequence:
            print(f"🔗 Recherche de l'ancre multiple : {anchor_sequence}")
            for i in range(len(words) - len(anchor_sequence) + 1):
                if all(anchor_sequence[j].lower() in words[i + j]['text'].lower()
                       for j in range(len(anchor_sequence))):
                    print(f"✅ Ancre multiple trouvée : {[words[i + j]['text'] for j in range(len(anchor_sequence))]}")
                    return words[i + offset]
            print("❌ Aucune ancre multiple trouvée")
            return None

        if anchor_text:
            print(f"🔗 Recherche de l'ancre simple : {anchor_text}")
            for i, word in enumerate(words):
                if anchor_text.lower() in word['text'].lower():
                    if min_y is not None and word['y'] < min_y:
                        continue
                    if max_y is not None and word['y'] > max_y:
                        continue
                    print(f"✅ Ancre simple trouvée : {word['text']} à (x={word['x']}, y={word['y']})")
                    return words[i + offset] if i + offset < len(words) else word
            print("❌ Aucune ancre simple trouvée")
        return None

    def extract_by_direction(anchor_word):
        anchor_x = anchor_word['x']
        anchor_y = anchor_word['y']
        anchor_page = anchor_word['page']

        if direction == 'right_xy':
            print("📐 Recherche en direction: right_xy")
            candidates = [
                w for w in words
                if w['page'] == anchor_page and
                   w['x'] > anchor_x + tol_x and
                   abs(w['y'] - anchor_y) < tol_y
            ]
            print(f"🔎 {len(candidates)} mots candidats trouvés (avant regex): {[w['text'] for w in candidates]}")

            matched_words = []
            for w in candidates:
                if match_and_collect(w):
                    print(f"✔️ Match accepté : {w['text']} (x={w['x']}, y={w['y']})")
                    matched_words.append(w['text'])

            if matched_words:
                value = " ".join(matched_words)
                print(f"➡️ Valeur extraite : {value}")
                return value

        elif direction == 'line_right':
            print("📐 Recherche en direction: line_right")
            anchor_line = anchor_word['line_num']
            candidates = [
                w for w in words
                if w['page'] == anchor_page and
                   w['line_num'] == anchor_line and
                   w['x'] > anchor_x
            ]
            print(f"🔎 {len(candidates)} mots candidats trouvés (avant regex): {[w['text'] for w in candidates]}")

            matched_words = [w['text'] for w in candidates if match_and_collect(w)]

            if matched_words:
                value = " ".join(matched_words)
                print(f"➡️ Valeur extraite : {value}")
                return value

        elif direction == 'nearby_xy':
            print("📐 Recherche en direction: nearby_xy")
            candidates = [
                w for w in words
                if w['page'] == anchor_page and
                   abs(w['x'] - anchor_x) <= tol_x and
                   abs(w['y'] - anchor_y) <= tol_y
            ]
            print(f"🔎 {len(candidates)} mots candidats trouvés (avant regex): {[w['text'] for w in candidates]}")

            matched_words = [w['text'] for w in candidates if match_and_collect(w)]

            if matched_words:
                value = " ".join(matched_words)
                print(f"➡️ Valeur extraite : {value}")
                return value
        
        elif direction == 'below':
            print("📐 Recherche en direction: below")
            candidates = [
                w for w in words
                if w['page'] == anchor_page and
                w['y'] > anchor_y and
                w['y'] <= anchor_y + tol_y and
                (min_x is None or w['x'] >= min_x) and
                (max_x is None or w['x'] <= max_x)
            ]
            print(f"🔎 {len(candidates)} mots candidats trouvés (en dessous): {[w['text'] for w in candidates]}")
            
                # 🔍 Log des mots proches en x mais rejetés par y
            debug_rejected_y = [
                w for w in words
                if w['page'] == anchor_page and
                abs(w['x'] - anchor_x) <= tol_x and
                not (w['y'] > anchor_y and w['y'] <= anchor_y + tol_y)
            ]
            for w in debug_rejected_y:
                print(f"❌ {w['text']} rejeté (y={w['y']}, anchor_y={anchor_y}, tol_y={tol_y})")


            matched_words = [w['text'] for w in candidates if match_and_collect(w)]

            if matched_words:
                value = " ".join(matched_words)
                print(f"➡️ Valeur extraite : {value}")
                return value


        # Fallback
        print("🔁 Méthode fallback utilisée (séquence brute)")
        search_range = words[words.index(anchor_word):words.index(anchor_word) + 50]
        print(f"🔎 Mots testés dans le fallback : {[w['text'] for w in search_range]}")

        if concat:
            texts = []
            for w in search_range:
                if w is anchor_word:
                    continue
                if concat_until and concat_until.lower() in w['text'].lower():
                    break
                if match_and_collect(w):
                    texts.append(w['text'])
            if texts:
                value = " ".join(texts)
                print(f"➡️ Valeur extraite (fallback concat) : {value}")
                return value
        else:
            for w in search_range:
                match = re.search(regex, w['text'])
                if match:
                    value = match.group(0)
                    print(f"➡️ Valeur extraite (fallback regex) : {value}")
                    return value

        return None

    anchor_word = find_anchor_word()
    if not anchor_word:
        print("⚠️ Aucun mot d'ancrage trouvé → champ ignoré")
        return None

    raw_value = extract_by_direction(anchor_word)
    if raw_value is not None:
        return normalize_value(field_name, raw_value, normalisation)

    print("❌ Aucune valeur extraite")
    return None

def extract_tokens_by_column_regex(line_text, columns_order, columns_regex, separator="!"):
    print("\n🔍 Ligne originale reçue :", repr(line_text))
    tokens = []
    remaining = line_text

    for idx, col_name in enumerate(columns_order):
        pattern = columns_regex.get(col_name)

        # 🔁 Si pas de regex définie pour cette colonne → on split le reste
        if not pattern:
            print(f"\n✂️ Aucune regex pour colonne '{col_name}' → split brut par '{separator}'")
            rest_parts = [p.strip() for p in remaining.strip().split(separator) if p.strip()]
            expected_rest = len(columns_order) - len(tokens)

            if len(rest_parts) < expected_rest:
                print(f"❌ Trop peu de champs restants après split brut ({len(rest_parts)} vs {expected_rest})")
                return None

            tokens.extend(rest_parts[:expected_rest])
            print(f"✅ Tokens finaux après split brut : {tokens}")
            return tokens

        print(f"\n🔎 Recherche pour colonne [{idx}] '{col_name}' avec regex: {pattern}")
        found = False

        for match in re.finditer(pattern, remaining):
            start, end = match.span()
            if match.lastgroup == "val":
                matched_text = match.group("val")
            if match.lastindex and match.lastindex >= 1:
                matched_text = match.group(1)
            else:
                matched_text = match.group()
            
            
            # ✅ Si le caractère juste avant le match est suspect (ex: '1', 'I', 'l'), on ignore ce caractère
            if start > 0 and remaining[start - 1] in "1Il!":
                print(f"⚠️ Correction OCR probable (caractère suspect avant match) → on garde : '{matched_text}' (index {start})")
                tokens.append(matched_text)
                remaining = remaining[end:].strip()
                found = True
                break

            # ✅ Match normal
            print(f"✅ Trouvé: '{matched_text}'")
            tokens.append(matched_text)
            remaining = remaining[end:].strip()
            found = True
            break

        if not found:
            print(f"❌ Aucune correspondance pour la colonne '{col_name}' → ligne rejetée")
            return {"status": "error", "reason": f"Échec sur colonne '{col_name}'", "line": line_text}


        print(f"✂️ Texte restant: {repr(remaining)}")

    print("\n✅ Tous les tokens extraits avec succès :", tokens)
    return {"status": "success", "tokens": tokens}

def extract_transactions_with_separator(words, transaction_conf, normalisation):
    print("\n📄 Début extraction des transactions (mode with_separator)")

    separator = transaction_conf.get("separator", "!")
    columns_order = transaction_conf.get("columns_order", [])
    columns_regex = transaction_conf.get("columns_regex", {})
    x_min = transaction_conf.get("start_line_x_min")
    x_max = transaction_conf.get("start_line_x_max")
    y_min = transaction_conf.get("start_line_y_min")
    y_max = transaction_conf.get("start_line_y_max")
    y_tolerance = transaction_conf.get("y_tolerance", 5)
    start_line_regex = re.compile(transaction_conf.get("start_line_regex"))

    sorted_words = sorted(words, key=lambda w: (w["page"], w["y"], w["x"]))
    transactions = []
    visited_lines = set()
    lignes_exclues = []
    for word in sorted_words:
        if x_min is not None and word["x"] < x_min:
            continue
        if x_max is not None and word["x"] > x_max:
            continue
        if y_min is not None and word["y"] < y_min:
            continue
        if y_max is not None and word["y"] > y_max:
            continue
        if not start_line_regex.search(word["text"]):
            continue

        page = word["page"]
        anchor_y = word["y"]
        line_key = (page, anchor_y)
        if line_key in visited_lines:
            continue
        visited_lines.add(line_key)

        y_band_min = anchor_y - y_tolerance
        y_band_max = anchor_y + y_tolerance
        line_words = [
            w for w in sorted_words
            if w["page"] == page and y_band_min <= w["y"] <= y_band_max
        ]

        line_words_sorted = sorted(line_words, key=lambda w: w["x"])
        line_text = " ".join(w["text"] for w in line_words_sorted)

        print(f"\n📞 Ligne détectée brute (p{page} y={anchor_y}) : {line_text}")

        # 👉 Appel à ta fonction existante
        result = extract_tokens_by_column_regex(line_text, columns_order, columns_regex, separator)
        if result["status"] != "success":
            print(f"⚠️ Ligne ignorée : {result['reason']}")
            lignes_exclues.append({
                "page": page,
                "y": anchor_y,
                "texte": line_text,
                "raison": result["reason"]
            })
            continue

        tokens = result["tokens"]
        if len(tokens) != len(columns_order):
            print(f"⚠️ Ligne ignorée : nombre de champs incorrect ({len(tokens)} vs {len(columns_order)})")
            lignes_exclues.append({
                "page": page,
                "y": anchor_y,
                "texte": line_text,
                "raison": "Nombre de champs incorrect"
            })
            continue

        transaction = {col_name: tokens[i] for i, col_name in enumerate(columns_order)}
        print(f"✅ Transaction extraite : {transaction}")
        transactions.append(transaction)

    print(f"\n✅ Total transactions extraites (with_separator): {len(transactions)}")
    print(f"❌ Total lignes exclues : {len(lignes_exclues)}")
    return {
        "transactions": transactions,
        "lignes_exclues": lignes_exclues
    }

def extract_transactions(words, transaction_conf, normalisation):
    print("\n📄 Début extraction des transactions")
    
    if transaction_conf.get("mode") == "with_separator":
        return extract_transactions_with_separator(words, transaction_conf, normalisation)

    columns = transaction_conf['columns']
    start_line_regex = re.compile(transaction_conf['start_line_regex'])
    start_line_x_max = transaction_conf.get('start_line_x_max', None)
    start_line_x_min = transaction_conf.get('start_line_x_min', None)
    start_line_y_min_raw = transaction_conf.get('start_line_y_min', None)  # <- changé
    start_line_y_max = transaction_conf.get('start_line_y_max', None)
    y_tol_above = transaction_conf.get('y_tolerance_above', 5)
    y_tol_below = transaction_conf.get('y_tolerance_below', 10)

    print(f"🔍 Regex de départ : {transaction_conf['start_line_regex']}")
    print(f"🔍 Nombre total de mots dans le document : {len(words)}")
    
    sorted_words = sorted(words, key=lambda w: (w['page'], w['y'], w['x']))
    transactions = []
    anchor_y = None
    current_transaction = None
    
    last_anchor_y = None
    last_anchor_page = None

    for i, word in enumerate(sorted_words):
        # Empêche de détecter deux transactions sur la même ligne OCR
        if last_anchor_y is not None and abs(word['y'] - last_anchor_y) < 5 and word['page'] == last_anchor_page:
            continue

        # Gestion de start_line_y_min par page
        page = word['page']
        if isinstance(start_line_y_min_raw, dict):
            start_line_y_min = start_line_y_min_raw.get(page, start_line_y_min_raw.get("default"))
        else:
            start_line_y_min = start_line_y_min_raw

        text = word['text']
        is_start_line_candidate = (
            start_line_regex.search(text) and
            (start_line_x_max is None or word['x'] <= start_line_x_max) and
            (start_line_x_min is None or word['x'] >= start_line_x_min) and
            (start_line_y_min is None or word['y'] >= start_line_y_min) and
            (start_line_y_max is None or word['y'] <= start_line_y_max)
        )

        if not is_start_line_candidate:
            continue

        # Nouvelle transaction détectée
        anchor_y = word['y']
        current_transaction = {col: "" for col in columns}
        transactions.append(current_transaction)
        print(f"\n🧾 Nouvelle transaction détectée : {text} (y = {anchor_y})")

        last_anchor_y = word['y']
        last_anchor_page = word['page']
        
        # Récupérer tous les mots autour de cette ancre dans la fenêtre verticale
        y_min = anchor_y - y_tol_above
        y_max = anchor_y + y_tol_below

        # On récupère les mots dans la bande verticale définie
        line_words = [
            w for w in sorted_words
            if w['page'] == page and y_min <= w['y'] <= y_max
        ]

        # Et on les trie de gauche à droite
        line_words = sorted(line_words, key=lambda w: w['x'])

        for w in line_words:
            for col_name, col_conf in columns.items():
                if (
                    col_conf['x_min'] <= w['x'] <= col_conf['x_max']
                    and ('y_min' not in col_conf or w['y'] >= col_conf['y_min'])
                    and ('y_max' not in col_conf or w['y'] <= col_conf['y_max'])
                ):
                    if 'regex' in col_conf and not re.search(col_conf['regex'], w['text']):
                        continue
                    current_transaction[col_name] += " " + w['text']
                    print(f"  ➕ {w['text']} → {col_name}")
                    break

    # Nettoyage des champs
    for tx in transactions:
        for k, v in tx.items():
            tx[k] = v.strip()

    print(f"\n✅ Total transactions extraites : {len(transactions)}")
    return {
        "transactions": transactions,
        "lignes_exclues": []
    }
    
def natural_sort_key(s):
    # Découpe en séquences de chiffres et de lettres pour tri naturel
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]


def find_matching_tables_sorted(ocr_dir, base_prefix, filter_all=None, filter_any=None):
    """
    Retourne la liste triée de tuples (filename, data) des tableaux OCR 
    contenant tous les mots de filter_all et/ou au moins un mot de filter_any.
    """
    matched = []

    for fname in os.listdir(ocr_dir):
        if not fname.endswith(".json"):
            continue
        if "_p" not in fname or "_tab" not in fname:
            continue
        if not fname.startswith(base_prefix):
            continue

        path = os.path.join(ocr_dir, fname)
        data = load_ocr_json(path)

        full_text = " ".join(
            w['text']
            for page in data
            for block in page.get('blocks', [])
            for line in block.get('lines', [])
            for w in line.get('words', [])
        ).lower()

        if filter_all and not all(word.lower() in full_text for word in filter_all):
            continue
        if filter_any and not any(word.lower() in full_text for word in filter_any):
            continue

        matched.append((fname, data))

    if not matched:
        print("⚠️ Aucun tableau OCR ne correspond aux filtres")
        return []

    # 🔤 Tri naturel (alphanumérique)
    matched_sorted = sorted(matched, key=lambda x: natural_sort_key(x[0]))

    print(f"✅ {len(matched_sorted)} tableau(x) retenu(s) après filtre et tri naturel.")
    for fname, _ in matched_sorted:
        print(f"  ➕ {fname}")

    return matched_sorted

def parse_document(ocr_json, yaml_config, ocr_json_path):
    output = {}

    all_words = []
    for page in ocr_json:
        for block in page.get('blocks', []):
            for line in block.get('lines', []):
                all_words.extend(line.get('words', []))

    structure = yaml_config.get('structure', {})
    normalisation = yaml_config.get('normalisation', {})

    champs_simples = structure.get('champs_simples', {})
    for field_name, field_conf in champs_simples.items():
        output[field_name] = extract_field(all_words, field_name, field_conf, normalisation)

    transactions_conf = structure.get('transactions')
    if transactions_conf:
        source = transactions_conf.get('source', 'document')
        if source == 'table':
            base_prefix = os.path.splitext(os.path.basename(ocr_json_path))[0]
            ocr_table_data = find_matching_tables_sorted(
                ocr_dir="data/ocr",
                base_prefix=base_prefix,
                filter_all=transactions_conf.get('filter_contains'),
                filter_any=transactions_conf.get('filter_contains_any')
            )

            all_transactions = []
            all_excluded = []
            fichiers_tables = []

            for fname, data in ocr_table_data:
                print(f"📄 Analyse du tableau : {fname}")
                table_words = []
                for page in data:
                    for block in page.get('blocks', []):
                        for line in block.get('lines', []):
                            table_words.extend(line.get('words', []))

                result = extract_transactions(table_words, transactions_conf, normalisation)
                all_transactions.extend(result.get("transactions", []))
                all_excluded.extend(result.get("lignes_exclues", []))
                fichiers_tables.append(fname)

            output['transactions'] = all_transactions
            output['lignes_exclues'] = all_excluded
            output['fichiers_tables'] = fichiers_tables

        else:
            result = extract_transactions(all_words, transactions_conf, normalisation)
            output['transactions'] = result.get("transactions", [])
            output['lignes_exclues'] = result.get("lignes_exclues", [])
    else:
        output['transactions'] = []

    print(f"Total transaction extraires : {len(output['transactions'])}, Total transaction exclues : {len(output['lignes_exclues'])}")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parser structuré de relevé bancaire OCR selon un YAML")
    parser.add_argument('--ocr-json', required=True, help='Fichier OCR JSON')
    parser.add_argument('--yaml-config', required=True, help='Fichier YAML de configuration')
    parser.add_argument('--output', required=True, help='Fichier de sortie JSON structuré')

    args = parser.parse_args()

    ocr_data = load_ocr_json(args.ocr_json)
    config = load_yaml(args.yaml_config)

    result = parse_document(ocr_data, config, args.ocr_json)


    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✅ Parsing terminé → {args.output}")