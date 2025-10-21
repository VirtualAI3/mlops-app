from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from ultralytics import YOLO
from PIL import Image
import io
import base64
import sqlite3
from datetime import datetime, timedelta
import json
import threading
import time
import subprocess
import ssl
import os

DB_PATH = "data/database.sqlite"

# ------------------ BASE DE DATOS ------------------ #
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stars INTEGER,
            detections TEXT,
            image_source TEXT,
            created_at TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS retrain_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            executed_at TEXT,
            num_registros INTEGER,
            detalles TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ------------------ REENTRENAMIENTO AUTOMÁTICO ------------------ #
def verificar_condicion_reentrenamiento():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        hoy = datetime.now().date().isoformat()
        cursor.execute("SELECT COUNT(*) FROM retrain_log WHERE DATE(executed_at)=?", (hoy,))
        if cursor.fetchone()[0] > 0:
            print(f"🚫 Ya se realizó un reentrenamiento hoy ({hoy}).")
            conn.close()
            return

        fecha_limite = (datetime.now() - timedelta(days=6)).isoformat()
        cursor.execute("SELECT detections FROM predictions WHERE stars=1 AND created_at>=?", (fecha_limite,))
        registros = cursor.fetchall()
        conn.close()

        filtrados = sum(
            any(d['confidence'] < 0.51 for d in json.loads(det[0])) for det in registros
        )

        if filtrados >= 2:
            print("🔁 Ejecutando retrain.py...")
            subprocess.run(["python", "scripts/retrain.py"], check=True)
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO retrain_log (executed_at, num_registros, detalles) VALUES (?, ?, ?)",
                (datetime.now().isoformat(), filtrados, f"Reentrenamiento con {filtrados} registros")
            )
            conn.commit()
            conn.close()
            print("✅ Reentrenamiento completado.")
        else:
            print(f"⏳ No se cumple condición ({filtrados}/2).")

    except Exception as e:
        print(f"⚠️ Error en verificación: {e}")

def tarea_periodica_reentrenamiento(intervalo_horas=6):
    while True:
        verificar_condicion_reentrenamiento()
        time.sleep(intervalo_horas * 3600)

thread = threading.Thread(target=tarea_periodica_reentrenamiento, args=(6,), daemon=True)
thread.start()

# ------------------ FLASK APP ------------------ #
app = Flask(__name__)
CORS(app)  # habilita CORS si hay frontends externos

class_names = ['Bacteria', 'Fungi', 'Sano', 'Nematodo', 'Peste', 'Phytophthora']
model = YOLO('model/potato_leaf_detector.pt')

@app.route("/")
def index():
    return send_from_directory('.', 'templates/index.html')

@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.json
        image_data = data.get("image")
        if not image_data:
            return jsonify({"error": "No image provided"}), 400

        img_bytes = base64.b64decode(image_data.split(",")[1])
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

        results = model(img)
        detections = []
        threshold = 0.5
        for box in results[0].boxes:
            conf = float(box.conf.cpu().numpy()[0])
            if conf < threshold:
                continue
            xyxy = box.xyxy.cpu().numpy().flatten()
            cls = int(box.cls.cpu().numpy()[0])
            detections.append({
                "x1": float(xyxy[0]),
                "y1": float(xyxy[1]),
                "x2": float(xyxy[2]),
                "y2": float(xyxy[3]),
                "confidence": conf,
                "class": class_names[cls] if cls < len(class_names) else str(cls)
            })
        return jsonify({"detections": detections})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/save_rating", methods=["POST"])
def save_rating():
    try:
        data = request.json
        stars = data.get("stars")
        detections = data.get("detections")
        image_source = data.get("image_source")
        if stars is None or detections is None or image_source is None:
            return jsonify({"error": "Faltan campos"}), 400
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO predictions (stars, detections, image_source, created_at)
            VALUES (?, ?, ?, ?)
        ''', (stars, json.dumps(detections), image_source, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return jsonify({"message": "Calificación guardada correctamente"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Para pruebas locales HTTPS
    context = ssl.SSLContext(ssl.PROTOCOL_TLS)
    if os.path.exists("cert.pem") and os.path.exists("key.pem"):
        context.load_cert_chain("cert.pem", "key.pem")
        app.run(host="0.0.0.0", port=8443, ssl_context=context)
    else:
        print("⚠️ No se encontraron certificados SSL, ejecutando en HTTP.")
        app.run(host="0.0.0.0", port=5000)