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
    # 載入共用資料
    vowels = load_json('dot_vowels.json')
    rushio = load_json('dot_rushio_syllables.json')
    special_cases = load_json('dot_special.json')

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

    # 先整理 key 長度順序（長 ➜ 短）
    special_keys = load_json_keys_sorted(special_cases)
    consonants_keys = load_json_keys_sorted(consonants)
    vowels_keys = load_json_keys_sorted(vowels)
    rushio_keys = load_json_keys_sorted(rushio)
    tones_keys = load_json_keys_sorted(tones)

    result = []
    current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": ""}

    i = 0
    length = len(braille_text)
    while i < length:
        # 鼻音宣告：點字第六點 ⠠ 出現在音節開頭，標示鼻音（nn）
        if braille_text[i] == '⠠':
            # 若當前音節還是空的，則標記鼻音（之後拼好音節再加）
            if not any(current_syllable.values()):
                current_syllable["nasal"] = True  # 自定欄位 nasal
                i += 1
                continue

        # 特判：⠗ 為 er 的條件：前面為空格或開頭，後面接 tone，然後是空格或句尾
        if (
                braille_text[i] == '⠗' and
                (i == 0 or braille_text[i - 1] == ' ') and
                (i + 1 < length and braille_text[i + 1] in tones) and
                (i + 2 == length or braille_text[i + 2] == ' ')
        ):
            current_syllable["vowel"] = "er"
            current_syllable["tone"] = tones[braille_text[i + 1]]
            result.append(assemble_syllable(current_syllable))
            current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": ""}
            i += 2
            continue

        # ✅ 特殊點字：允許前面已有子音 initial
        special_len, special_match = match_from_dict(braille_text, i, special_keys)
        if special_len > 0:
            special_value = special_cases[special_match]

            if current_syllable["initial"]:  # 若已有子音
                current_syllable["vowel"] = special_value
                result.append(assemble_syllable(current_syllable))
                current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": ""}
            else:
                # 沒有子音時整組當獨立音節使用
                result.append(special_value)

            i += special_len
            continue

        # 拼音 rushio（如 ⠔=d、⠢=bˋ）：直接作為音節尾，並結束音節
        rushio_len, rushio_match = match_from_dict(braille_text, i, rushio_keys)
        if rushio_len > 0:
            rushio_value = get_rushio_value(rushio_match, dialect, rushio)

            if rushio_value:
                current_syllable["rushio"] = rushio_value
                i += rushio_len
                continue

        # 聲母
        cons_len, cons_match = match_from_dict(braille_text, i, consonants_keys)
        if cons_len > 0:
            if not any(current_syllable.values()):
                current_syllable["initial"] = consonants[cons_match]
                i += cons_len
                continue

        # 元音處理區
        vowel_len, vowel_match = match_from_dict(braille_text, i, vowels_keys)
        if vowel_len > 0:
            if vowel_match == '⠔':
                prev_char = braille_text[i - 1] if i > 0 else ''
                if prev_char in ['⠵', '⠉', '⠎']:  # z, c, s 的點字
                    current_syllable["vowel"] = "ii"
                else:
                    current_syllable["vowel"] = "ua"
            else:
                current_syllable["vowel"] = vowels[vowel_match]
            i += vowel_len
            continue

        # 尾音區塊：可能是 rushio（⠔、⠢）或 tone
        tail_len, tail_match = match_from_dict(braille_text, i, tones_keys)
        if tail_len > 0:
            if tail_match in rushio:
                rushio_value = get_rushio_value(tail_match, dialect, rushio)
                if rushio_value:
                    current_syllable["rushio"] = rushio_value
                result.append(assemble_syllable(current_syllable))
                current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": ""}
            else:
                current_syllable["tone"] = tones[tail_match]
            i += tail_len
            continue

        # 例外字元：當作分隔符號
        if any(current_syllable.values()):
            result.append(assemble_syllable(current_syllable))
            current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": ""}
        result.append(braille_text[i])
        i += 1

    if any(current_syllable.values()):
        result.append(assemble_syllable(current_syllable))

    return ''.join(result)
