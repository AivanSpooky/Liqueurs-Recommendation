// Шаблоны разметки: карточка ликёра, элемент выдачи, ошибки. Общие для ЛР3 и ЛР4.

const ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

export function escape(text) {
  return String(text ?? '').replace(/[&<>"']/g, (ch) => ESCAPES[ch]);
}

export function number(value, digits = 2) {
  return Number(value).toFixed(digits).replace('.', ',');
}

function facts(item) {
  const flags = [item.bitter ? 'горький' : null, item.wood_contact ? 'дерево' : null].filter(Boolean);
  const values = [`${number(item.abv, 1)} %`, `${item.sugar} г/л`, `${number(item.volume, 2)} л`, item.sugar_class, ...flags];
  return values.map((value) => `<span class="fact">${escape(value)}</span>`).join('');
}

export function card(item, { state = '', actions = '', extra = '' } = {}) {
  return `<article class="card ${state}" data-id="${escape(item.id)}">
    <div class="title"><b>${escape(item.name)}</b><span class="id">${escape(item.id)}</span></div>
    <div class="meta">${escape(item.producer)} · ${escape(item.country)}</div>
    <div class="taste">${item.taste.map(escape).join(' › ')}</div>
    <div class="facts">${facts(item)}</div>${extra}
    <div class="actions">${actions}</div>
  </article>`;
}

export function toggle(kind, id, pressed, label) {
  return `<button class="btn ${kind}" data-action="${kind}" data-id="${escape(id)}" aria-pressed="${pressed}">${label}</button>`;
}

function parts(contributions) {
  const rows = contributions.map((p) => `<div class="part"><span>${escape(p.label)}</span>
      <div class="bar"><span style="width:${Math.min(100, p.value / 0.35 * 100)}%"></span></div>
      <span class="num">${number(p.value, 3)}</span></div>`);
  return rows.length ? `<details class="parts"><summary>вклад признаков в близость</summary>${rows.join('')}</details>` : '';
}

function blameText(rec) {
  const name = `«${escape(rec.blame.name)}»`;
  return rec.penalty >= 0.001 ? `штраф −${number(rec.penalty, 3)}: напоминает дизлайк ${name}` : `ближайший дизлайк: ${name}`;
}

export function why(rec) {
  const anchor = rec.anchor ? `похож на <b>${escape(rec.anchor.name)}</b>` : '';
  const group = rec.group !== null && rec.group !== undefined ? `<span class="badge">интерес ${rec.group + 1}</span>` : '';
  const blame = rec.blame && (rec.penalty >= 0.001 || !rec.anchor) ? ` <span class="penalty">${blameText(rec)}</span>` : '';
  return `<div class="why">${anchor}${group}${blame}</div>`;
}

export function result(rec, { extra = '', scoreLabel = 'релевантность' } = {}) {
  const width = Math.max(0, Math.min(100, rec.score * 100));
  return `<article class="result" data-id="${escape(rec.item.id)}">
    <div class="head"><span class="rank">${rec.rank}</span>
      <div><b>${escape(rec.item.name)}</b> <span class="muted">${escape(rec.item.taste.join(' › '))}</span></div>
      <span class="score" title="${scoreLabel}">${number(rec.score, 3)}</span></div>
    <div class="bar"><span style="width:${width}%"></span></div>
    ${why(rec)}${parts(rec.contributions || [])}${extra}
  </article>`;
}

export function errors(messages) {
  return `<div class="errors" role="alert"><b>Проверьте ввод:</b><ul>${messages.map((m) => `<li>${escape(m)}</li>`).join('')}</ul></div>`;
}
