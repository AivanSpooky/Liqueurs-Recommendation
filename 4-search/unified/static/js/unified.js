// Контроллер объединённой системы: поиск (ЛР4) ⇄ рекомендации (ЛР3), профиль и история (РК1).
import { ApiError, getJson, postJson } from './api.js';
import { FiltersForm } from './filters-form.js';
import * as view from './views.js';

const $ = (id) => document.getElementById(id);
const KIND_LABELS = { search: 'поиск', refine: 'уточнение', recommend: 'рекомендации' };

class UnifiedApp {
  constructor(catalog, options, filterOptions) {
    this.byId = Object.fromEntries(catalog.items.map((item) => [item.id, item]));
    this.options = options;
    this.form = new FiltersForm($('filters'), filterOptions, catalog.taxonomy);
    this.state = { profile: { likes: [], dislikes: [] }, history: [], current: null };
  }

  async start() {
    $('ranker').innerHTML = this.optionList(this.options.rankers, this.options.default_ranker);
    $('policy').innerHTML = this.optionList(this.options.policies, this.options.default_policy);
    this.bind();
    await this.call(() => getJson('/api/state'));
  }

  optionList(list, selected) {
    return list.map((o) => `<option value="${o.key}" title="${view.escape(o.description)}" ${o.key === selected ? 'selected' : ''}>${view.escape(o.title)}</option>`).join('');
  }

  bind() {
    this.form.bindFlags();
    $('filters').addEventListener('submit', (e) => { e.preventDefault(); this.operation('search'); });
    $('do-refine').addEventListener('click', () => this.operation('refine'));
    $('do-clear').addEventListener('click', () => setTimeout(() => this.form.fill({}), 0));
    $('do-recommend').addEventListener('click', () => this.recommend());
    this.bindSide();
  }

  bindSide() {
    $('rows').addEventListener('click', (e) => this.onRate(e.target.closest('[data-action]')));
    ['likes', 'dislikes'].forEach((id) => $(id).addEventListener('click', (e) => this.onRemove(e.target)));
    $('history').addEventListener('click', (e) => this.onHistory(e.target.closest('[data-step]')));
    $('do-restart').addEventListener('click', () => this.post('/api/reset', { keep_profile: true }));
    $('do-reset').addEventListener('click', () => this.post('/api/reset', { keep_profile: false }));
  }

  operation(kind) {
    return this.post(`/api/${kind}`, { filters: this.form.read() });
  }

  recommend() {
    const scope = document.querySelector('input[name="scope"]:checked').value;
    const useFilters = $('use-filters').checked;
    const settings = { top_n: $('top-n').value, ranker: $('ranker').value, policy: $('policy').value, scope };
    return this.post('/api/recommend', { ...settings, use_filters: useFilters, filters: useFilters ? this.form.read() : {} });
  }

  onRate(button) {
    if (button) this.post('/api/profile', { action: button.dataset.action, id: button.dataset.id }, false);
  }

  onRemove(target) {
    if (target.dataset.remove) this.post('/api/profile', { action: 'remove', id: target.dataset.remove }, false);
  }

  async onHistory(button) {
    if (!button) return;
    await this.post('/api/history', { index: Number(button.dataset.step) });
    this.form.fill(this.state.current?.filters || {});
  }

  post(url, payload, clearMessages = true) {
    return this.call(() => postJson(url, payload), clearMessages);
  }

  async call(request, clearMessages = true) {
    if (clearMessages) $('messages').innerHTML = '';
    try {
      this.render(await request());
    } catch (error) {
      $('messages').innerHTML = view.errors(error instanceof ApiError ? error.messages : [String(error)]);
    }
  }

  render(state) {
    this.state = state;
    this.renderProfile(state.profile);
    this.renderHistory(state.history, state.current);
    this.renderStep(state.current);
  }

  renderProfile(profile) {
    const tag = (kind) => (id) => `<span class="tag ${kind}">${view.escape(this.byId[id].name)}<button data-remove="${id}" aria-label="убрать">×</button></span>`;
    $('likes').innerHTML = profile.likes.map(tag('like')).join('') || '<span class="muted">отметьте 👍 в выдаче</span>';
    $('dislikes').innerHTML = profile.dislikes.map(tag('dislike')).join('') || '<span class="muted">—</span>';
  }

  renderHistory(history, current) {
    const item = (s) => `<li class="${current && s.index === current.index ? 'current' : ''} ${s.parent !== null ? 'child' : ''}">
      <button data-step="${s.index}"><span class="num">${s.index + 1}</span>
      <span><span class="kind">${KIND_LABELS[s.kind]}${s.exact ? '' : ' · приближённо'}</span>${view.escape(s.title)}</span>
      <span class="cnt">${s.count}</span></button></li>`;
    $('history').innerHTML = history.map(item).join('') || '<li class="muted">пока пусто</li>';
  }

  renderStep(step) {
    $('step-title').textContent = step ? `Шаг ${step.index + 1}. ${step.title}` : 'Начните с поиска или запросите рекомендации';
    $('notice').innerHTML = step && !step.exact ? this.notice(step) : '';
    $('rows').innerHTML = step ? step.rows.map((row) => this.rowHtml(row)).join('') || '<p class="empty">Ничего не найдено</p>' : this.catalogHint();
  }

  catalogHint() {
    return Object.values(this.byId).map((item) => view.card(item, { state: this.stateClass(item.id), actions: this.actions(item.id) })).join('');
  }

  notice(step) {
    const changes = step.advice ? `<div class="advice">Чтобы получить точные совпадения (${step.advice.found}), можно ослабить фильтры:
      <ul>${step.advice.changes.map((c) => `<li>${view.escape(c)}</li>`).join('')}</ul></div>` : '';
    return `<div class="notice"><b>${view.escape(step.message)}</b>${changes}</div>`;
  }

  rowHtml(row) {
    const fit = row.exact ? '' : `<div class="fit">соответствие фильтрам ${Math.round(row.fit * 100)} %</div>
      <div class="unmet">${row.unmet.map((u) => `<span>${view.escape(u.filter)} · ${Math.round(u.degree * 100)} %</span>`).join('')}</div>`;
    const why = row.explanation ? `<div class="relevance">релевантность ${view.number(row.relevance, 3)} ${view.why(row.explanation)}</div>` : '';
    return view.card(row.item, { state: this.stateClass(row.item.id), actions: this.actions(row.item.id), extra: fit + why });
  }

  stateClass(id) {
    if (this.state.profile.dislikes.includes(id)) return 'is-dislike';
    return this.state.profile.likes.includes(id) ? 'is-like' : '';
  }

  actions(id) {
    const { likes, dislikes } = this.state.profile;
    return view.toggle('like', id, likes.includes(id), '👍 Нравится') + view.toggle('dislike', id, dislikes.includes(id), '👎 Не нравится');
  }
}

async function main() {
  const [catalog, options, filters] = await Promise.all(['/api/catalog', '/api/options', '/api/filters'].map(getJson));
  await new UnifiedApp(catalog, options, filters).start();
}

main();
