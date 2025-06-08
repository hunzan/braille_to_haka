document.addEventListener("DOMContentLoaded", async () => {
  try {
    // 載入所有 JSON
    const consonants = await (await fetch('/brailletotl_data/dottl_consonants.json')).json();
    const vowels = await (await fetch('/brailletotl_data/dottl_vowels.json')).json();
    const nasals = await (await fetch('/brailletotl_data/dottl_nasals.json')).json();
    const rushio = await (await fetch('/brailletotl_data/dottl_rushio.json')).json();
    const nasalCons = await (await fetch('/brailletotl_data/dottl_nasals_cons.json')).json();
    const nasalVowels = await (await fetch('/brailletotl_data/dottl_nasals_vowels.json')).json();

    // 加入 POJ 差異表
    const pojDiff = await (await fetch('/brailletotl_data/tl_to_poj_diff.json')).json();

    const multiCodeMap = {
      ...nasals,
      ...vowels,
      ...rushio,
      ...nasalCons,
      ...nasalVowels
    };

    const multiCodeKeys = Object.keys(multiCodeMap).sort((a, b) => b.length - a.length);

    function tokenize(input) {
      input = input.replace(/\u2800/g, ' ');
      const tokens = [];
      let i = 0;

      while (i < input.length) {
        if (input[i] === '\n') {
          tokens.push('\n');
          i++;
          continue;
        }
        if (input[i] === ' ') {
          tokens.push(' ');
          i++;
          continue;
        }

        let matched = false;
        for (const key of multiCodeKeys) {
          if (input.startsWith(key, i)) {
            tokens.push(key);
            i += key.length;
            matched = true;
            break;
          }
        }

        if (!matched) {
          tokens.push(input[i]);
          i++;
        }
      }

      return tokens;
    }

    function convertTLtoPOJ(tlText, pojDiff) {
      tlText = tlText.replace(/nn/g, "ⁿ");

      const sortedDiff = Object.entries(pojDiff).sort((a, b) => b[1].length - a[1].length);
      for (const [poj, tl] of sortedDiff) {
        const regex = new RegExp(tl, 'g');
        tlText = tlText.replace(regex, poj);
      }

      // 補救字典
      const fixMap = {
        "ⁿg": "nng",
        "ⁿ̂g": "nn̂g",
        "ⁿ̄g": "nn̄g",
        "ⁿ̋g": "nn̆g",
      };

      for (const [key, val] of Object.entries(fixMap)) {
        const regex = new RegExp(key, 'g');
        tlText = tlText.replace(regex, val);
      }

      return tlText;
    }

    // 元素綁定
    const inputBox = document.getElementById('inputText');
    const outputBox = document.getElementById('outputText');
    const convertBtn = document.getElementById('convertBtn');
    const copyBtn = document.getElementById('copyBtn');
    const clearBtn = document.getElementById('clearBtn');
    const fontSizeSlider = document.getElementById('fontSizeSlider');
    const fontSizeValue = document.getElementById('fontSizeValue');
    const bgColorPicker = document.getElementById('bgColor');
    const textColorPicker = document.getElementById('textColor');
    const copyStatus = document.getElementById('copyStatus');
    const outputFormatSelect = document.getElementById('outputMode');

    convertBtn.onclick = () => {
      const brailleStr = inputBox.value;
      const tokens = tokenize(brailleStr);

      let i = 0;
      const partialResult = [];

      while (i < tokens.length) {
        const char = tokens[i];

        if (char === '\n') {
          partialResult.push('\n');
          i++;
          continue;
        }
        if (char === ' ') {
          partialResult.push(' ');
          i++;
          continue;
        }

        let mapped = '';

        if (nasalCons[char]) {
          const next = tokens[i + 1];
          if (next && nasalVowels[next]) {
            mapped = nasalCons[char] + nasalVowels[next];
            i += 2;
          } else {
            mapped = '?';
            i++;
          }
        } else if (consonants[char]) {
          const next = tokens[i + 1];
          if (next && vowels[next]) {
            mapped = consonants[char] + vowels[next];
            i += 2;
          } else if (next && rushio[next]) {
            mapped = consonants[char] + rushio[next];
            i += 2;
          } else if (next && (nasals[next] || nasalCons[next] || nasalVowels[next])) {
            mapped = '?';
            i += 2;
          } else {
            mapped = consonants[char];
            i += 1;
          }
        } else if (vowels[char]) {
          mapped = vowels[char];
          i++;
        } else if (nasalVowels[char] || nasalCons[char]) {
          mapped = '?';
          i++;
        } else if (nasals[char]) {
          mapped = nasals[char];
          i++;
        } else if (rushio[char]) {
          mapped = rushio[char];
          i++;
        } else {
          mapped = '?';
          i++;
        }

        const nextToken = tokens[i] || '';
        if (mapped && nextToken !== ' ' && nextToken !== '\n' && nextToken !== '') {
          mapped += '-';
        }

        partialResult.push(mapped);
      }

      // 先組合成台羅文字
      const tlResult = partialResult.join('');

      // 判斷使用者選擇是否要輸出 POJ
      const outputFormat = outputFormatSelect.value;
      let finalResult = tlResult;

      if (outputFormat === 'poj') {
        finalResult = convertTLtoPOJ(tlResult, pojDiff);
      }

      outputBox.value = finalResult;

      navigator.clipboard.writeText(finalResult).then(() => {
        copyStatus.textContent = '已自動複製轉換結果！';
        setTimeout(() => (copyStatus.textContent = ''), 3000);
      }).catch(() => {
        copyStatus.textContent = '複製失敗，請手動複製。';
        setTimeout(() => (copyStatus.textContent = ''), 3000);
      });
    };

    copyBtn.onclick = () => {
      const text = outputBox.value;
      if (!text) return;
      navigator.clipboard.writeText(text).then(() => {
        copyStatus.textContent = '複製成功！';
        setTimeout(() => (copyStatus.textContent = ''), 3000);
      }).catch(() => {
        copyStatus.textContent = '複製失敗，請手動複製。';
        setTimeout(() => (copyStatus.textContent = ''), 3000);
      });
    };

    clearBtn.onclick = () => {
      inputBox.value = '';
      outputBox.value = '';
      copyStatus.textContent = '';
    };

    fontSizeSlider.addEventListener('input', (e) => {
      const size = e.target.value;
      fontSizeValue.textContent = size + 'px';
      inputBox.style.fontSize = size + 'px';
      outputBox.style.fontSize = size + 'px';
    });

    bgColorPicker.addEventListener('input', (e) => {
      const color = e.target.value;
      inputBox.style.backgroundColor = color;
      outputBox.style.backgroundColor = color;
    });

    textColorPicker.addEventListener('input', (e) => {
      const color = e.target.value;
      inputBox.style.color = color;
      outputBox.style.color = color;
    });

    // 預設初始化樣式
    inputBox.style.fontSize = fontSizeSlider.value + 'px';
    outputBox.style.fontSize = fontSizeSlider.value + 'px';
    inputBox.style.backgroundColor = bgColorPicker.value;
    outputBox.style.backgroundColor = bgColorPicker.value;
    inputBox.style.color = textColorPicker.value;
    outputBox.style.color = textColorPicker.value;

  } catch (error) {
    console.error('載入 JSON 發生錯誤：', error);
  }
});

