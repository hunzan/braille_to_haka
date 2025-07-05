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

@app.route("/ncp/api/create-order", methods=["POST"])
def create_order():
    try:
        data = request.get_json()  # 取前端傳來的資料
        print("收到訂單資料：", data)

        # 🔸 這裡應該要呼叫 PayPal 的 API 建立訂單（等你後續串接）
        # 先假裝建立訂單成功，給個假的訂單 ID
        order_id = "FAKE_ORDER_ID_12345"

        # 回傳訂單 ID（前端會用這個）
        return jsonify({"id": order_id})
    except Exception as e:
        print("建立訂單時發生錯誤：", e)
        return jsonify({"error": "建立訂單失敗"}), 500

if __name__ == '__main__':
    app.run(debug=True)
