import os
import random
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ======================================
# RUTAS
# ======================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Subir un nivel desde /backend
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..'))

# Ruta de la carpeta del dataset
DATASET_FOLDER = os.path.join(PROJECT_ROOT, 'Lab_aforo')

# ======================================
# MAPEO DE LABORATORIOS
# ======================================

LAB_FOLDER_MAP = {
    'lab-fisica': 'fisica',
    'lab-grafica': 'grafica',
    'lab-informatica': 'informatica',
    'lab-ingenieria': 'ingenieros',
    'zonas-estudio': 'zonaestudio'
}

# Carpetas del dataset
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
        'message': 'AforoLAB API funcionando',
        'dataset': DATASET_FOLDER
    })

# ======================================
# OBTENER IMAGEN DE LAB
# ======================================

@app.route('/image/<lab_id>')
def get_lab_image(lab_id):

    if lab_id not in LAB_FOLDER_MAP:
        return jsonify({
            'error': 'Laboratorio no encontrado'
        }), 404

    lab_folder = LAB_FOLDER_MAP[lab_id]

    try:

        all_images = []

        # Buscar imágenes en todas las categorías
        for category in CATEGORIES:

            folder_path = os.path.join(
                DATASET_FOLDER,
                category,
                lab_folder
            )

            print("Buscando en:", folder_path)

            if os.path.exists(folder_path):

                files = [
                    f for f in os.listdir(folder_path)
                    if f.lower().endswith((
                        '.png',
                        '.jpg',
                        '.jpeg',
                        '.webp'
                    ))
                ]

                for file in files:
                    all_images.append({
                        'folder': folder_path,
                        'file': file
                    })

        # Si no hay imágenes
        if not all_images:
            return jsonify({
                'error': 'No se encontraron imágenes',
                'lab_id': lab_id,
                'lab_folder': lab_folder
            }), 404

        # Elegir una aleatoria
        selected = random.choice(all_images)

        print("Imagen enviada:", selected['file'])

        return send_from_directory(
            selected['folder'],
            selected['file']
        )

    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

# ======================================
# RUN
# ======================================

if __name__ == '__main__':

    print("===================================")
    print("AforoLAB Backend")
    print("PROJECT_ROOT:", PROJECT_ROOT)
    print("DATASET_FOLDER:", DATASET_FOLDER)
    print("===================================")

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )