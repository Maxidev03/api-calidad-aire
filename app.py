import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Medicion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(50), nullable=False)
    gas_level = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<Medicion {self.id} - Gas: {self.gas_level}>'

@app.route('/mediciones', methods=['POST'])
def recibir_mediciones():
    datos = request.get_json()
    if not datos or 'deviceId' not in datos or 'gas_level' not in datos:
        return jsonify({"error": "Datos incompletos"}), 400

    nueva_medicion = Medicion(device_id=datos['deviceId'], gas_level=datos['gas_level'])

    try:
        db.session.add(nueva_medicion)
        db.session.commit()
        return jsonify({"status": "ok, datos guardados"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "No se pudo guardar en la base de datos"}), 500

@app.route('/mediciones', methods=['GET'])
def obtener_mediciones():
    try:
        ultimas_mediciones = Medicion.query.order_by(Medicion.timestamp.desc()).limit(100).all()
        resultados = []
        for medicion in ultimas_mediciones:
            resultados.append({
                "id": medicion.id,
                "deviceId": medicion.device_id,
                "gas_level": medicion.gas_level,
                "timestamp": medicion.timestamp.isoformat() + "Z"
            })
        return jsonify(resultados)
    except Exception as e:
        return jsonify({"error": "No se pudo obtener datos"}), 500
