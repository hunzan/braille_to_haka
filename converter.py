import json
import os
import re

def load_json(filename):
    base_path = os.path.join(os.path.dirname(__file__), 'braille_data')
    with open(os.path.join(base_path, filename), encoding='utf-8') as f:
        return json.load(f)

def load_json_keys_sorted(data_dict):
    # 依 key 長度由長到短排序
    return sorted(data_dict.keys(), key=len, reverse=True)

def is_punctuation(braille_text, i, punctuation_keys):
    punct_len, punct_match = match_from_dict(braille_text, i, punctuation_keys, allow_trailing_space=True)
    return punct_len > 0

def match_from_dict(text, start, candidates, allow_trailing_space=False):
    for candidate in candidates:
        candidate_to_match = candidate.rstrip() if allow_trailing_space else candidate
        length = len(candidate_to_match)
        if text.startswith(candidate_to_match, start):
            # 回傳原始 candidate（包含尾空白），避免外面 key error
            return length, candidate
    return 0, None

def assemble_syllable(syllable):
    initial = str(syllable.get("initial", ""))
    vowel = str(syllable.get("vowel", ""))
    nasal = "nn" if syllable.get("nasal") else ""
    rushio = str(syllable.get("rushio", ""))
    tone = str(syllable.get("tone", ""))

    syllable_str = initial + vowel + nasal + rushio + tone

    # 若 tone 是空的，就在結尾標上 _
    if tone == "":
        syllable_str += "_"

    return syllable_str

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
        # 處理鼻音⠠
        if braille_text[i] == '⠠':
            if not any(v for k, v in current_syllable.items() if k != "nasal"):
                current_syllable["nasal"] = True
                i += 1
                continue

        # 特殊 er 音節
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

        # 特殊字
        special_len, special_match = match_from_dict(braille_text, i, special_keys)
        if special_len > 0:
            current_syllable["vowel"] = special_cases[special_match]
            i += special_len

            if i < length:
                tone_len, tone_match = match_from_dict(braille_text, i, tones_keys)
                if tone_len > 0:
                    current_syllable["tone"] = tones[tone_match]
                    i += tone_len

                    # 判斷下一個點字是否是標點或拼音
                    if i < length:
                        if is_punctuation(braille_text, i, punctuation_keys):
                            result.append(assemble_syllable(current_syllable))
                            current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": "", "nasal": False}
                        else:
                            # 下一個不是標點，表示音節結束，開始新音節
                            result.append(assemble_syllable(current_syllable))
                            current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": "", "nasal": False}
                    continue

            result.append(assemble_syllable(current_syllable))
            current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": "", "nasal": False}
            continue

        # 腔調 rushio
        rushio_len, rushio_match = match_from_dict(braille_text, i, rushio_keys)
        if rushio_len > 0:
            rushio_value = get_rushio_value(rushio_match, dialect, rushio)
            if rushio_value:
                current_syllable["rushio"] = rushio_value
                i += rushio_len

                # 判斷下一個點字是否是標點或拼音
                if i < length:
                    if is_punctuation(braille_text, i, punctuation_keys):
                        result.append(assemble_syllable(current_syllable))
                        current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": "", "nasal": False}
                    else:
                        # 下一個不是標點，表示音節結束，開始新音節
                        result.append(assemble_syllable(current_syllable))
                        current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": "", "nasal": False}
                continue

        # 子音 consonants
        cons_len, cons_match = match_from_dict(braille_text, i, consonants_keys)
        if cons_len > 0:
            if not any(v for k, v in current_syllable.items() if k != "nasal"):
                current_syllable["initial"] = consonants[cons_match]
                i += cons_len
                continue

        # 母音 vowels
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

                    if i < length:
                        punct_len, punct_match = match_from_dict(braille_text, i, punctuation_keys, allow_trailing_space=True)
                        if punct_len > 0 and punct_match is not None:
                            result.append(assemble_syllable(current_syllable))
                            current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": "", "nasal": False}

                            if punct_match == '⠦':
                                prev_char = braille_text[i - 1] if i > 0 else ''
                                next_char = braille_text[i + punct_len] if i + punct_len < length else ''

                                if prev_char in tones:
                                    result.append('？')
                                elif not next_char or (next_char not in tones and next_char != ' '):
                                    result.append('「')
                                else:
                                    result.append('？')
                            else:
                                result.append(punctuations[punct_match])

                            i += punct_len
                            continue

            result.append(assemble_syllable(current_syllable))
            current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": "", "nasal": False}
            continue

        # 尾音 tone 或 rushio
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

        # 當前音節已經有內容，先輸出
        if any(v for k, v in current_syllable.items() if k != "nasal"):
            result.append(assemble_syllable(current_syllable))
            current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": "", "nasal": False}

        # 嘗試匹配標點符號
        punct_len, punct_match = match_from_dict(braille_text, i, punctuation_keys, allow_trailing_space=True)
        if punct_len > 0 and punct_match is not None:
            # 特殊處理 ⠦
            if punct_match == '⠦':
                prev_char = braille_text[i - 1] if i > 0 else ''
                next_char = braille_text[i + punct_len] if i + punct_len < length else ''

                if prev_char in tones:
                    result.append('？')
                elif not next_char or (next_char not in tones and next_char != ' '):
                    result.append('「')
                else:
                    result.append('？')

            # 新增特別允許 ⠴ 可接其他標點，不影響前面標點處理
            elif punct_match == '⠴':
                # 這裡不管前面是不是標點，都直接加上對應標點符號
                result.append(punctuations[punct_match])

            else:
                result.append(punctuations[punct_match])

            i += punct_len
            continue
        else:
            # 找不到匹配，當作原字輸出，避免死循環
            result.append(braille_text[i])
            i += 1

    # 最後還有殘留音節輸出
    if any(v for k, v in current_syllable.items() if k != "nasal"):
        result.append(assemble_syllable(current_syllable))

    raw_pinyin = ''.join(result)
    # 讓 _ 後面接拼音的地方空一格
    final_pinyin = re.sub(r'_(?=[a-zA-Zng])', ' ', raw_pinyin)
    # 把其他的 _ 全部移除（遇到標點的情況）
    final_pinyin = final_pinyin.replace('_', '')
    return final_pinyin

def add_space_after_tone_less_syllable(text):
    # 定義 tone 記號
    tone_marks = ['ˋ', 'ˊ', 'ˇ', '˙']

    # 定義標點符號
    punctuation_marks = ['。', '，', '！', '？', '：', '；', '」', '）', '】', '》', '』', '”', '’']

    result = []
    i = 0
    while i < len(text):
        result.append(text[i])
        # 檢查這個字元是否是拼音字母
        if text[i].isalpha():
            # 檢查下一個字元是否是 tone
            next_char = text[i + 1] if i + 1 < len(text) else ''
            if next_char not in tone_marks:
                # 再檢查下一個字元是否是標點符號或空格
                lookahead = text[i + 1] if i + 1 < len(text) else ''
                if lookahead not in punctuation_marks and lookahead != ' ':
                    result.append(' ')
        i += 1

    return ''.join(result)
