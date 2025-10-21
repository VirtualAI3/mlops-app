from flask import Flask, request, jsonify, send_from_directory
from ultralytics import YOLO
from PIL import Image
import io
import base64
import sqlite3
from datetime import datetime
import json
import threading
import time
import subprocess
from datetime import datetime, timedelta

DB_PATH = "data/database.sqlite"

def init_retrain_log_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
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

init_retrain_log_db()

def verificar_condicion_reentrenamiento():
    """Revisa la BD y ejecuta retrain.py si se cumplen las condiciones."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Verificar si ya hubo reentrenamiento hoy
        hoy = datetime.now().date().isoformat()
        cursor.execute("SELECT COUNT(*) FROM retrain_log WHERE DATE(executed_at) = ?", (hoy,))
        entrenamientos_hoy = cursor.fetchone()[0]
        if entrenamientos_hoy > 0:
            print(f"🚫 Ya se realizó un reentrenamiento hoy ({hoy}). Se omite.")
            conn.close()
            return

        # Verificar condiciones de reentrenamiento
        fecha_limite = (datetime.now() - timedelta(days=6)).isoformat()
        cursor.execute('''
            SELECT detections FROM predictions
            WHERE stars = 1 AND created_at >= ?
        ''', (fecha_limite,))

        registros = cursor.fetchall()
        conn.close()

        # Contar los registros que cumplen condición
        filtrados = 0
        for (detections_json,) in registros:
            detections = json.loads(detections_json)
            if any(d['confidence'] < 0.51 for d in detections):
                filtrados += 1
            if filtrados >= 2:
                break

        # Condición para reentrenar
        if filtrados >= 2:
            print("🔁 Se detectaron 2+ registros con 1 estrella y confianza < 0.51. Ejecutando retrain.py...")
            subprocess.run(["python", "retrain.py"], check=True)
            print("✅ Reentrenamiento completado.")

            # Registrar evento
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO retrain_log (executed_at, num_registros, detalles)
                VALUES (?, ?, ?)
            ''', (datetime.now().isoformat(), filtrados, f"Reentrenamiento automático con {filtrados} registros filtrados"))
            conn.commit()
            conn.close()

        else:
            print(f"⏳ No se cumple la condición aún ({filtrados}/2 registros).")

    except Exception as e:
        print(f"⚠️ Error en verificación automática: {e}")


def tarea_periodica_reentrenamiento(intervalo_horas=6):
    """Ejecuta la verificación cada X horas (por defecto cada 6 horas)."""
    while True:
        verificar_condicion_reentrenamiento()
        time.sleep(intervalo_horas * 3600)


thread = threading.Thread(target=tarea_periodica_reentrenamiento, args=(0.1,), daemon=True)
thread.start()


DB_PATH = "data/database.sqlite"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stars INTEGER,
            detections TEXT,          -- JSON con lista de detecciones
            image_source TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()


app = Flask(__name__)

# Cambia esta lista con los nombres reales de tus clases en el orden correcto
class_names = ['Bacteria', 'Fungi', 'Sano', 'Nematodo', 'Peste', 'Phytophthora']

# Cargar modelo YOLOv8
model = YOLO('model/potato_leaf_detector.pt')  # Cambia por el nombre de tu modelo

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

        # Decodificar imagen base64
        img_bytes = base64.b64decode(image_data.split(",")[1])
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")  # Convertir a RGB

        # Inferencia
        results = model(img)

        detections = []
        result = results[0]

        threshold = 0.5

        for box in result.boxes:
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
        detections = data.get("detections")  # Esperamos lista de detecciones
        image_source = data.get("image_source")
        
        if stars is None or detections is None or image_source is None:
            return jsonify({"error": "Faltan campos obligatorios"}), 400
        
        detections_json = json.dumps(detections)
        created_at = datetime.now().isoformat()
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO predictions (stars, detections, image_source, created_at)
            VALUES (?, ?, ?, ?)
        ''', (stars, detections_json, image_source, created_at))
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Calificación guardada correctamente"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
