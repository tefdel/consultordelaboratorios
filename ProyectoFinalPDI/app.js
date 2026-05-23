/* =============================================
   AforoLAB UAO — app.js
   YOLOv8 + Flask
   ============================================= */

// =============================================
// API
// =============================================

const API_BASE = 'http://localhost:5000';

// =============================================
// ESTADO
// =============================================

let labs = LABS_DATA.map(l => ({
  ...l,
  updatedAt: new Date().toISOString()
}));

// =============================================
// SELECT
// =============================================

function populateSelects() {

  const opts = labs.map(l => `
    <option value="${l.id}">
      ${l.icon} ${l.name}
    </option>
  `).join('');

  document.getElementById(
    'lab-select'
  ).innerHTML = opts;
}

// =============================================
// FINDER
// =============================================

async function renderFinder() {

  const id = document.getElementById(
    'lab-select'
  ).value;

  const lab = labs.find(
    l => l.id === id
  );

  const grid = document.getElementById(
    'finder-grid'
  );

  if (!lab) {

    grid.innerHTML = '';

    return;
  }

  try {

    // =========================================
    // BACKEND
    // =========================================

    const response = await fetch(
      `${API_BASE}/detect/${lab.id}`
    );

    const detection = await response.json();

    // =========================================
    // DATOS
    // =========================================

    lab.current = detection.people;

    lab.updatedAt = new Date().toISOString();

    // =========================================
    // STATUS
    // =========================================

    const status = getStatus(
      lab.current,
      lab.capacity
    );

    const pct = Math.round(
      (lab.current / lab.capacity) * 100
    );

    // =========================================
    // IMAGEN
    // =========================================

    const labImage = detection.image_url;

    // =========================================
    // HTML
    // =========================================

    grid.innerHTML = `

      <div class="card" style="padding:0;overflow:hidden">

        <div class="lf-card-header">

          <div class="lf-card-header-left">

            <span class="lf-icon">
              ${lab.icon}
            </span>

            <div>

              <div class="lf-lab-name">
                ${lab.name}
              </div>

              <div class="lf-lab-sub">
                ${lab.building} · ${lab.floor}
              </div>

            </div>

          </div>

          ${renderBadge(status, true)}

        </div>

        <div class="lf-card-body">

          <div class="count-row">

            <div>

              <p class="count-label">
                Personas detectadas
              </p>

              <div class="count-big">

                ${lab.current}

                <span class="count-cap">
                  / ${lab.capacity}
                </span>

              </div>

            </div>

            <div class="count-pct">
              ${pct}%
            </div>

          </div>

          ${renderBar(pct, status)}

          <p class="update-time">

            Actualizado:
            ${fmtTime(lab.updatedAt)}

          </p>

          <p class="update-time">

            Estado:
            <strong>
              ${detection.cnn_label}
            </strong>

          </p>

        </div>

      </div>

      <!-- CAMARA -->

      <div class="cam-card">

        <div class="cam-wrap">

          <img
            src="${labImage}"
            alt="${lab.name}"
          />

          <div class="cam-overlay"></div>

          <div class="cam-live">

            <span class="live-dot"></span>

            EN VIVO

          </div>

          <div class="cam-id">

            📷 CAM-${lab.id.toUpperCase()}

          </div>

          <div class="cam-bottom">

            <p class="cam-bottom-label">

              YOLOv8

            </p>

            <p class="cam-bottom-count">

              ${lab.current} personas

            </p>

          </div>

        </div>

      </div>
    `;

    // =========================================
    // ACTUALIZAR GRID Y ALERTAS
    // =========================================

    renderGrid();

    renderAlerts();

  } catch (error) {

    console.error(error);

    grid.innerHTML = `

      <div class="card">

        <h3>
          Error conectando Flask
        </h3>

      </div>
    `;
  }
}

// =============================================
// GRID
// =============================================

function renderGrid() {

  const sorted = [...labs].sort(
    (a, b) =>
      (b.current / b.capacity) -
      (a.current / a.capacity)
  );

  document.getElementById(
    'labs-grid'
  ).innerHTML = sorted.map(lab => {

    const status = getStatus(
      lab.current,
      lab.capacity
    );

    const pct = Math.round(
      (lab.current / lab.capacity) * 100
    );

    return `

      <article class="lab-card">

        <div class="lab-card-top">

          <div class="lab-card-info">

            <span class="lab-emoji">
              ${lab.icon}
            </span>

            <div>

              <div class="lab-name">
                ${lab.name}
              </div>

              <div class="lab-sub">
                ${lab.building} · ${lab.floor}
              </div>

            </div>

          </div>

          ${renderBadge(status)}

        </div>

        <div class="lab-count-row">

          <div class="lab-count">

            ${lab.current}

            <span>
              /${lab.capacity}
            </span>

          </div>

          <span class="lab-pct">
            ${pct}%
          </span>

        </div>

        ${renderBar(pct, status)}

      </article>
    `;

  }).join('');
}

// =============================================
// ALERTAS
// =============================================

function renderAlerts() {

  const alerts = labs.filter(l => {

    const s = getStatus(
      l.current,
      l.capacity
    );

    return (
      s === 'warning' ||
      s === 'full'
    );
  });

  const container = document.getElementById(
    'alerts-container'
  );

  if (alerts.length === 0) {

    container.innerHTML = `

      <div class="alert-empty">

        ✅ Sin alertas activas

      </div>
    `;

    return;
  }

  container.innerHTML = alerts.map(lab => `

    <div class="alert-item warning">

      <div class="alert-icon warning">

        ⚠️

      </div>

      <div style="flex:1">

        <div class="alert-header">

          <span class="alert-name">
            ${lab.name}
          </span>

          ${renderBadge(
            getStatus(
              lab.current,
              lab.capacity
            )
          )}

        </div>

        <p class="alert-body">

          ${lab.current}
          personas detectadas

        </p>

      </div>

    </div>

  `).join('');
}

// =============================================
// EVENT
// =============================================

document
  .getElementById('lab-select')
  .addEventListener(
    'change',
    renderFinder
  );

// =============================================
// BOOT
// =============================================

populateSelects();

renderFinder();