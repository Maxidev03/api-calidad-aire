import os
import json
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
from pywebpush import webpush, WebPushException

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY')
VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY')
VAPID_CLAIMS = {
    "sub": "mailto:example@email.com"
}

class Medicion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(50), nullable=False)
    gas_level = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class PushSubscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subscription_json = db.Column(db.Text, nullable=False)

@app.route('/save-subscription', methods=['POST'])
def save_subscription():
    data = request.get_json()
    if not data or 'endpoint' not in data:
        return jsonify({"error": "Suscripción inválida"}), 400

    subscription_json_str = json.dumps(data)

    existing_subscription = PushSubscription.query.filter_by(subscription_json=subscription_json_str).first()
    if existing_subscription:
        return jsonify({"status": "ok, suscripción ya existe"}), 200

    new_subscription = PushSubscription(subscription_json=subscription_json_str)
    try:
        db.session.add(new_subscription)
        db.session.commit()
        print(f"Nueva suscripción guardada: {data.get('endpoint')}")
        return jsonify({"status": "ok, suscripción guardada"}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error al guardar suscripción: {e}")
        return jsonify({"error": "No se pudo guardar la suscripción"}), 500

@app.route('/mediciones', methods=['POST'])
def recibir_mediciones():
    datos = request.get_json()
    if not datos or 'deviceId' not in datos or 'gas_level' not in datos:
        return jsonify({"error": "Datos incompletos"}), 400

    nueva_medicion = Medicion(device_id=datos['deviceId'], gas_level=datos['gas_level'])

    try:
        db.session.add(nueva_medicion)
        db.session.commit()
        print(f"Dato guardado: {nueva_medicion.gas_level}")

        if nueva_medicion.gas_level >= 700:
            print("Nivel de gas alto detectado. Enviando notificaciones...")
            send_notifications_to_all(nueva_medicion.gas_level)

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

def send_notifications_to_all(gas_level):
    if not VAPID_PRIVATE_KEY:
        print("Error: VAPID_PRIVATE_KEY no está configurada en las variables de entorno.")
        return

    with app.app_context():
        subscriptions = PushSubscription.query.all()

        payload = {
            "title": "¡Alerta de Calidad del Aire!",
            "body": f"Nivel de contaminación elevado: {gas_level}. Se recomienda precaución.",
            "icon": "https://placehold.co/192x192/fca5a5/b91c1c?text=⚠️"
        }

        for sub_row in subscriptions:
            try:
                subscription_info = json.loads(sub_row.subscription_json)
                webpush(
                    subscription_info=subscription_info,
                    data=json.dumps(payload),
                    vapid_private_key=VAPID_PRIVATE_KEY,
                    vapid_claims=VAPID_CLAIMS.copy()
                )
                print(f"Notificación enviada a: {subscription_info.get('endpoint')}")
            except WebPushException as ex:
                print(f"Error al enviar notificación: {ex}")
                if ex.response and ex.response.status_code in [404, 410]:
                    db.session.delete(sub_row)
                    db.session.commit()
            except Exception as e:
                print(f"Error general al procesar suscripción: {e}")


@app.route('/crear-tablas-en-db-ahora')
def crear_tablas():
    try:
        with app.app_context():
            db.create_all()
        return "<h1>¡Las tablas han sido creadas exitosamente!</h1>"
    except Exception as e:
        return f"<h1>Ocurrió un error al crear las tablas: {e}</h1>"