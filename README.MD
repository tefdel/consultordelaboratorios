# AforoLAB UAO

Sistema de visión computacional para monitorear el aforo de laboratorios de la Universidad Autónoma de Occidente con YOLOv8 + DeepSORT.

## Descripción

AforoLAB es una aplicación web que permite consultar en tiempo real el nivel de ocupación de los laboratorios universitarios. Utiliza un pipeline combinado de:
- **CNN (EfficientNet-B0)**: Clasifica el estado global de la imagen (Vacío, Disponible, Lleno)
- **YOLOv8**: Detecta y cuenta personas en tiempo real
- **DeepSORT**: Seguimiento de objetos a través de frames

## Estructura del Proyecto

```
ConsultorDeLaboratorios/
├── README.MD
├── ProyectoFinalPDI/           # Frontend
│   ├── index.html             # Página principal
│   ├── admin.html             # Dashboard administrativo
│   ├── app.js                 # Lógica principal
│   ├── admin.js               # Dashboard de estadísticas
│   ├── horario.js             # Consulta por franja horaria
│   ├── data.js                # Datos de laboratorios
│   ├── styles.css             # Estilos CSS
│   └── data.js
├── backend/                    # API Flask
│   ├── app.py                 # API REST + procesamiento de imágenes
│   ├── train_cnn.py           # Entrenamiento de la CNN
│   └── requirements.txt       # Dependencias
├── Lab_aforo/                 # Dataset de imágenes
│   ├── Labs_Vacíos/
│   ├── Labs_Disponibles/
│   └── Labs_Llenos/
└── models/                     # Modelos entrenados
    └── cnn_hibrida.pth
```

## Laboratorios Monitoreados

| ID | Nombre | Edificio | Piso | Capacidad |
|----|--------|----------|------|-----------|
| lab-fisica | Lab. Física | Bloque 6 | 1 | 22 |
| lab-grafica | Grafica Lab | Bloque 5 | 1 | 20 |
| lab-informatica | Laboratorios Informática | Bloque 9 | 2 | 65 |
| lab-ingenieria | Lab. Ingeniería | Bloque 8 | 2 | 32 |
| zonas-estudio | Zonas de Estudio | Bloque 1 | 1 | 50 |

## Requisitos

```bash
pip install -r backend/requirements.txt
```

Dependencias principales:
- Flask 2.3.3
- flask-cors 4.0.0
- ultralytics (YOLOv8)
- opencv-python
- pillow-heif (soporte HEIC)
- torch, torchvision

## Instalación y Ejecución

1. **Entrenar la CNN** (requiere dataset en `Lab_aforo/`):
```bash
python backend/train_cnn.py
```

2. **Iniciar el servidor Flask**:
```bash
python backend/app.py
```
El servidor corre en `http://localhost:5000`

3. **Servir el frontend**:
Usar un servidor web estático para `ProyectoFinalPDI/`:
```bash
npx serve ProyectoFinalPDI
# o
python -m http.server 8000
```

## API Endpoints

| Endpoint | Descripción |
|----------|-------------|
| `/` | Info del sistema |
| `/detect/<lab_id>` | Detección en tiempo real |
| `/detect-hora/<lab_id>?hora=8.5` | Consulta por franja horaria |
| `/franjas` | Franja horaria disponibles |
| `/output/<lab_id>` | Imagen procesada |

## Tecnologías

- **Frontend**: HTML5, CSS3, JavaScript (ES6+), Chart.js
- **Backend**: Python, Flask, PyTorch
- **Visión**: YOLOv8, EfficientNet-B0, OpenCV
- **Dataset**: Imágenes organizadas por estado (Vacío/Disponible/Lleno)

## Características

- ✅ Consulta de aforo en tiempo real
- ✅ Dashboard con estadísticas históricas
- ✅ Consulta por franja horaria
- ✅ API REST documentada
- ✅ Diseño responsive

## Materia

Proyecto de Procesamiento Digital de Imágenes (PDI)  
Universidad Autónoma de Occidente - Semestre 2026-1