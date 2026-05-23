/* =============================================
   AforoLAB UAO — data.js
   Datos de laboratorios y funciones compartidas
   ============================================= */

const LABS_DATA = [
  { id: 'lab-fisica',     name: 'Lab. Física',                 icon: '🔭', building: 'Bloque 6', floor: 'Piso 1', capacity: 22, current: 16 },
  { id: 'lab-grafica',    name: 'Grafica Lab',                 icon: '🎨', building: 'Bloque 5', floor: 'Piso 1', capacity: 20, current: 0  },
  { id: 'lab-informatica',name: 'Laboratorios Informática',    icon: '💻', building: 'Bloque 9', floor: 'Piso 2', capacity: 65, current: 40 },
  { id: 'lab-ingenieria', name: 'Lab. Ingeniería',             icon: '⚙️', building: 'Bloque 8', floor: 'Piso 2', capacity: 32, current: 31 },
  { id: 'zonas-estudio',  name: 'Zonas de Estudio',            icon: '📚', building: 'Bloque 1', floor: 'Piso 1', capacity: 50, current: 25 },
];

/* Colores para cada estado */
const STATUS_COLOR = {
  empty:     '#9CA3AF',
  available: '#059669',
  warning:   '#D97706',
  full:      '#C8102E',
};

const STATUS_LABEL = {
  empty:     'Disponible',
  available: 'Disponible',
  warning:   'Casi lleno',
  full:      'Lleno',
};

/**
 * Determina el estado de un laboratorio según ocupación actual y capacidad.
 * @param {number} current
 * @param {number} capacity
 * @returns {'empty'|'available'|'warning'|'full'}
 */
function getStatus(current, capacity) {
  if (current === 0) return 'empty';
  const ratio = current / capacity;
  if (ratio >= 1)    return 'full';
  if (ratio >= 0.8)  return 'warning';
  return 'available';
}

/**
 * Genera el HTML de un badge de estado.
 * @param {'empty'|'available'|'warning'|'full'} status
 * @param {boolean} [large=false]
 * @returns {string}
 */
function renderBadge(status, large = false) {
  return `<span class="badge ${status}${large ? ' lg' : ''}">
    <span class="bdot"></span>${STATUS_LABEL[status]}
  </span>`;
}

/**
 * Genera el HTML de una barra de ocupación.
 * @param {number} pct  - Porcentaje (0-100)
 * @param {'empty'|'available'|'warning'|'full'} status
 * @returns {string}
 */
function renderBar(pct, status) {
  return `<div class="bar-track">
    <div class="bar-fill" style="width:${Math.min(100, pct)}%;background:${STATUS_COLOR[status]}"></div>
  </div>`;
}

/**
 * Formatea un ISO timestamp a hora local colombiana.
 * @param {string} iso
 * @returns {string}
 */
function fmtTime(iso) {
  return new Date(iso).toLocaleTimeString('es-CO');
}

/**
 * Simula el conteo histórico de un laboratorio a una hora dada.
 * Algoritmo determinista para reproducibilidad.
 */
function simulateHistorical(labId, capacity, hour, minute) {
  let seed = 0;
  const key = `${labId}-${hour}-${Math.floor(minute / 10)}`;
  for (let i = 0; i < key.length; i++) {
    seed = (seed * 31 + key.charCodeAt(i)) >>> 0;
  }
  const rand = (seed % 1000) / 1000;
  let factor = 0.1;
  if      (hour >= 7  && hour <= 9)  factor = 0.5 + rand * 0.3;
  else if (hour >= 10 && hour <= 12) factor = 0.75 + rand * 0.25;
  else if (hour >= 13 && hour <= 14) factor = 0.4 + rand * 0.3;
  else if (hour >= 15 && hour <= 18) factor = 0.7 + rand * 0.3;
  else if (hour >= 19 && hour <= 21) factor = 0.3 + rand * 0.3;
  else                               factor = rand * 0.15;
  return Math.min(capacity + 2, Math.round(capacity * factor));
}
