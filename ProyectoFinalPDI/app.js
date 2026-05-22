/* =============================================
   AforoLAB UAO — app.js
   Lógica de la página principal (index.html)
   ============================================= */

/* Estado reactivo: copia mutable de los datos base */
let labs = LABS_DATA.map(l => ({ ...l, updatedAt: new Date().toISOString() }));
let reports = [];

/* ─── Inicializar selectores ─── */
function populateSelects() {
  const opts = labs.map(l =>
    `<option value="${l.id}">${l.icon} ${l.name}</option>`
  ).join('');
  document.getElementById('lab-select').innerHTML = opts;
  document.getElementById('r-lab').innerHTML =
    '<option value="">Selecciona un laboratorio</option>' + opts;
}

/* ─── LABFINDER ─── */
function renderFinder() {
  const id  = document.getElementById('lab-select').value;
  const lab = labs.find(l => l.id === id);
  const grid = document.getElementById('finder-grid');
  if (!lab) { grid.innerHTML = ''; return; }

  const status = getStatus(lab.current, lab.capacity);
  const pct    = Math.round((lab.current / lab.capacity) * 100);

  grid.innerHTML = `
    <!-- Tarjeta de datos en tiempo real -->
    <div class="card" style="padding:0;overflow:hidden">
      <div class="lf-card-header">
        <div class="lf-card-header-left">
          <span class="lf-icon">${lab.icon}</span>
          <div>
            <div class="lf-lab-name">${lab.name}</div>
            <div class="lf-lab-sub">${lab.building} · ${lab.floor}</div>
          </div>
        </div>
        ${renderBadge(status, true)}
      </div>
      <div class="lf-card-body">
        <div class="count-row">
          <div>
            <p class="count-label">Personas detectadas</p>
            <div class="count-big">${lab.current}<span class="count-cap"> / ${lab.capacity}</span></div>
          </div>
          <div class="count-pct">${pct}%</div>
        </div>
        ${renderBar(pct, status)}
        <p class="update-time">Actualizado: ${fmtTime(lab.updatedAt)}</p>
      </div>
    </div>

    <!-- Tarjeta de cámara + consulta histórica -->
    <div class="cam-card">
      <div class="cam-wrap">
        <img src="https://picsum.photos/seed/${lab.id}/800/450" alt="Cámara en vivo de ${lab.name}" />
        <div class="cam-overlay"></div>
        <div class="cam-live"><span class="live-dot"></span> EN VIVO</div>
        <div class="cam-id">📷 CAM-${lab.id.toUpperCase()}</div>
        <div class="cam-bottom">
          <p class="cam-bottom-label">Detección YOLOv8</p>
          <p class="cam-bottom-count">${lab.current} personas</p>
        </div>
        <span class="cam-bottom-time">${fmtTime(lab.updatedAt)}</span>
      </div>
      <div class="hist-section">
        <div class="hist-title">
          <span>🕐</span>
          <strong>Consultar a una hora específica</strong>
        </div>
        <p class="section-sub">Revisa cuántas personas había en este laboratorio en una hora del día.</p>
        <div class="hist-row">
          <div>
            <label for="hist-time">Hora</label>
            <input type="time" id="hist-time" />
          </div>
          <button class="btn btn-primary" onclick="queryHistorical('${lab.id}', ${lab.capacity})">
            Consultar
          </button>
        </div>
        <div id="hist-result"></div>
      </div>
    </div>
  `;
}

function queryHistorical(labId, capacity) {
  const t = document.getElementById('hist-time').value;
  if (!t) return;
  const [hh, mm] = t.split(':').map(Number);
  const count  = simulateHistorical(labId, capacity, hh, mm);
  const status = getStatus(count, capacity);
  const pct    = Math.round((count / capacity) * 100);

  document.getElementById('hist-result').innerHTML = `
    <div class="hist-result">
      <p style="font-size:12px;color:var(--text-muted);margin-bottom:4px">
        A las <strong style="color:var(--text)">${t}</strong> había
      </p>
      <div class="hist-count-row">
        <div class="hist-count">${count}<span> / ${capacity}</span></div>
        ${renderBadge(status)}
      </div>
      ${renderBar(pct, status)}
    </div>
  `;
}

/* Listener del selector */
document.getElementById('lab-select').addEventListener('change', renderFinder);

/* ─── LABS GRID ─── */
function renderGrid() {
  const sorted = [...labs].sort((a, b) =>
    (b.current / b.capacity) - (a.current / a.capacity)
  );
  document.getElementById('labs-grid').innerHTML = sorted.map(lab => {
    const status = getStatus(lab.current, lab.capacity);
    const pct    = Math.round((lab.current / lab.capacity) * 100);
    return `
      <article class="lab-card">
        <div class="lab-card-top">
          <div class="lab-card-info">
            <span class="lab-emoji">${lab.icon}</span>
            <div>
              <div class="lab-name">${lab.name}</div>
              <div class="lab-sub">${lab.building} · ${lab.floor}</div>
            </div>
          </div>
          ${renderBadge(status)}
        </div>
        <div class="lab-count-row">
          <div class="lab-count">${lab.current}<span>/${lab.capacity}</span></div>
          <span class="lab-pct">${pct}%</span>
        </div>
        ${renderBar(pct, status)}
        <p class="lab-time">Actualizado ${fmtTime(lab.updatedAt)}</p>
      </article>
    `;
  }).join('');
}

/* ─── ALERTS ─── */
function renderAlerts() {
  const alerts = labs
    .filter(l => {
      const s = getStatus(l.current, l.capacity);
      return s === 'warning' || s === 'full';
    })
    .map(l => ({
      lab: l,
      critical: l.current > l.capacity || (l.current / l.capacity) >= 0.9,
    }));

  const container = document.getElementById('alerts-container');

  if (alerts.length === 0) {
    container.innerHTML = `
      <div class="alert-empty">
        ✅ Sin alertas activas. Todos los laboratorios están dentro del aforo permitido.
      </div>`;
    return;
  }

  container.innerHTML = alerts.map(({ lab, critical }) => `
    <div class="alert-item ${critical ? 'critical' : 'warning'}">
      <div class="alert-icon ${critical ? 'critical' : 'warning'}">
        ${critical ? '🔴' : '⚠️'}
      </div>
      <div style="flex:1">
        <div class="alert-header">
          <span class="alert-name">${lab.name}</span>
          ${renderBadge(critical ? 'full' : 'warning')}
        </div>
        <p class="alert-body">
          <strong>${lab.current}</strong> personas detectadas vs. límite de <strong>${lab.capacity}</strong>
          ${lab.current > lab.capacity
            ? `<span class="alert-sobrecupo">(sobrecupo +${lab.current - lab.capacity})</span>`
            : ''}
        </p>
        <p class="alert-meta">${lab.building} · ${lab.floor} · ${fmtTime(lab.updatedAt)}</p>
      </div>
    </div>
  `).join('');
}

/* ─── REPORT ISSUE ─── */
const TYPE_LABEL = {
  'conteo-alto': 'Conteo alto',
  'conteo-bajo': 'Conteo bajo',
  'camara':      'Cámara',
  'otro':        'Otro',
};

document.getElementById('r-lab').addEventListener('change', function () {
  const lab = labs.find(l => l.id === this.value);
  document.getElementById('r-lab-info').textContent = lab
    ? `Conteo actual del sistema: ${lab.current} / ${lab.capacity}`
    : '';
});

document.getElementById('submit-report').addEventListener('click', function () {
  const labId = document.getElementById('r-lab').value;
  const type  = document.getElementById('r-type').value;
  const desc  = document.getElementById('r-desc').value.trim();
  if (!labId || !type || !desc) return;

  const lab   = labs.find(l => l.id === labId);
  const count = document.getElementById('r-count').value;
  const email = document.getElementById('r-email').value;

  reports.unshift({
    id: Date.now(),
    labName: lab.name,
    type,
    count,
    systemCount: lab.current,
    desc,
    email,
    createdAt: new Date().toISOString(),
  });

  /* Reset form */
  ['r-lab', 'r-type'].forEach(id => document.getElementById(id).value = '');
  ['r-count', 'r-email', 'r-desc'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('r-lab-info').textContent = '';

  /* Success message */
  const msg = document.getElementById('r-success');
  msg.style.display = 'flex';
  setTimeout(() => msg.style.display = 'none', 4000);

  renderReports();
});

function renderReports() {
  document.getElementById('report-count-title').textContent =
    `Reportes recientes (${reports.length})`;

  if (reports.length === 0) {
    document.getElementById('report-list').innerHTML =
      '<p class="empty-msg">Aún no hay reportes registrados en esta sesión.</p>';
    return;
  }

  document.getElementById('report-list').innerHTML = `
    <div class="report-list">
      ${reports.map(r => `
        <div class="report-item">
          <div class="report-top">
            <span class="report-lab-name">${r.labName}</span>
            <span class="report-tag">${TYPE_LABEL[r.type] || r.type}</span>
          </div>
          <p style="font-size:11px;color:var(--text-muted);margin-bottom:4px">
            Sistema: ${r.systemCount}${r.count ? ` · Real: ${r.count}` : ''}
          </p>
          <p style="font-size:12px;color:var(--text)">${r.desc}</p>
          <p style="font-size:10px;color:var(--text-muted);margin-top:6px">
            ${new Date(r.createdAt).toLocaleString('es-CO')}
          </p>
        </div>
      `).join('')}
    </div>
  `;
}

/* ─── SIMULATE TICK (auto-refresh cada 30 s) ─── */
function simulateTick() {
  labs = labs.map(l => {
    const delta = Math.floor(Math.random() * 5) - 2;
    const next  = Math.max(0, Math.min(l.capacity + 2, l.current + delta));
    return { ...l, current: next, updatedAt: new Date().toISOString() };
  });
  renderGrid();
  renderAlerts();
  renderFinder();
}

/* ─── BOOT ─── */
populateSelects();
renderFinder();
renderGrid();
renderAlerts();
renderReports();
setInterval(simulateTick, 30_000);
