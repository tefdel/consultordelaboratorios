/* =============================================
   AforoLAB UAO — horario.js
   Consulta por franja horaria
   ============================================= */

// API_BASE ya está declarado en app.js (cargado antes)
// NO redeclarar aquí para evitar el error de const duplicada

// =============================================
// FRANJAS (espejo del backend)
// =============================================

const FRANJAS = [
  { desde: 6.0,  hasta: 7.0,  label: 'Laboratorio vacío   (06:00 – 07:00)', categoria: 'Vacio'      },
  { desde: 7.0,  hasta: 8.5,  label: 'Hora más suave       (07:00 – 08:30)', categoria: 'Disponible' },
  { desde: 8.5,  hasta: 12.0, label: 'Hora pico            (08:30 – 12:00)', categoria: 'Lleno'      },
  { desde: 12.0, hasta: 13.0, label: 'Laboratorio vacío   (12:00 – 13:00)', categoria: 'Vacio'      },
  { desde: 13.0, hasta: 15.0, label: 'Hora más suave       (13:00 – 15:00)', categoria: 'Disponible' },
  { desde: 15.0, hasta: 17.0, label: 'Hora pico            (15:00 – 17:00)', categoria: 'Lleno'      },
  { desde: 17.0, hasta: 20.0, label: 'Hora más suave       (17:00 – 20:00)', categoria: 'Disponible' },
  { desde: 20.0, hasta: 21.5, label: 'Laboratorio vacío   (20:00 – 21:30)', categoria: 'Vacio'      },
];

const CATEGORIA_BADGE = {
  Vacio:      { text: 'Vacío',      cls: 'empty'     },
  Disponible: { text: 'Disponible', cls: 'available'  },
  Lleno:      { text: 'Lleno',      cls: 'full'       },
};

// =============================================
// POBLAR SELECTS AL CARGAR
// =============================================

function initHorario() {

  const labSel = document.getElementById('hs-lab');
  if (!labSel) return;

  // Limpiar antes de poblar (evita duplicados si se llama más de una vez)
  labSel.innerHTML = '';

  LABS_DATA.forEach(l => {
    const opt       = document.createElement('option');
    opt.value       = l.id;
    opt.textContent = `${l.icon} ${l.name}`;
    labSel.appendChild(opt);
  });

  // Franjas
  const franjaSel = document.getElementById('hs-franja');
  franjaSel.innerHTML = '';

  FRANJAS.forEach((f) => {
    const opt       = document.createElement('option');
    opt.value       = f.desde;        // hora decimal → backend
    opt.textContent = f.label;
    franjaSel.appendChild(opt);
  });

  // Seleccionar la franja actual por defecto
  const ahora       = new Date();
  const horaActual  = ahora.getHours() + ahora.getMinutes() / 60;
  const franjaActual = FRANJAS.findIndex(
    f => horaActual >= f.desde && horaActual < f.hasta
  );
  if (franjaActual >= 0) franjaSel.selectedIndex = franjaActual;
}

// =============================================
// CONSULTAR HORARIO
// =============================================

async function consultarHorario() {

  const labId = document.getElementById('hs-lab').value;
  const hora  = document.getElementById('hs-franja').value;

  const resultDiv = document.getElementById('hs-result');
  resultDiv.innerHTML = '<p class="hs-loading">⏳ Procesando imagen con YOLOv8...</p>';

  try {
    const res  = await fetch(`${API_BASE}/detect-hora/${labId}?hora=${hora}`);
    const data = await res.json();

    if (data.error) {
      resultDiv.innerHTML = `<div class="card hs-error">❌ ${data.error}</div>`;
      return;
    }

    const lab    = LABS_DATA.find(l => l.id === labId);
    const badge  = CATEGORIA_BADGE[data.categoria] || CATEGORIA_BADGE['Vacio'];
    const franja = FRANJAS.find(f => String(f.desde) === String(hora));

    // Cache-buster para forzar recarga de imagen
    const imgSrc = `${data.image_url}?t=${Date.now()}`;

    resultDiv.innerHTML = `
      <div class="hs-card">

        <!-- INFO -->
        <div class="hs-info">

          <div class="hs-info-top">
            <span class="hs-lab-icon">${lab ? lab.icon : '🏫'}</span>
            <div>
              <h3 class="hs-lab-name">${lab ? lab.name : labId}</h3>
              <p class="hs-lab-sub">${lab ? lab.building + ' · ' + lab.floor : ''}</p>
            </div>
          </div>

          <div class="hs-meta">
            <div class="hs-meta-row">
              <span class="hs-meta-label">Franja consultada</span>
              <span class="hs-meta-value">${franja ? franja.label.trim() : hora}</span>
            </div>
            <div class="hs-meta-row">
              <span class="hs-meta-label">Categoría esperada</span>
              <span class="badge ${badge.cls}">${badge.text}</span>
            </div>
            <div class="hs-meta-row">
              <span class="hs-meta-label">Personas detectadas</span>
              <span class="hs-people">${data.people}</span>
            </div>
            <div class="hs-meta-row">
              <span class="hs-meta-label">Estado YOLO</span>
              <span class="badge ${CATEGORIA_BADGE[data.categoria]?.cls || 'empty'}">
                ${data.estado_yolo || data.yolo_label}
              </span>
            </div>
          </div>

          <div class="hs-tip">
            💡 La imagen es una muestra representativa de ese laboratorio
            en la franja <strong>${franja ? franja.label.split('(')[0].trim() : ''}</strong>.
          </div>

        </div>

        <!-- IMAGEN -->
        <div class="hs-img-wrap">
          <img
            src="${imgSrc}"
            alt="${lab ? lab.name : labId}"
            class="hs-img"
            onload="this.classList.add('loaded')"
          />
          <div class="cam-live" style="top:12px;left:12px">
            <span class="live-dot"></span> YOLOv8
          </div>
          <div class="cam-bottom">
            <p class="cam-bottom-label">Conteo automático</p>
            <p class="cam-bottom-count">${data.people} personas</p>
          </div>
        </div>

      </div>
    `;

  } catch (err) {
    resultDiv.innerHTML = `
      <div class="card hs-error">
        ❌ No se pudo conectar con el servidor Flask (localhost:5000).<br>
        <small>${err.message}</small>
      </div>`;
  }
}

// =============================================
// BOOT
// =============================================

document.addEventListener('DOMContentLoaded', () => {
  initHorario();
  document.getElementById('hs-btn')
    .addEventListener('click', consultarHorario);
});