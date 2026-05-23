import os
import cv2

from ultralytics import YOLO

from flask import Flask, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ======================================
# RUTAS
# ======================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PROJECT_ROOT = os.path.abspath(
    os.path.join(BASE_DIR, '..')
)

DATASET_FOLDER = os.path.join(
    PROJECT_ROOT,
    'Lab_aforo'
)

OUTPUT_FOLDER = os.path.join(
    BASE_DIR,
    'outputs'
)

os.makedirs(
    OUTPUT_FOLDER,
    exist_ok=True
)

# ======================================
# YOLO
# ======================================

print('Cargando YOLOv8...')

yolo_model = YOLO('yolov8n.pt')

# ======================================
# MAPEO LABS
# ======================================

LAB_FOLDER_MAP = {
    'lab-fisica': 'fisica',
    'lab-grafica': 'grafica',
    'lab-informatica': 'informatica',
    'lab-ingenieria': 'ingenieros',
    'zonas-estudio': 'zonaestudio'
}

# ======================================
# CATEGORÍAS
# ======================================

CATEGORIES = [
    'Labs_Disponibles',
    'Labs_Llenos',
    'Labs_Vacios'
]

# ======================================
# ROOT
# ======================================

@app.route('/')
def index():

    return jsonify({
        'message': 'YOLO funcionando'
    })

# ======================================
# DETECT
# ======================================

@app.route('/detect/<lab_id>')
def detect(lab_id):

    if lab_id not in LAB_FOLDER_MAP:

        return jsonify({
            'error': 'Lab no encontrado'
        }), 404

    try:

        lab_folder = LAB_FOLDER_MAP[lab_id]

        image_path = None

        # ==================================
        # BUSCAR PRIMERA IMAGEN
        # ==================================

        for category in CATEGORIES:

            folder_path = os.path.join(
                DATASET_FOLDER,
                category,
                lab_folder
            )

            if os.path.exists(folder_path):

                files = sorted([

                    f for f in os.listdir(folder_path)

                    if f.lower().endswith((
                        '.png',
                        '.jpg',
                        '.jpeg'
                    ))

                ])

                if files:

                    image_path = os.path.join(
                        folder_path,
                        files[0]
                    )

                    break

        # ==================================
        # VALIDACIÓN
        # ==================================

        if image_path is None:

            return jsonify({
                'error': 'No hay imágenes'
            }), 404

        # ==================================
        # LEER IMAGEN
        # ==================================

        image = cv2.imread(
            image_path
        )

        # ==================================
        # YOLO
        # ==================================

        results = yolo_model(
            image_path
        )

        people_count = 0

        for result in results:

            for box in result.boxes:

                cls = int(box.cls[0])

                # PERSONA
                if cls == 0:

                    people_count += 1

                    x1, y1, x2, y2 = map(
                        int,
                        box.xyxy[0]
                    )

                    # RECTÁNGULO
                    cv2.rectangle(
                        image,
                        (x1, y1),
                        (x2, y2),
                        (0, 255, 0),
                        2
                    )

                    # TEXTO
                    cv2.putText(
                        image,
                        'Persona',
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),
                        2
                    )

        # ==================================
        # ESTADO
        # ==================================

        if people_count == 0:

            estado = 'Disponible'

        elif people_count < 15:

            estado = 'Medio'

        else:

            estado = 'Lleno'

        # ==================================
        # TEXTO FINAL
        # ==================================

        cv2.putText(
            image,
            f'Personas: {people_count}',
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            3
        )

        cv2.putText(
            image,
            f'Estado: {estado}',
            (20, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 0, 0),
            3
        )

        # ==================================
        # GUARDAR
        # ==================================

        output_path = os.path.join(
            OUTPUT_FOLDER,
            f'{lab_id}.jpg'
        )

        cv2.imwrite(
            output_path,
            image
        )

        # ==================================
        # RESPUESTA
        # ==================================

        return jsonify({

            'people': people_count,

            'cnn_label': estado,

            'image_url':
                f'http://localhost:5000/output/{lab_id}'

        })

    except Exception as e:

        return jsonify({
            'error': str(e)
        }), 500

# ======================================
# SERVIR IMAGEN
# ======================================

@app.route('/output/<lab_id>')
def output_image(lab_id):

    output_path = os.path.join(
        OUTPUT_FOLDER,
        f'{lab_id}.jpg'
    )

    return send_file(
        output_path,
        mimetype='image/jpeg'
    )

# ======================================
# RUN
# ======================================

if __name__ == '__main__':

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )