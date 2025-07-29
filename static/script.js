document.addEventListener("DOMContentLoaded", async () => {
  try {
    // 載入 JSON 檔案
    const consonantsHpzt = await (await fetch('/braille_data/dot_consonants_hpzt.json')).json();
    const consonantsSiian2 = await (await fetch('/braille_data/dot_consonants_siian2.json')).json();
    const vowels = await (await fetch('/braille_data/dot_vowels.json')).json();
    const rushio = await (await fetch('/braille_data/dot_rushio_syllables.json')).json();
    const toneHpzt = await (await fetch('/braille_data/dot_tone_hpzt.json')).json();
    const toneSiian2 = await (await fetch('/braille_data/dot_tone_siian2.json')).json();

    // 腔調選項對應的子音+音調資料組合
    const dialectConfigs = {
      "siian2": { consonants: consonantsSiian2, tones: toneSiian2 },
      "namsiian2": { consonants: consonantsSiian2, tones: toneSiian2 },
      "hailuk": { consonants: consonantsHpzt, tones: toneHpzt },
      "tapu": { consonants: consonantsHpzt, tones: toneHpzt },
      "ngiophing": { consonants: consonantsHpzt, tones: toneHpzt },
      "coan": { consonants: consonantsHpzt, tones: toneHpzt },
    };

    // 綁定畫面元素
    const inputBox = document.getElementById('inputText');
    const outputBox = document.getElementById('outputText');
    const convertBtn = document.getElementById('convertBtn');
    const dialectSelect = document.getElementById('outputMode');// 這裡是腔調選單
    const bgColorPicker = document.getElementById('bgColor');
    const textColorPicker = document.getElementById('textColor');

    // 共用 tokenizers
    const multiCodeMap = {
      ...consonantsHpzt,
      ...consonantsSiian2,
      ...vowels,
      ...rushio,
      ...toneHpzt,
      ...toneSiian2
    };
    const multiCodeKeys = Object.keys(multiCodeMap).sort((a, b) => b.length - a.length);

    function tokenize(input) {
      input = input.replace(/\u2800/g, ' ');
      const tokens = [];
      let i = 0;
      while (i < input.length) {
        if (input[i] === '\n' || input[i] === ' ') {
          tokens.push(input[i]);
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

    convertBtn.onclick = () => {
      const brailleText = inputBox.value;
      const dialect = dialectSelect.value;

      fetch('/api/convert', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ braille: brailleText, dialect })
      })
        .then(res => res.json())
        .then(data => {
          outputBox.value = data.result;

          // 自動複製 outputBox 內容到剪貼簿
          navigator.clipboard.writeText(data.result).then(() => {
            copyStatus.textContent = '已自動複製轉換結果！';
            setTimeout(() => {
              copyStatus.textContent = '';
            }, 3000);
          }).catch(() => {
            copyStatus.textContent = '複製失敗，請手動複製。';
            setTimeout(() => {
              copyStatus.textContent = '';
            }, 3000);
          });
        })
        .catch(err => {
          console.error('轉換錯誤：', err);
          outputBox.value = '⚠️ 轉換失敗';
        });
    };

    // ✅ 複製按鈕
    copyBtn.addEventListener('click', () => {
      const text = outputBox.value.trim();
      if (!text) return;

      navigator.clipboard.writeText(text).then(() => {
        copyStatus.textContent = '複製成功！';
      }).catch(() => {
        copyStatus.textContent = '複製失敗，請手動複製。';
      }).finally(() => {
        setTimeout(() => copyStatus.textContent = '', 3000);
      });
    });

    // ✅ 清除按鈕
    clearBtn.addEventListener('click', () => {
      inputBox.value = '';
      outputBox.value = '';
      copyStatus.textContent = '';
    });

    // ✅ 字體大小滑桿
    fontSizeSlider.addEventListener('input', (e) => {
      const size = `${e.target.value}px`;
      fontSizeValue.textContent = size;
      inputBox.style.fontSize = size;
      outputBox.style.fontSize = size;
    });

    // ✅ 背景顏色選擇
    bgColorPicker.addEventListener('input', (e) => {
      const color = e.target.value;
      inputBox.style.backgroundColor = color;
      outputBox.style.backgroundColor = color;
    });

    // ✅ 文字顏色選擇
    textColorPicker.addEventListener('input', (e) => {
      const color = e.target.value;
      inputBox.style.color = color;
      outputBox.style.color = color;
    });

    // ✅ 初始樣式設定
    const initFontSize = `${fontSizeSlider.value}px`;
    fontSizeValue.textContent = initFontSize;
    inputBox.style.fontSize = initFontSize;
    outputBox.style.fontSize = initFontSize;

    const initBgColor = bgColorPicker.value;
    inputBox.style.backgroundColor = initBgColor;
    outputBox.style.backgroundColor = initBgColor;

    const initTextColor = textColorPicker.value;
    inputBox.style.color = initTextColor;
    outputBox.style.color = initTextColor;

  } catch (error) {
    console.error("載入 JSON 發生錯誤：", error);
    alert("無法載入點字資料，請檢查檔案或伺服器設定！");
  }
});

