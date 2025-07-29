from flask import Flask, request, jsonify, render_template
from converter import convert_braille_to_pinyin
from flask import send_from_directory

app = Flask(__name__)

@app.route('/braille_data/<path:filename>')
def serve_braille_data(filename):
    return send_from_directory('braille_data', filename)

# 首頁：表單介面
@app.route("/", methods=["GET", "POST"])
def index():
    result = ""
    if request.method == "POST":
        braille_input = request.form.get("braille", "")
        dialect = request.form.get("dialect", "siian2")
        result = convert_braille(braille_input, dialect)
    return render_template("index.html", result=result)

# API 路由：給前端或第三方系統呼叫
@app.route('/api/convert', methods=['POST'])
def convert():
    data = request.get_json()
    braille = data.get('braille', '')
    dialect = data.get('dialect', '')
    result = convert_braille_to_pinyin(braille, dialect)
    return jsonify({'result': result})

@app.route('/support_us')
def support_us():
    return render_template('support_us.html')

if __name__ == '__main__':
    app.run(debug=True)
