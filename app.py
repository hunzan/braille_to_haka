from flask import Flask, render_template, request, jsonify, send_from_directory
from converter import braille_to_tl, convert_tl_to_poj  # 新增 POJ 轉換函式

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    data = request.get_json()
    braille_input = data.get('braille', '')
    output_mode = data.get('outputMode', 'tl')  # 預設是台羅

    # Step 1：點字轉台羅
    tl_output = braille_to_tl(braille_input)

    # Step 2：若使用者選 POJ，轉為 POJ（內部處理差異表）
    if output_mode == 'poj':
        tl_output = convert_tl_to_poj(tl_output)

    # Step 3：回傳最後結果
    return jsonify({'result': tl_output})

@app.route('/brailletotl_data/<path:filename>')
def braille_data(filename):
    return send_from_directory('brailletotl_data', filename)

@app.route('/support_us')
def support_us():
    return render_template('support_us.html')

if __name__ == '__main__':
    app.run(debug=True)
