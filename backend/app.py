import os
import cv2
import random
import datetime

import torch
import torch.nn as nn
import numpy as np

from torchvision import transforms, models
from PIL import Image
from ultralytics import YOLO
from flask import Flask, jsonify, send_file, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ======================================
# RUTAS
# ======================================

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT   = os.path.abspath(os.path.join(BASE_DIR, '..'))
DATASET_FOLDER = os.path.join(PROJECT_ROOT, 'Lab_aforo')
MODEL_DIR      = os.path.join(PROJECT_ROOT, 'models')
MODEL_PATH     = os.path.join(MODEL_DIR, 'cnn_hibrida.pth')
OUTPUT_FOLDER  = os.path.join(BASE_DIR, 'outputs')
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# ======================================
# CARGAR YOLO
# ======================================

print('Cargando YOLOv8...')
yolo_model = YOLO('yolov8n.pt')
print('YOLOv8 listo.')

# ======================================
# CARGAR CNN
# ======================================

CNN_CLASSES = ['Disponible', 'Lleno', 'Vacio']   # orden alfabético = ImageFolder

def cargar_cnn():
    model = models.efficientnet_b0(weights=None)
    in_features      = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.4),
        nn.Linear(in_features, 3),
    )
    checkpoint = torch.load(MODEL_PATH, map_location=DEVICE)
    # El checkpoint puede ser state_dict directo o dict con 'model_state_dict'
    if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
        state = checkpoint['model_state_dict']
        # Usar clases guardadas si existen
        if 'classes' in checkpoint:
            global CNN_CLASSES
            CNN_CLASSES = checkpoint['classes']
    else:
        state = checkpoint
    model.load_state_dict(state)
    model.to(DEVICE)
    model.eval()
    return model

print('Cargando CNN...')
try:
    cnn_model = cargar_cnn()
    CNN_OK    = True
    print(f'CNN lista. Clases: {CNN_CLASSES}')
except Exception as e:
    cnn_model = None
    CNN_OK    = False
    print(f'CNN no disponible: {e}')

# ======================================
# TRANSFORM PARA CNN (igual que en entrenamiento)
# ======================================

cnn_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225]),
])

def predecir_cnn(image_path: str) -> tuple[str, float]:
    """Devuelve (clase_predicha, confianza 0-1)."""
    if not CNN_OK:
        return 'Sin CNN', 0.0
    try:
        pil_img = Image.open(image_path).convert('RGB')
        tensor  = cnn_transform(pil_img).unsqueeze(0).to(DEVICE)
        with torch.no_grad():
            logits = cnn_model(tensor)
            probs  = torch.softmax(logits, dim=1)[0]
            idx    = probs.argmax().item()
        return CNN_CLASSES[idx], float(probs[idx])
    except Exception as e:
        print(f'Error CNN: {e}')
        return 'Error', 0.0

# ======================================
# MAPEO: id frontend → subcarpeta dataset
# ======================================

LAB_FOLDER_MAP = {
    'lab-fisica':      'fisica',
    'lab-grafica':     'grafica',
    'lab-informatica': 'informatica',
    'lab-ingenieria':  'ingenieros',
    'zonas-estudio':   'zonaestudio',
}

# ======================================
# FRANJAS HORARIAS → CATEGORIA
# ======================================

def hora_a_categoria(hora: float) -> str:
    if   6.0  <= hora < 7.0:  return 'Vacio'
    elif 7.0  <= hora < 8.5:  return 'Disponible'
    elif 8.5  <= hora < 12.0: return 'Lleno'
    elif 12.0 <= hora < 13.0: return 'Vacio'
    elif 13.0 <= hora < 15.0: return 'Disponible'
    elif 15.0 <= hora < 17.0: return 'Lleno'
    elif 17.0 <= hora < 20.0: return 'Disponible'
    elif 20.0 <= hora < 21.5: return 'Vacio'
    else:                      return 'Vacio'

def categoria_a_carpeta(categoria: str) -> str:
    mapping = {
        'Vacio':      'Labs_Vacíos',
        'Disponible': 'Labs_Disponibles',
        'Lleno':      'Labs_Llenos',
    }
    nombre = mapping.get(categoria, 'Labs_Vacíos')
    ruta   = os.path.join(DATASET_FOLDER, nombre)
    if not os.path.exists(ruta):
        keyword = categoria.lower()[:3]
        for entry in os.listdir(DATASET_FOLDER):
            if keyword in entry.lower() and os.path.isdir(
                os.path.join(DATASET_FOLDER, entry)
            ):
                return entry
    return nombre

def buscar_imagen(lab_folder: str, categoria: str):
    carpeta_cat = categoria_a_carpeta(categoria)
    carpeta_lab = os.path.join(DATASET_FOLDER, carpeta_cat, lab_folder)
    if not os.path.exists(carpeta_lab):
        return None
    VALID = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.heic'}
    imagenes = [
        f for f in os.listdir(carpeta_lab)
        if os.path.splitext(f)[1].lower() in VALID
    ]
    if not imagenes:
        return None
    return os.path.join(carpeta_lab, random.choice(imagenes))

# ======================================
# PIPELINE COMBINADO: CNN + YOLO
# ======================================

def procesar_imagen(image_path: str, lab_id: str, hora_str: str, categoria: str):
    """
    1. CNN  → clasifica estado global de la imagen
    2. YOLO → detecta y cuenta personas, dibuja boxes
    3. Combina ambos resultados en la imagen de salida
    """

    # ── Soporte HEIC ──────────────────────────────
    if image_path.lower().endswith('.heic'):
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
            pil_img = Image.open(image_path).convert('RGB')
            image   = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        except Exception as e:
            return None, f'No se pudo leer HEIC: {e}'
    else:
        image = cv2.imread(image_path)

    if image is None:
        return None, 'No se pudo leer la imagen'

    # ── 1. CNN ────────────────────────────────────
    cnn_label, cnn_conf = predecir_cnn(image_path)

    # ── 2. YOLO ───────────────────────────────────
    results      = yolo_model(image_path)
    people_count = 0

    for result in results:
        for box in result.boxes:
            if int(box.cls[0]) == 0:          # clase 0 = persona
                people_count += 1
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf_yolo = float(box.conf[0])
                cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(image,
                            f'Persona {conf_yolo:.0%}',
                            (x1, y1 - 8),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.45, (0, 255, 0), 1)

    # ── 3. Estado YOLO ────────────────────────────
    if people_count == 0:
        yolo_label = 'Vacio'
    elif people_count < 15:
        yolo_label = 'Disponible'
    else:
        yolo_label = 'Lleno'

    # ── 4. Estado final combinado ─────────────────
    # La CNN conoce el contexto global (luz, mobiliario, densidad visual)
    # YOLO da el conteo exacto de personas
    # Usamos CNN como etiqueta principal + YOLO como verificación
    estado_final = cnn_label   # etiqueta principal = CNN

    # Colores
    COLOR = {
        'Disponible': (34,  197, 94),    # verde
        'Lleno':      (220, 38,  38),    # rojo
        'Vacio':      (156, 163, 175),   # gris
        'Sin CNN':    (255, 165,  0),
        'Error':      (255, 165,  0),
    }
    c_cnn  = COLOR.get(cnn_label,   (255, 165, 0))
    c_yolo = COLOR.get(yolo_label,  (255, 165, 0))
    c_fin  = COLOR.get(estado_final,(255, 165, 0))

    # ── 5. Overlay de texto ───────────────────────
    h, w = image.shape[:2]

    # Banda negra semitransparente arriba
    overlay = image.copy()
    cv2.rectangle(overlay, (0, 0), (w, 130), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.55, image, 0.45, 0, image)

    # Línea 1 — hora y categoría consultada
    cv2.putText(image,
                f'Hora: {hora_str}  |  Franja: {categoria}',
                (16, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                (200, 200, 200), 1)

    # Línea 2 — resultado CNN
    cv2.putText(image,
                f'CNN: {cnn_label}  ({cnn_conf:.0%})',
                (16, 62),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75,
                c_cnn, 2)

    # Línea 3 — resultado YOLO
    cv2.putText(image,
                f'YOLO: {people_count} personas  ->  {yolo_label}',
                (16, 96),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75,
                c_yolo, 2)

    # Línea 4 — estado final (CNN)
    cv2.putText(image,
                f'Estado final: {estado_final}',
                (16, 126),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75,
                c_fin, 2)

    # ── 6. Guardar ────────────────────────────────
    output_path = os.path.join(OUTPUT_FOLDER, f'{lab_id}.jpg')
    cv2.imwrite(output_path, image)

    return {
        'people':       people_count,
        'yolo_label':   yolo_label,
        'cnn_label':    cnn_label,
        'cnn_conf':     round(cnn_conf, 3),
        'estado_final': estado_final,
        'categoria':    categoria,
        'hora':         hora_str,
        'image_url':    f'http://localhost:5000/output/{lab_id}',
    }, None

# ======================================
# ROOT
# ======================================

@app.route('/')
def index():
    return jsonify({
        'message': 'AforoLAB API — CNN + YOLOv8',
        'cnn_ok':  CNN_OK,
        'clases':  CNN_CLASSES,
    })

# ======================================
# DETECT (tiempo real)
# ======================================

@app.route('/detect/<lab_id>')
def detect(lab_id):
    if lab_id not in LAB_FOLDER_MAP:
        return jsonify({'error': 'Lab no encontrado'}), 404
    try:
        now      = datetime.datetime.now()
        hora_dec = now.hour + now.minute / 60
        hora_str = now.strftime('%H:%M')
        categoria   = hora_a_categoria(hora_dec)
        image_path  = buscar_imagen(LAB_FOLDER_MAP[lab_id], categoria)
        if image_path is None:
            return jsonify({'error': 'No hay imágenes para este lab/categoría'}), 404
        resultado, error = procesar_imagen(image_path, lab_id, hora_str, categoria)
        if error:
            return jsonify({'error': error}), 500
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ======================================
# DETECT POR HORA
# GET /detect-hora/<lab_id>?hora=8.5
# ======================================

@app.route('/detect-hora/<lab_id>')
def detect_hora(lab_id):
    if lab_id not in LAB_FOLDER_MAP:
        return jsonify({'error': 'Lab no encontrado'}), 404
    hora_param = request.args.get('hora')
    if hora_param is None:
        return jsonify({'error': 'Falta el parámetro ?hora=HH.MM'}), 400
    try:
        hora = float(hora_param)
    except ValueError:
        return jsonify({'error': 'hora debe ser numérico (ej. 8.5)'}), 400
    if not (0 <= hora < 24):
        return jsonify({'error': 'Hora fuera de rango (0-23.99)'}), 400
    try:
        categoria  = hora_a_categoria(hora)
        image_path = buscar_imagen(LAB_FOLDER_MAP[lab_id], categoria)
        if image_path is None:
            return jsonify({
                'error': f'No hay imágenes de "{categoria}" para "{lab_id}"'
            }), 404
        h, m     = int(hora), int(round((hora - int(hora)) * 60))
        hora_str = f'{h:02d}:{m:02d}'
        resultado, error = procesar_imagen(image_path, lab_id, hora_str, categoria)
        if error:
            return jsonify({'error': error}), 500
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ======================================
# FRANJAS INFO
# ======================================

@app.route('/franjas')
def franjas():
    return jsonify([
        {'desde': '06:00', 'hasta': '07:00', 'categoria': 'Vacio',      'label': 'Laboratorio vacío'},
        {'desde': '07:00', 'hasta': '08:30', 'categoria': 'Disponible', 'label': 'Hora más suave'},
        {'desde': '08:30', 'hasta': '12:00', 'categoria': 'Lleno',      'label': 'Hora pico'},
        {'desde': '12:00', 'hasta': '13:00', 'categoria': 'Vacio',      'label': 'Laboratorio vacío'},
        {'desde': '13:00', 'hasta': '15:00', 'categoria': 'Disponible', 'label': 'Hora más suave'},
        {'desde': '15:00', 'hasta': '17:00', 'categoria': 'Lleno',      'label': 'Hora pico'},
        {'desde': '17:00', 'hasta': '20:00', 'categoria': 'Disponible', 'label': 'Hora más suave'},
        {'desde': '20:00', 'hasta': '21:30', 'categoria': 'Vacio',      'label': 'Laboratorio vacío'},
    ])

# ======================================
# SERVIR IMAGEN
# ======================================

@app.route('/output/<lab_id>')
def output_image(lab_id):
    path = os.path.join(OUTPUT_FOLDER, f'{lab_id}.jpg')
    if not os.path.exists(path):
        return jsonify({'error': 'Imagen no generada aún'}), 404
    return send_file(path, mimetype='image/jpeg')

# ======================================
# RUN
# ======================================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)