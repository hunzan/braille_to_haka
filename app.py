# app.py
from flask import Flask, render_template, request, jsonify, send_from_directory
from converter import braille_to_tl

app = Flask(__name__)

# 首頁介面
@app.route('/')
def index():
    return render_template('index.html')

# API：接收點字，轉換成台羅
@app.route('/convert', methods=['POST'])
def convert():
    data = request.get_json()
    braille_input = data.get('braille', '')
    tl_output = braille_to_tl(braille_input)
    return jsonify({'result': tl_output})

# 讓 /brailletotl_data/ URL 能對應到專案資料夾的 brailletotl_data 資料夾
@app.route('/brailletotl_data/<path:filename>')
def braille_data(filename):
    return send_from_directory('brailletotl_data', filename)

if __name__ == '__main__':
    app.run(debug=True)
