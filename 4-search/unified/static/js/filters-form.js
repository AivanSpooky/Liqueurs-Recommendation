// Форма фильтров ЛР4: построение по справочникам, чтение в JSON, восстановление из истории.
import { escape } from './views.js';

const FLAG_VALUES = [['any', 'неважно'], ['yes', 'да'], ['no', 'нет']];
const RANGE_KEYS = ['abv', 'sugar', 'volume'];

function checkbox(name, value, label) {
  return `<label><input type="checkbox" name="${name}" value="${escape(value)}"> ${escape(label)}</label>`;
}

function treeNode(node) {
  const value = escape(JSON.stringify(node.path));
  const box = `<input type="checkbox" name="taste" value="${value}"> ${escape(node.label)} <span class="count">${node.items.length}</span>`;
  if (!node.children.length) return `<label class="leaf">${box}</label>`;
  return `<details><summary><label>${box}</label></summary>${node.children.map(treeNode).join('')}</details>`;
}

export class FiltersForm {
  constructor(form, options, taxonomy) {
    this.form = form;
    this.build(options, taxonomy);
  }

  build(options, taxonomy) {
    this.form.querySelector('#f-taste').innerHTML = taxonomy.children.map(treeNode).join('');
    this.form.querySelector('#f-sugar-classes').innerHTML = options.sugar_classes.map((c) => checkbox('sugar_classes', c, c)).join('');
    this.form.querySelector('#f-countries').innerHTML = options.countries.map((c) => checkbox('countries', c, c)).join('');
    this.form.querySelector('#f-producers').innerHTML = options.producers.map((c) => checkbox('producers', c, c)).join('');
    this.buildRanges(options.ranges);
  }

  buildRanges(ranges) {
    this.form.querySelectorAll('[data-range]').forEach((box) => {
      const { min, max } = ranges[box.dataset.range];
      box.innerHTML = `<input class="input" name="${box.dataset.range}-min" placeholder="от ${min}" inputmode="decimal">
        <input class="input" name="${box.dataset.range}-max" placeholder="до ${max}" inputmode="decimal">`;
    });
    this.form.querySelectorAll('[data-flag]').forEach((box) => { box.innerHTML = this.flagButtons(box.dataset.flag); });
  }

  flagButtons(flag) {
    return FLAG_VALUES.map(([value, label]) => `<button type="button" data-flag-value="${value}" aria-pressed="${value === 'any'}">${label}</button>`).join('');
  }

  bindFlags() {
    this.form.addEventListener('click', (event) => {
      const button = event.target.closest('[data-flag-value]');
      if (button) this.setFlag(button.parentElement.dataset.flag, button.dataset.flagValue);
    });
  }

  setFlag(flag, value) {
    this.form.querySelectorAll(`[data-flag="${flag}"] button`).forEach((b) => b.setAttribute('aria-pressed', b.dataset.flagValue === value));
  }

  checked(name) {
    return [...this.form.querySelectorAll(`input[name="${name}"]:checked`)].map((input) => input.value);
  }

  read() {
    const value = (name) => this.form.elements[name].value.trim();
    const ranges = Object.fromEntries(RANGE_KEYS.map((key) => [key, { min: value(`${key}-min`), max: value(`${key}-max`) }]));
    const flags = Object.fromEntries(['bitter', 'wood'].map((f) => [f, this.form.querySelector(`[data-flag="${f}"] [aria-pressed="true"]`).dataset.flagValue]));
    const lists = { countries: this.checked('countries'), producers: this.checked('producers'), sugar_classes: this.checked('sugar_classes') };
    return { name: value('name'), taste: this.checked('taste').map((v) => JSON.parse(v)), ...ranges, ...flags, ...lists };
  }

  fill(filters = {}) {
    this.form.reset();
    this.form.elements.name.value = filters.name || '';
    RANGE_KEYS.forEach((key) => ['min', 'max'].forEach((side) => { this.form.elements[`${key}-${side}`].value = filters[key]?.[side] ?? ''; }));
    ['bitter', 'wood'].forEach((flag) => this.setFlag(flag, filters[flag] || 'any'));
    this.fillChecks(filters);
  }

  fillChecks(filters) {
    const wanted = { taste: (filters.taste || []).map((p) => JSON.stringify(p)), countries: filters.countries || [],
      producers: filters.producers || [], sugar_classes: filters.sugar_classes || [] };
    this.form.querySelectorAll('input[type="checkbox"]').forEach((input) => { input.checked = (wanted[input.name] || []).includes(input.value); });
  }
}
