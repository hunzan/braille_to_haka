import json
import os

def load_json(filename):
    base_path = os.path.join(os.path.dirname(__file__), 'braille_data')
    with open(os.path.join(base_path, filename), encoding='utf-8') as f:
        return json.load(f)

def load_json_keys_sorted(data_dict):
    # 依 key 長度由長到短排序
    return sorted(data_dict.keys(), key=len, reverse=True)

def match_from_dict(text, start, candidates):
    # 從 text[start:] 嘗試比對候選 key，成功就回傳 (匹配長度, key)，否則 (0, None)
    for candidate in candidates:
        length = len(candidate)
        if text.startswith(candidate, start):
            return length, candidate
    return 0, None

current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": "", "nasal": False}

def assemble_syllable(syllable):
    initial = str(syllable.get("initial", ""))
    vowel = str(syllable.get("vowel", ""))
    nasal = "nn" if syllable.get("nasal") else ""
    rushio = str(syllable.get("rushio", ""))
    tone = str(syllable.get("tone", ""))

    return initial + vowel + nasal + rushio + tone

def get_rushio_value(key, dialect, rushio_dict):
    # 根據腔調取出拼音值，支援巢狀格式的 JSON，如：
    # "⠼⠔": { "default": "ab", "tapu": "abˋ", "choaan": "abˊ" }
    if key not in rushio_dict:
        return None
    entry = rushio_dict[key]
    if isinstance(entry, dict):
        return entry.get(dialect, entry.get("default"))
    else:
        return entry  # fallback for舊格式

def convert_braille_to_pinyin(braille_text, dialect):
    vowels = load_json('dot_vowels.json')
    rushio = load_json('dot_rushio_syllables.json')
    special_cases = load_json('dot_special.json')
    punctuations = load_json('dot_punctuation.json')
    punctuation_keys = load_json_keys_sorted(punctuations)

    dialect_map = {
        'siian2': '四縣腔',
        'namsiian2': '南四縣腔',
        'hailuk': '海陸腔',
        'tapu': '大埔腔',
        'ngiauphin': '饒平腔',
        'choaan': '詔安腔'
    }

    human_dialect = dialect_map.get(dialect, None)
    if human_dialect is None:
        return '⚠️ 無此腔調配置'

    if human_dialect in ['四縣腔', '南四縣腔']:
        consonants = load_json('dot_consonants_siian2.json')
        tones = load_json('dot_tone_siian2.json')
    else:
        consonants = load_json('dot_consonants_hpzt.json')
        tones = load_json('dot_tone_hpzt.json')

    special_keys = load_json_keys_sorted(special_cases)
    consonants_keys = load_json_keys_sorted(consonants)
    vowels_keys = load_json_keys_sorted(vowels)
    rushio_keys = load_json_keys_sorted(rushio)
    tones_keys = load_json_keys_sorted(tones)

    result = []
    current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": "", "nasal": False}

    i = 0
    length = len(braille_text)
    while i < length:
        if braille_text[i] == '⠠':
            # 僅當前音節未開始時，才標記鼻音
            if not any(v for k, v in current_syllable.items() if k != "nasal"):
                current_syllable["nasal"] = True
                i += 1
                continue

        if (
            braille_text[i] == '⠗' and
            (i == 0 or braille_text[i - 1] == ' ') and
            (i + 1 < length and braille_text[i + 1] in tones) and
            (i + 2 == length or braille_text[i + 2] == ' ')
        ):
            current_syllable["vowel"] = "er"
            current_syllable["tone"] = tones[braille_text[i + 1]]
            result.append(assemble_syllable(current_syllable))
            current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": "", "nasal": False}
            i += 2
            continue

        special_len, special_match = match_from_dict(braille_text, i, special_keys)
        if special_len > 0:
            current_syllable["vowel"] = special_cases[special_match]
            i += special_len

            if i < length:
                tone_len, tone_match = match_from_dict(braille_text, i, tones_keys)
                if tone_len > 0:
                    current_syllable["tone"] = tones[tone_match]
                    i += tone_len

            result.append(assemble_syllable(current_syllable))
            current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": "", "nasal": False}
            continue

        rushio_len, rushio_match = match_from_dict(braille_text, i, rushio_keys)
        if rushio_len > 0:
            rushio_value = get_rushio_value(rushio_match, dialect, rushio)
            if rushio_value:
                current_syllable["rushio"] = rushio_value
                i += rushio_len
                continue

        cons_len, cons_match = match_from_dict(braille_text, i, consonants_keys)
        if cons_len > 0:
            if not any(v for k, v in current_syllable.items() if k != "nasal"):
                current_syllable["initial"] = consonants[cons_match]
                i += cons_len
                continue

        vowel_len, vowel_match = match_from_dict(braille_text, i, vowels_keys)
        if vowel_len > 0:
            if vowel_match == '⠔':
                prev_char = braille_text[i - 1] if i > 0 else ''
                if prev_char in ['⠵', '⠉', '⠎']:
                    current_syllable["vowel"] = "ii"
                else:
                    current_syllable["vowel"] = "ua"
            else:
                current_syllable["vowel"] = vowels[vowel_match]
            i += vowel_len

            if i < length:
                final_cons_len, final_cons_match = match_from_dict(braille_text, i, consonants_keys)
                if final_cons_len > 0:
                    next_char = braille_text[i + final_cons_len] if i + final_cons_len < length else ''
                    if next_char in tones:
                        current_syllable["rushio"] = consonants[final_cons_match]
                        i += final_cons_len

            if i < length:
                tone_len, tone_match = match_from_dict(braille_text, i, tones_keys)
                if tone_len > 0:
                    current_syllable["tone"] = tones[tone_match]
                    i += tone_len

                    # ➕ Tone 結束後立即檢查標點
                    if i < length:
                        punct_len, punct_match = match_from_dict(braille_text, i, punctuation_keys)
                        if punct_len > 0:
                            result.append(assemble_syllable(current_syllable))
                            current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": "", "nasal": False}
                            result.append(punctuations[punct_match])
                            i += punct_len
                            continue

            result.append(assemble_syllable(current_syllable))
            current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": "", "nasal": False}
            continue

        tail_len, tail_match = match_from_dict(braille_text, i, tones_keys)
        if tail_len > 0:
            if tail_match in rushio:
                rushio_value = get_rushio_value(tail_match, dialect, rushio)
                if rushio_value:
                    current_syllable["rushio"] = rushio_value
                result.append(assemble_syllable(current_syllable))
                current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": "", "nasal": False}
            else:
                current_syllable["tone"] = tones[tail_match]
            i += tail_len
            continue

        if any(v for k, v in current_syllable.items() if k != "nasal"):
            result.append(assemble_syllable(current_syllable))
            current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": "", "nasal": False}

        # 嘗試匹配標點符號
        punct_len, punct_match = match_from_dict(braille_text, i, punctuation_keys)
        if punct_len > 0:
            result.append(punctuations[punct_match])
            i += punct_len
        else:
            punct_len, punct_match = match_from_dict(braille_text, i, punctuation_keys)
            if punct_len > 0:
                result.append(punctuations[punct_match])
                i += punct_len
            else:
                result.append(braille_text[i])
                i += 1

    if any(v for k, v in current_syllable.items() if k != "nasal"):
        result.append(assemble_syllable(current_syllable))

    return ''.join(result)
