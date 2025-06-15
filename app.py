from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/mediciones', methods=['POST'])
def recibir_mediciones():
    datos = request.get_json()

    print(f"Datos recibidos: {datos}")


    return jsonify({"status": "ok, datos recibidos"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)