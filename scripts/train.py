import os
import shutil
from ultralytics import YOLO

def evaluar_modelo(model_path, data_yaml, split='test'):
    model = YOLO(model_path)
    results = model.val(data=data_yaml, split=split)
    metrics = results.metrics
    map50 = metrics.get('map50', 0) if isinstance(metrics, dict) else getattr(metrics.box, 'map50', 0)
    map_full = metrics.get('map', 0) if isinstance(metrics, dict) else getattr(metrics.box, 'map', 0)
    return map50, map_full

def obtener_ultima_carpeta(base_path, prefix):
    """Devuelve la última carpeta creada que empiece con el prefijo dado."""
    subdirs = [
        os.path.join(base_path, d)
        for d in os.listdir(base_path)
        if os.path.isdir(os.path.join(base_path, d)) and d.startswith(prefix)
    ]
    if not subdirs:
        return None
    # Ordenar por fecha de modificación (más reciente al final)
    subdirs.sort(key=os.path.getmtime)
    return subdirs[-1]

def run_train():
    current_model_path = 'model/potato_leaf_detector.pt'
    deprecated_model_path = 'model/potato_leaf_detector_deprecated.pt'
    data_yaml = 'configs/data.yaml'

    model = YOLO(current_model_path)

    model.train(
        data=data_yaml,
        epochs=20,
        imgsz=640,
        batch=16,
        name='yolo11n_run',
        patience=10
    )

    # Detectar la última carpeta generada
    runs_folder_base = 'runs/detect'
    last_run_folder = obtener_ultima_carpeta(runs_folder_base, 'yolo11n_run')

    if not last_run_folder:
        print("Error: No se encontró ninguna carpeta de entrenamiento en runs/detect/.")
        return

    last_model_path = os.path.join(last_run_folder, 'weights', 'last.pt')

    if not os.path.exists(last_model_path):
        print(f"Error: El modelo entrenado no se encontró en {last_model_path}. No se actualizará el modelo.")
        return

    # Evaluar modelo actual
    if os.path.exists(current_model_path):
        map50_actual, map_actual = evaluar_modelo(current_model_path, data_yaml, split='test')
        print(f"Modelo actual - mAP@0.5: {map50_actual:.4f}, mAP@0.5:0.95: {map_actual:.4f}")
    else:
        map50_actual, map_actual = 0, 0
        print("No existe modelo actual, se asumirá mAP 0 para ambos.")

    # Evaluar modelo nuevo
    map50_nuevo, map_nuevo = evaluar_modelo(last_model_path, data_yaml, split='test')
    print(f"Modelo nuevo - mAP@0.5: {map50_nuevo:.4f}, mAP@0.5:0.95: {map_nuevo:.4f}")

    # Comparar y actualizar si mejora
    if (map_nuevo > map_actual) or (abs(map_nuevo - map_actual) < 1e-4 and map50_nuevo > map50_actual):
        print("Nuevo modelo es mejor. Actualizando modelo guardado...")

        if os.path.exists(deprecated_model_path):
            os.remove(deprecated_model_path)

        if os.path.exists(current_model_path):
            os.rename(current_model_path, deprecated_model_path)

        shutil.copy(last_model_path, current_model_path)
        print("Modelo actualizado correctamente.")
    else:
        print("Nuevo modelo NO mejora al actual. No se actualizará el modelo.")

    # Limpiar carpeta para ahorrar espacio
    if os.path.exists(last_run_folder):
        shutil.rmtree(last_run_folder)
        print(f"Carpeta {last_run_folder} eliminada para liberar espacio.")