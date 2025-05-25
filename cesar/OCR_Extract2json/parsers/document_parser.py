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
    tol_x = field_conf.get('tolerance_x', 5)  # met des tolérances par défaut si non définies dans les règles
    tol_y = field_conf.get('tolerance_y', 10)

    print(f"\n🔍 Extraction du champ : {field_name}")

    def match_and_collect(w):
        if min_x is not None and w['x'] < min_x:
            return False
        if max_x is not None and w['x'] > max_x:
            return False
        if min_y is not None and w['y'] < min_y:
            return False
        if max_y is not None and w['y'] > max_y:
            return False
        return re.search(regex, w['text'])

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

        if direction == 'right_xy': # meme x aligné horizontalement, donc cherche à droite du x avec une tolérance en y
            matched_words = []
            for w in words:
                if w['page'] == anchor_page and w['x'] > anchor_x + tol_x and abs(w['y'] - anchor_y) < tol_y:
                    print(f"✅ Candidat potentiel : {w['text']} ({w['x']}, {w['y']})")
                    if match_and_collect(w):
                        print(f"✔️ Match final : {w['text']}")
                        matched_words.append(w['text'])
            if matched_words:
                value = " ".join(matched_words)
                print(f"➡️ Valeur extraite : {value}")
                return value

        elif direction == 'line_right':  # à droite sur la même ligne ocr, attention ne pas utiliser si l'ocr a mal capté les lignes
            anchor_line = anchor_word['line_num']
            right_words = [
                w for w in words
                if w['page'] == anchor_page and
                   w['line_num'] == anchor_line and
                   w['x'] > anchor_x and
                   match_and_collect(w)
            ]
            texts = [w['text'] for w in right_words]
            if texts:
                value = " ".join(texts)
                print(f"➡️ Valeur extraite : {value}")
                return value

        elif direction == 'nearby_xy': # proche en valeur absolue en x et y suivant les tolérances définies
            matched_words = [
                w['text'] for w in words
                if w['page'] == anchor_page and
                   abs(w['x'] - anchor_x) <= tol_x and
                   abs(w['y'] - anchor_y) <= tol_y and
                   match_and_collect(w)
            ]
            if matched_words:
                value = " ".join(matched_words)
                print(f"➡️ Valeur extraite : {value}")
                return value

        # fallback
        search_range = words[words.index(anchor_word):words.index(anchor_word) + 50]
        if concat:
            texts = []
            for w in search_range:
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

def extract_transactions(words, transaction_conf, normalisation):
    tolerance_y = transaction_conf.get('group_by_y_tolerance', 3)
    columns = transaction_conf['columns']
    start_line_regex = re.compile(transaction_conf['start_line_regex'])

    # Grouper les mots par ligne (approximation sur y)
    lines = []
    current_line = []
    sorted_words = sorted(words, key=lambda w: (w['page'], w['y'], w['x']))
    last_y = None

    for word in sorted_words:
        y = word['y']
        if last_y is None or abs(y - last_y) <= tolerance_y:
            current_line.append(word)
        else:
            lines.append(current_line)
            current_line = [word]
        last_y = y
    if current_line:
        lines.append(current_line)

    # Traitement des lignes
    transactions = []
    current_transaction = None
    for line in lines:
        line_text = " ".join([w['text'] for w in line])
        if start_line_regex.search(line_text):
            # Nouvelle transaction
            current_transaction = {col: "" for col in columns}
            transactions.append(current_transaction)

        if current_transaction is not None:
            for word in line:
                for col_name, col_conf in columns.items():
                    if col_conf['x_min'] <= word['x'] <= col_conf['x_max']:
                        if 'regex' in col_conf and not re.search(col_conf['regex'], word['text']):
                            continue
                        current_transaction[col_name] += " " + word['text']
                        break

    # Nettoyage des champs
    for tx in transactions:
        for k, v in tx.items():
            tx[k] = v.strip()

    return transactions




def parse_document(ocr_json, yaml_config):
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
        output['transactions'] = extract_transactions(all_words, transactions_conf, normalisation)
    else:
        output['transactions'] = []

    return output

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parser structuré de relevé bancaire OCR selon un YAML")
    parser.add_argument('--ocr-json', required=True, help='Fichier OCR JSON')
    parser.add_argument('--yaml-config', required=True, help='Fichier YAML de configuration')
    parser.add_argument('--output', required=True, help='Fichier de sortie JSON structuré')

    args = parser.parse_args()

    ocr_data = load_ocr_json(args.ocr_json)
    config = load_yaml(args.yaml_config)

    result = parse_document(ocr_data, config)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✅ Parsing terminé → {args.output}")