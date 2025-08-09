import json
import os
import re

def _peek_nonspace(text, pos):
    # 取下一個非空白字元（若沒有則回 ''），不移動游標；把 U+2800 視為空白
    i = pos
    n = len(text)
    while i < n and text[i] in (' ', '\u2800'):
        i += 1
    return text[i] if i < n else ''

def _prev_nonspace(text, pos):
    # 取上一個非空白字元（若沒有則回 ''）；把 U+2800 視為空白
    i = pos - 1
    while i >= 0 and text[i] in (' ', '\u2800'):
        i -= 1
    return text[i] if i >= 0 else ''

def _endswith_key(text, end_index, key_set, max_len):
    """檢查 text[:end_index] 是否以 key_set 中任一鍵結尾（長度至多 max_len）。"""
    start = max(0, end_index - max_len)
    for j in range(end_index, start, -1):
        if text[j-1:end_index] in key_set:
            return True
    return False

def load_json(filename):
    base_path = os.path.join(os.path.dirname(__file__), 'braille_data')
    with open(os.path.join(base_path, filename), encoding='utf-8') as f:
        return json.load(f)

def load_json_keys_sorted(data_dict):
    # 依 key 長度由長到短排序
    return sorted(data_dict.keys(), key=len, reverse=True)

def match_from_dict(text, start, candidates, allow_trailing_space=False):
    # candidates 須為「已依長度由長到短」的列表
    for candidate in candidates:
        candidate_to_match = candidate.rstrip() if allow_trailing_space else candidate
        length = len(candidate_to_match)
        if text.startswith(candidate_to_match, start):
            # 回傳原始 candidate（包含尾空白），避免外面 key error
            return length, candidate
    return 0, None

# ---------- 新增：共用小工具 ----------

def _has_syllable_content(syllable):
    # 除了 nasal 以外的欄位只要有值，就代表正在組裝音節
    return any(v for k, v in syllable.items() if k != "nasal")

def _endswith_any(text, end_index, keys):
    """
    檢查 text[:end_index] 是否以 keys 之任何鍵（最長優先）結尾。
    回傳 (匹配長度, 鍵)；若無則 (0, None)。
    """
    for k in keys:
        L = len(k)
        if end_index - L >= 0 and text[end_index - L:end_index] == k:
            return L, k
    return 0, None

def _is_tone_char(ch, tones_dict):
    return ch in tones_dict

def _peek_nonspace(text, pos):
    # 取下一個非空白字元（若沒有則回 ''），不移動游標
    i = pos
    n = len(text)
    while i < n and text[i] == ' ':
        i += 1
    return text[i] if i < n else ''

def _prev_nonspace(text, pos):
    # 取上一個非空白字元（若沒有則回 ''）
    i = pos - 1
    while i >= 0 and text[i] == ' ':
        i -= 1
    return text[i] if i >= 0 else ''

def _match_punctuation_with_context(text, i, punctuation_keys, tones_keys, rushio_keys,
                                    current_syllable, punct_map,
                                    opening_braille_set=None, closing_braille_set=None):
    """
    具有脈絡的標點判定：
      1) 位置 i 能匹配某個標點鍵
      2) 前面只能是：起始/空格/ tone / rushio 結尾
      3) 後面第一個非空白不可是 tone
    ★ 特例：若命中「開括號」或「閉括號」集合，直接視為標點（避免被拼音誤吃）
    """
    # 嘗試匹配任何標點（含可帶尾空白的鍵）
    punct_len, punct_match = match_from_dict(text, i, punctuation_keys, allow_trailing_space=True)
    if punct_len == 0 or punct_match is None:
        return 0, None

    # ★ 高優先級（收斂版）：括號類「在合理脈絡」才放行，避免與母音同形時誤殺
    # ★ 高優先級（收斂版）：括號類「在合理脈絡」才放行，避免與母音同形時誤殺
    if opening_braille_set and punct_match in opening_braille_set:
        if not _has_syllable_content(current_syllable):  # 不在組音節中
            prev_ch = _prev_nonspace(text, i)
            # 前面是起始/空白/已確定的點字標點鍵（用 punct_map 的鍵判斷）
            if prev_ch == '' or prev_ch == ' ' or prev_ch in punct_map:
                next_ch = _peek_nonspace(text, i + punct_len)
                # 開括號後面不能馬上是 tone（標點不帶 tone）
                if not next_ch or next_ch not in tones_keys:
                    return punct_len, punct_match
        # 不符合上述脈絡 → 不強行放行，落回一般規則

    if closing_braille_set and punct_match in closing_braille_set:
        # 閉括號通常出現在音節後；只要不在組音節中就視為標點
        if not _has_syllable_content(current_syllable):
            return punct_len, punct_match
        # 若正在組音節，先讓音節結束後再由外層流程處理，不在這裡硬判
        return 0, None

    # 前面脈絡：只能是起始/空格/ tone / rushio
    prev_ch = _prev_nonspace(text, i)
    prev_ok = False
    if prev_ch == '' or prev_ch == ' ':
        prev_ok = True
    else:
        if prev_ch in tones_keys:
            prev_ok = True
        else:
            _, rkey = _endswith_any(text, i, rushio_keys)
            if rkey is not None:
                prev_ok = True
    if not prev_ok:
        return 0, None

    # 後面脈絡：第一個非空白不能是 tone（標點不帶 tone）
    next_ch = _peek_nonspace(text, i + punct_len)
    if next_ch and next_ch in tones_keys:
        return 0, None

    return punct_len, punct_match

# ---------- 組裝輸出 ----------

def assemble_syllable(syllable):
    initial = str(syllable.get("initial", ""))
    vowel = str(syllable.get("vowel", ""))
    nasal = "nn" if syllable.get("nasal") else ""
    rushio = str(syllable.get("rushio", ""))
    tone = str(syllable.get("tone", ""))

    # rushio 後面不加底線，不管 tone 有沒有
    syllable_text = initial + vowel + nasal + rushio + tone

    # 如果沒有 rushio 且沒有 tone，才加底線，用來標記空格
    if rushio == "" and tone == "":
        syllable_text += "_"

    return syllable_text

def get_rushio_value(key, dialect, rushio_dict):
    # 根據腔調取出拼音值，支援巢狀格式的 JSON，如：
    # "⠼⠔": { "default": "ab", "tapu": "abˋ", "choaan": "abˊ" }
    if key not in rushio_dict:
        return None
    entry = rushio_dict[key]
    if isinstance(entry, dict):
        return entry.get(dialect, entry.get("default"))
    else:
        return entry  # fallback for 舊格式

def convert_braille_to_pinyin(braille_text, dialect):
    vowels = load_json('dot_vowels.json')
    rushio = load_json('dot_rushio_syllables.json')
    special_cases = load_json('dot_special.json')
    punctuations = load_json('dot_punctuation.json')

    # ★ 動態蒐集：這些明眼標點的「點字鍵」
    opening_targets = {'『', '【', '（'}
    closing_targets = {'】'}  # 若也想包含『」』）等，自己加進來
    opening_braille_set = {k for k, v in punctuations.items() if v in opening_targets}
    closing_braille_set = {k for k, v in punctuations.items() if v in closing_targets}

    punctuation_keys = load_json_keys_sorted(punctuations)
    special_punctuations_allow_prefix = ["⠴", "⠠⠴", "⠐⠜", "⠨⠜"]  # 保留，但會先走「脈絡判定」版

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

    # ★ 查表用（供分號短路與 bb 限制）
    rushio_key_set = set(rushio_keys)
    rushio_max_len = max((len(k) for k in rushio_keys), default=0)
    tones_key_set  = set(tones_keys)
    tones_max_len  = max((len(k) for k in tones_keys),  default=0)

    # 開/閉括號鍵：長到短排序，避免子串誤配
    opening_braille_sorted = sorted(opening_braille_set, key=len, reverse=True)
    closing_braille_sorted = sorted(closing_braille_set, key=len, reverse=True)

    result = []
    current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": "", "nasal": False}

    i = 0
    length = len(braille_text)

    while i < length:

        # ★ 高優先級：句首 / 空白 / 點字空白 / 換行 後的「開括號」一定當標點
        #   這三個：『(⠠⠦)、【(⠨⠣)、（(⠐⠣)
        if i == 0 or braille_text[i - 1] in (' ', '\u2800', '\n', '\r'):
            # 安全回退用：若 dot_punctuation.json 無對應鍵，給預設明眼符號
            hard_open_map = {'⠠⠦': '『', '⠨⠣': '【', '⠐⠣': '（'}
            matched_open_key = None
            matched_open_len = 0

            for open_key in ('⠠⠦', '⠨⠣', '⠐⠣'):
                if braille_text.startswith(open_key, i):
                    matched_open_key = open_key
                    matched_open_len = len(open_key)
                    break

            if matched_open_key is not None:
                if _has_syllable_content(current_syllable):
                    result.append(assemble_syllable(current_syllable))
                    current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": "", "nasal": False}
                result.append(punctuations.get(matched_open_key, hard_open_map[matched_open_key]))
                i += matched_open_len
                continue

        # ★ 高優先級：遇到「閉括號」鍵，直接當標點
        matched_close = None
        for k in closing_braille_sorted:
            if braille_text.startswith(k, i):
                matched_close = k
                break
        if matched_close is not None:
            if _has_syllable_content(current_syllable):
                result.append(assemble_syllable(current_syllable))
                current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": "", "nasal": False}
            result.append(punctuations[matched_close])  # 】（或你表裡定義的任一閉括號）
            i += len(matched_close)
            continue

        # ★ 高優先級：若 '⠆' 後為點字空格，且「前面是 rushio 或 tone」，視為分號 '；'
        if braille_text[i] == '⠆' and i + 1 < length and braille_text[i + 1] == '\u2800':
            prev_is_rushio = _endswith_key(braille_text, i, rushio_key_set, rushio_max_len)
            prev_is_tone   = _endswith_key(braille_text, i, tones_key_set,  tones_max_len)
            if prev_is_rushio or prev_is_tone:
                if _has_syllable_content(current_syllable):
                    result.append(assemble_syllable(current_syllable))
                    current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": "", "nasal": False}
                result.append('；')
                i += 2  # 跳過 '⠆' 與點字空格
                continue

        # ★ (A) 標點：先用「脈絡判定」的方式辨識，避免把母音/聲母誤當標點
        punct_len, punct_match = _match_punctuation_with_context(
            braille_text, i, punctuation_keys, tones_keys, rushio_keys,
            current_syllable, punctuations,
            opening_braille_set, closing_braille_set
        )
        if punct_len > 0:
            # 若當前音節尚未輸出，先結束它（理論上 _match 已確保沒有在組裝中）
            if _has_syllable_content(current_syllable):
                result.append(assemble_syllable(current_syllable))
                current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": "", "nasal": False}

            # 特例處理 ⠦（和你原邏輯一致）
            prev_char = _prev_nonspace(braille_text, i)
            next_char = _peek_nonspace(braille_text, i + punct_len)

            if punct_match == '⠦':
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

        # ★ (B) 兼容你原有「某些前綴形標點」的特殊判斷（多數情形會被 (A) 提早處理）
        sp_len, sp_match = match_from_dict(braille_text, i, special_punctuations_allow_prefix)
        if sp_len > 0:
            # 若後面第一個非空白是 tone，視為拼音，不當標點
            next_char = _peek_nonspace(braille_text, i + sp_len)
            if next_char in tones:
                pass
            else:
                # 同樣檢查脈絡；不合規就不當標點
                _plen, _pm = _match_punctuation_with_context(
                    braille_text, i, punctuation_keys, tones_keys, rushio_keys,
                    current_syllable, punctuations,
                    opening_braille_set, closing_braille_set
                )
                if _plen > 0 and _pm == sp_match:
                    # 是標點
                    if _has_syllable_content(current_syllable):
                        result.append(assemble_syllable(current_syllable))
                        current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": "", "nasal": False}
                    result.append(punctuations[sp_match])
                    i += sp_len
                    continue

        # (C) 拼音區塊開始：鼻化 ⠠
        if braille_text[i] == '⠠':
            if not _has_syllable_content(current_syllable):
                current_syllable["nasal"] = True
                i += 1
                continue

        # (D) 特殊 er 音節
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

        # (E) 特殊字
        special_len, special_match = match_from_dict(braille_text, i, special_keys)
        if special_len > 0:
            current_syllable["vowel"] = special_cases[special_match]
            i += special_len

            if i < length:
                tone_len, tone_match = match_from_dict(braille_text, i, tones_keys)
                if tone_len > 0:
                    current_syllable["tone"] = tones[tone_match]
                    i += tone_len

                    # 標點檢查（允許尾隨空白）
                    if i < length:
                        p_len, p_match = match_from_dict(braille_text, i, punctuation_keys, allow_trailing_space=True)
                        if p_len > 0 and p_match is not None:
                            result.append(assemble_syllable(current_syllable))
                            current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": "", "nasal": False}

                            # ⠦ 特例
                            prev_char = _prev_nonspace(braille_text, i)
                            next_char = _peek_nonspace(braille_text, i + p_len)
                            if p_match == '⠦':
                                if prev_char in tones:
                                    result.append('？')
                                elif not next_char or (next_char not in tones and next_char != ' '):
                                    result.append('「')
                                else:
                                    result.append('？')
                            else:
                                result.append(punctuations[p_match])

                            i += p_len
                            continue

            result.append(assemble_syllable(current_syllable))
            current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": "", "nasal": False}
            continue

        # (F) 腔調 rushio
        rushio_len, rushio_match = match_from_dict(braille_text, i, rushio_keys)
        if rushio_len > 0:
            rushio_value = get_rushio_value(rushio_match, dialect, rushio)
            if rushio_value:
                current_syllable["rushio"] = rushio_value
                i += rushio_len

                # 標點 or 下一音節
                if i < length:
                    # 依脈絡判定是否標點
                    p_len, p_match = _match_punctuation_with_context(
                        braille_text, i, punctuation_keys, tones_keys, rushio_keys,
                        current_syllable, punctuations,
                        opening_braille_set, closing_braille_set
                    )
                    if p_len > 0:
                        result.append(assemble_syllable(current_syllable))
                        current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": "", "nasal": False}

                        # ⠦ 特例
                        prev_char = _prev_nonspace(braille_text, i)
                        next_char = _peek_nonspace(braille_text, i + p_len)
                        if p_match == '⠦':
                            if prev_char in tones:
                                result.append('？')
                            elif not next_char or (next_char not in tones and next_char != ' '):
                                result.append('「')
                            else:
                                result.append('？')
                        else:
                            result.append(punctuations[p_match])

                        i += p_len
                        continue

                # 預設：結束音節
                result.append(assemble_syllable(current_syllable))
                current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": "", "nasal": False}
            continue

        # (G) 子音 consonants
        cons_len, cons_match = match_from_dict(braille_text, i, consonants_keys)
        if cons_len > 0:
            # ★ '⠆' 作為子音 bb 的嚴格條件：
            #    1) 必須在音節起始（current_syllable 目前不能有內容）
            #    2) 而且 '⠆' 後面「馬上」要能匹配到一個母音鍵（否則交給 tone/標點處理）
            if cons_match == '⠆':
                if not _has_syllable_content(current_syllable):
                    next_is_vowel = False
                    if i + cons_len < length:
                        vlen, _ = match_from_dict(braille_text, i + cons_len, vowels_keys)
                        next_is_vowel = vlen > 0
                    if next_is_vowel:
                        current_syllable["initial"] = consonants[cons_match]
                        i += cons_len
                        continue
                # 其他情況：不要當 bb，讓後續 (H)/(I)/(A) 去判斷（tone 或 標點）
            else:
                if not _has_syllable_content(current_syllable):
                    current_syllable["initial"] = consonants[cons_match]
                    i += cons_len
                    continue

        # (H) 母音 vowels
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

            # 嘗試補 rushio（僅限「子音作 rushio」的舊格式相容）
            if i < length:
                final_cons_len, final_cons_match = match_from_dict(braille_text, i, consonants_keys)
                if final_cons_len > 0:
                    # ★ 重要：禁止 '⠆' 在母音後被當成尾子音（避免吃掉真正的 tone/分號）
                    if final_cons_match != '⠆':
                        next_ch = _peek_nonspace(braille_text, i + final_cons_len)
                        if next_ch in tones_keys:
                            current_syllable["rushio"] = consonants[final_cons_match]
                            i += final_cons_len

            # 補 tone
            if i < length:
                tone_len, tone_match = match_from_dict(braille_text, i, tones_keys)
                if tone_len > 0:
                    current_syllable["tone"] = tones[tone_match]
                    i += tone_len

                    # tone 後若接標點（脈絡判定）
                    if i < length:
                        p_len, p_match = _match_punctuation_with_context(
                            braille_text, i, punctuation_keys, tones_keys, rushio_keys,
                            current_syllable, punctuations,
                            opening_braille_set, closing_braille_set
                        )
                        if p_len > 0:
                            result.append(assemble_syllable(current_syllable))
                            current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": "", "nasal": False}

                            # ⠦ 特例
                            prev_char = _prev_nonspace(braille_text, i)
                            next_char = _peek_nonspace(braille_text, i + p_len)
                            if p_match == '⠦':
                                if prev_char in tones:
                                    result.append('？')
                                elif not next_char or (next_char not in tones and next_char != ' '):
                                    result.append('「')
                                else:
                                    result.append('？')
                            else:
                                result.append(punctuations[p_match])

                            i += p_len
                            continue

            # 結束音節
            result.append(assemble_syllable(current_syllable))
            current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": "", "nasal": False}
            continue

        # (I) 尾音：tone 或 rushio（tones_keys 內有些鍵同時在 rushio 作對映時）
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

        # (J) 無法匹配：若有正在組裝的音節，先輸出；否則當原字輸出避免卡住
        if _has_syllable_content(current_syllable):
            result.append(assemble_syllable(current_syllable))
            current_syllable = {"initial": "", "vowel": "", "rushio": "", "tone": "", "nasal": False}
            continue

        # 嘗試最後一次「一般標點」（允許尾空白），否則原字輸出
        p2_len, p2_match = match_from_dict(braille_text, i, punctuation_keys, allow_trailing_space=True)
        if p2_len > 0 and p2_match is not None:
            prev_char = _prev_nonspace(braille_text, i)
            next_char = _peek_nonspace(braille_text, i + p2_len)
            if p2_match == '⠦':
                if prev_char in tones:
                    result.append('？')
                elif not next_char or (next_char not in tones and next_char != ' '):
                    result.append('「')
                else:
                    result.append('？')
            else:
                result.append(punctuations[p2_match])
            i += p2_len
            continue
        else:
            result.append(braille_text[i])
            i += 1

    # 收尾：若有殘留音節
    if _has_syllable_content(current_syllable):
        result.append(assemble_syllable(current_syllable))

    raw_pinyin = ''.join(result)
    # 讓 _ 後面接拼音的地方空一格
    final_pinyin = re.sub(r'_(?=[a-zA-Zng])', ' ', raw_pinyin)
    # 把其他的 _ 全部移除（遇到標點的情況）
    final_pinyin = final_pinyin.replace('_', '')
    # ★ 逗號「，」前後不留空白（你要的是明眼拼音的逗號）
    final_pinyin = re.sub(r'\s*，\s*', '，', final_pinyin)
    return final_pinyin

def add_space_after_tone_less_syllable(text):
    # 只對底線後接拼音字母（排除以 ng/m/t/p 等 rushio 開頭）插入空格
    # 假設 rushio 為 ng, m, t, p
    text = re.sub(r'_(?=[a-zA-Z])(?!ng|m|t|p)', ' ', text)
    text = text.replace('_', '')
    text = re.sub(r'([ˇˋˊ\^]) ', r'\1', text)
    return text
