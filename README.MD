# AforoLAB UAO
### Sistema de monitoreo de aforo en tiempo real

> **Universidad Autónoma de Occidente · Cali, Colombia**  
> Procesamiento Digital de Imágenes · Semestre 2026-I  
> Stack: `YOLOv8` · `CNN` · `DeepSORT` · `OpenCV` · `Flask` · `HTML/CSS/JS`

---

## 1. Descripción general

AforoLAB es una aplicación web que permite monitorear en tiempo real el nivel de ocupación de los laboratorios del campus UAO mediante visión computacional. El sistema combina dos modelos de inteligencia artificial:

- **YOLOv8n** — detección y conteo de personas fotograma a fotograma.
- **EfficientNet-B0 (CNN híbrida)** — clasificación global del estado del laboratorio (`Vacío` / `Disponible` / `Lleno`).

Los resultados se presentan a través de una interfaz web responsiva con auto-refresh cada 30 segundos.

---

## 2. Estructura del proyecto

```
AforoLAB/
├── backend/
│   ├── app.py                  ← Servidor Flask principal
│   └── outputs/                ← Imágenes procesadas (generadas en runtime)
├── frontend/
│   ├── index.html              ← Página principal
│   ├── styles.css              ← Estilos globales
│   ├── data.js                 ← Datos estáticos + helpers compartidos
│   ├── app.js                  ← Lógica del finder y grid de laboratorios
│   └── horario.js              ← Consulta por franja horaria
├── models/
│   └── cnn_hibrida.pth         ← Pesos EfficientNet-B0 entrenados
└── Lab_aforo/                  ← Dataset de imágenes
    ├── Labs_Vacíos/
    │   ├── fisica/
    │   ├── grafica/
    │   ├── informatica/
    │   ├── ingenieros/
    │   └── zonaestudio/
    ├── Labs_Disponibles/
    │   └── ...
    └── Labs_Llenos/
        └── ...
```

---

## 3. Requisitos del sistema

### Backend (Python)

| Paquete | Versión mínima |
|---|---|
| Python | 3.10 |
| PyTorch | 2.x (CPU o CUDA) |
| Ultralytics | ≥ 8.0 |
| OpenCV | opencv-python |
| Flask | flask + flask-cors |
| Torchvision | torchvision |
| Pillow | Pillow (+ `pillow-heif` opcional para HEIC) |

### Frontend

No requiere instalación. Es HTML/CSS/JS puro; solo se necesita un navegador moderno (Chrome 90+, Firefox 90+, Edge 90+). El dashboard usa **Chart.js 4.4** cargado desde CDN.

---

## 4. Instalación y ejecución

### 1. Clonar el repositorio

```bash
git clone https://github.com/uao/aforolab.git
cd AforoLAB
```

### 2. Instalar dependencias Python

```bash
pip install torch torchvision ultralytics
pip install flask flask-cors opencv-python Pillow

# Opcional — soporte imágenes HEIC (dispositivos Apple)
pip install pillow-heif
```

### 3. Iniciar el servidor Flask

```bash
cd backend
python app.py
```

El servidor arranca en `http://localhost:5000`. En el primer inicio descarga automáticamente los pesos de YOLOv8n (~6 MB).

### 4. Abrir el frontend

Abre `frontend/index.html` directamente en el navegador, o sírvelo con un servidor estático:

```bash
# Con Python
cd frontend && python -m http.server 8080

# Con Node
npx serve frontend
```

---

## 5. Endpoints de la API Flask

Base URL: `http://localhost:5000`

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/` | Estado del servidor, versión CNN y clases disponibles |
| `GET` | `/detect/<lab_id>` | Detección en tiempo real según la hora actual |
| `GET` | `/detect-hora/<lab_id>?hora=8.5` | Detección para una franja horaria específica |
| `GET` | `/franjas` | Lista de franjas horarias disponibles |
| `GET` | `/output/<lab_id>` | Sirve la última imagen procesada del laboratorio |

### IDs de laboratorio válidos

| ID | Laboratorio |
|---|---|
| `lab-fisica` | Lab. Física — Bloque 6, Piso 1 |
| `lab-grafica` | Grafica Lab — Bloque 5, Piso 1 |
| `lab-informatica` | Laboratorios Informática — Bloque 9, Piso 2 |
| `lab-ingenieria` | Lab. Ingeniería — Bloque 8, Piso 2 |
| `zonas-estudio` | Zonas de Estudio — Bloque 1, Piso 1 |

---

## 6. Franjas horarias

El sistema clasifica cada consulta en una categoría según la hora del día:

| Franja | Categoría | Descripción |
|---|---|---|
| 06:00 – 07:00 | `Vacío` | Sin actividad académica |
| 07:00 – 08:30 | `Disponible` | Hora tranquila de apertura |
| 08:30 – 12:00 | `Lleno` | Hora pico matutina |
| 12:00 – 13:00 | `Vacío` | Pausa del mediodía |
| 13:00 – 15:00 | `Disponible` | Reanudación moderada |
| 15:00 – 17:00 | `Lleno` | Hora pico vespertina |
| 17:00 – 20:00 | `Disponible` | Tarde-noche tranquila |
| 20:00 – 21:30 | `Vacío` | Cierre del campus |

---

## 7. Pipeline de procesamiento

Flujo de cada solicitud `/detect` o `/detect-hora`:

1. El frontend envía `GET /detect/<lab_id>` al servidor Flask.
2. Flask determina la hora actual (o la recibida por parámetro) y mapea a una categoría.
3. Se selecciona aleatoriamente una imagen del dataset para ese laboratorio y categoría.
4. **EfficientNet-B0** clasifica el estado global de la imagen → etiqueta principal.
5. **YOLOv8n** detecta cada persona y dibuja bounding boxes con nivel de confianza.
6. Se compone la imagen de salida con overlay de texto (CNN + YOLO + hora) y se guarda en `outputs/`.
7. La API devuelve JSON con `people`, `cnn_label`, `yolo_label`, `estado_final` e `image_url`.
8. El frontend renderiza la tarjeta con la imagen procesada, conteo y badges de estado.

### Ejemplo de respuesta JSON

```json
{
  "people": 12,
  "yolo_label": "Disponible",
  "cnn_label": "Disponible",
  "cnn_conf": 0.934,
  "estado_final": "Disponible",
  "categoria": "Disponible",
  "hora": "14:30",
  "image_url": "http://localhost:5000/output/lab-informatica"
}
```

---

## 8. Páginas del frontend

### `index.html` — Inicio

| Sección | Descripción |
|---|---|
| **LabFinder** | Selecciona un laboratorio y consulta disponibilidad inmediata con imagen procesada por YOLO. |
| **Consulta por horario** | Elige laboratorio + franja horaria para ver cómo estará el espacio según datos históricos. |
| **Grid general** | Estado de todos los laboratorios ordenados por nivel de ocupación, auto-refresh cada 30 s. |
| **Alertas activas** | Laboratorios con ocupación ≥ 80 % o al tope de capacidad. |

### `admin.html` — Dashboard administrativo

| Sección | Descripción |
|---|---|
| **KPIs** | Hora pico, permanencia promedio, lab más usado, lab subutilizado. |
| **Gráfico de líneas** | Ocupación simulada por laboratorio a lo largo del día (7:00–20:00). |
| **Ranking semanal** | Barras horizontales con los laboratorios más usados en la semana. |
| **Permanencia** | Barras verticales con el tiempo promedio de permanencia por laboratorio. |
| **Subutilizados** | Recomendaciones institucionales para labs con bajo uso. |
| **Exportar** | Descarga CSV con los datos del rango de fechas seleccionado, o PDF via impresión. |

---

## 9. Configuración

Toda la configuración vive directamente en `app.py`:

| Variable | Descripción |
|---|---|
| `DATASET_FOLDER` | Ruta a `Lab_aforo/` (relativa a la raíz del proyecto) |
| `MODEL_PATH` | Ruta a `models/cnn_hibrida.pth` |
| `OUTPUT_FOLDER` | Carpeta donde se guardan las imágenes procesadas |
| `DEVICE` | `cuda` si hay GPU, `cpu` en caso contrario (auto-detectado) |

En el frontend, la URL base del backend se configura en `app.js` — **solo se declara aquí**, `horario.js` la reutiliza:

```js
// app.js — única declaración
const API_BASE = 'http://localhost:5000';
```

Cambiar este valor si el servidor Flask corre en otro host o puerto.

---

## 10. Notas técnicas

**`const API_BASE` duplicado**  
`app.js` y `horario.js` comparten el scope global del navegador. `API_BASE` debe declararse únicamente en `app.js` (que carga primero en el HTML). Si `horario.js` lo redeclarase, el navegador lanzaría un `SyntaxError: Identifier 'API_BASE' has already been declared` y abortaría la ejecución completa de `horario.js`, rompiendo tanto el selector de franjas como el botón de consulta.

**Cache-buster en imágenes**  
Las imágenes se sirven añadiendo `?t=<timestamp>` a la URL para forzar que el navegador no muestre la imagen cacheada de una consulta anterior:
```js
const imgSrc = `${data.image_url}?t=${Date.now()}`;
```

**Soporte HEIC**  
Si el dataset contiene imágenes en formato HEIC (dispositivos Apple), se requiere `pillow-heif`. El servidor lo carga automáticamente si está instalado; si no, simplemente omite ese soporte.

**CNN vs YOLO — ¿cuál prevalece?**  
La CNN entrega la etiqueta de estado global (`estado_final`) porque conoce el contexto visual completo del laboratorio. YOLO provee el conteo exacto de personas. Ambos resultados se muestran por separado en la UI para transparencia del sistema.

---

## 11. Créditos

| | |
|---|---|
| **Proyecto** | Procesamiento Digital de Imágenes (PDI) |
| **Institución** | Universidad Autónoma de Occidente — Cali, Colombia |
| **Semestre** | 2026-I |
| **Stack** | YOLOv8 · EfficientNet-B0 · DeepSORT · OpenCV · Flask · HTML/CSS/JS |
| **Licencia** | Académica — uso interno UAO |

---

*© 2025 AforoLAB-UAO*