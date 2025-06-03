import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'brailletotl_data')

def load_json(filename):
    with open(os.path.join(DATA_DIR, filename), encoding='utf-8') as f:
        return json.load(f)

# 載入資料表
consonants = load_json('dottl_consonants.json')         # 純子音
vowels = load_json('dottl_vowels.json')                 # 純母音
nasals = load_json('dottl_nasals.json')                 # 鼻音韻尾與促音
rushio = load_json('dottl_rushio.json')                 # 鼻化韻尾
nasal_cons = load_json('dottl_nasals_cons.json')        # 鼻音子音
nasal_vowels = load_json('dottl_nasals_vowels.json')    # 鼻音母音

def tokenize_braille(braille_str):
    return list(braille_str)  # 不 strip()

def braille_to_tl(braille_str):
    # 將 Unicode 點字空格（\u2800）轉為一般空格
    braille_str = braille_str.replace('\u2800', ' ')
    tokens = tokenize_braille(braille_str)
    result = []
    i = 0

    while i < len(tokens):
        char = tokens[i]

        # 6. 空格 / 換行（以字元為準）
        if char == '\n':
            result.append('\n')
            i += 1
            continue
        elif char == ' ':
            result.append(' ')
            i += 1
            continue

        mapped = ''

        # 1. 鼻音子音 + 鼻音母音：必須配對，否則 ?
        if char in nasal_cons:
            if i + 1 < len(tokens) and tokens[i + 1] in nasal_vowels:
                mapped = nasal_cons[char] + nasal_vowels[tokens[i + 1]]
                i += 2
            else:
                mapped = '?'
                i += 1

        # 2. 純子音：可單獨，或接純母音 / 促音；接鼻音類→ ?
        elif char in consonants:
            if i + 1 < len(tokens):
                next_char = tokens[i + 1]
                if next_char in vowels | rushio:
                    mapped = consonants[char] + (
                        vowels.get(next_char) or rushio.get(next_char)
                    )
                    i += 2
                elif next_char in (nasals | nasal_cons | nasal_vowels):
                    mapped = '?'
                    i += 2
                else:
                    mapped = consonants[char]
                    i += 1
            else:
                mapped = consonants[char]
                i += 1

        # 3. 純母音或促音 / 入聲：可單獨存在
        elif char in vowels:
            mapped = vowels[char]
            i += 1

        elif char in rushio:
            mapped = rushio[char]
            i += 1

        # 4. 鼻音母音或鼻音子音：單獨出現都錯
        elif char in nasal_vowels or char in nasal_cons:
            mapped = '?'
            i += 1

        # 5. 純鼻音：只能單獨存在，前不能有子音組合
        elif char in nasals:
            mapped = nasals[char]
            i += 1

        # 7. 其他不明符號
        else:
            mapped = '?'
            i += 1

        # 判斷是否加 -
        next_token = tokens[i] if i < len(tokens) else ''
        if mapped and next_token not in {' ', '\n', ''}:
            mapped += '-'

        result.append(mapped)

    return ''.join(result)
