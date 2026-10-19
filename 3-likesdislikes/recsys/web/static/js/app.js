// Контроллер страницы ЛР3: режимы v1/v2/v3, выбор предпочтений, запрос рекомендаций.
import { ApiError, getJson, postJson } from './api.js';
import { Profile } from './profile.js';
import * as view from './views.js';

const $ = (id) => document.getElementById(id);

const MODE_HINTS = {
  v1: 'Выберите один ликёр-затравку — система ранжирует остальные по убыванию близости к нему.',
  v2: 'Отметьте понравившиеся ликёры. Порядок отметок важен: он моделирует время лайков.',
  v3: 'Отметьте лайки и дизлайки — дизлайки снижают оценку объектов, похожих на них больше, чем на лайки.',
};

class App {
  constructor(catalog, options) {
    this.items = catalog.items;
    this.byId = Object.fromEntries(catalog.items.map((item) => [item.id, item]));
    this.branches = catalog.taxonomy.children.map((node) => node.label);
    this.options = options;
    this.state = { mode: 'v2', query: '', branch: null, profile: new Profile() };
  }

  start() {
    this.renderStatic();
    this.bind();
    this.render();
  }

  renderStatic() {
    $('modes').innerHTML = this.options.modes.map((m) => `<button data-mode="${m.key}">${m.key} · ${view.escape(m.title)}</button>`).join('');
    $('ranker').innerHTML = this.optionList(this.options.rankers, this.options.default_ranker);
    $('policy').innerHTML = this.optionList(this.options.policies, this.options.default_policy);
    $('branches').innerHTML = this.branches.map((b) => `<button class="chip" data-branch="${view.escape(b)}">${view.escape(b)}</button>`).join('');
  }

  optionList(list, selected) {
    return list.map((o) => `<option value="${o.key}" ${o.key === selected ? 'selected' : ''}>${view.escape(o.title)}</option>`).join('');
  }

  bind() {
    $('modes').addEventListener('click', (e) => e.target.dataset.mode && this.setMode(e.target.dataset.mode));
    $('branches').addEventListener('click', (e) => e.target.dataset.branch && this.setBranch(e.target.dataset.branch));
    $('query').addEventListener('input', (e) => this.update({ query: e.target.value.trim().toLowerCase() }));
    $('catalog').addEventListener('click', (e) => this.onCardAction(e.target.closest('[data-action]')));
    ['likes', 'dislikes'].forEach((kind) => $(kind).addEventListener('click', (e) => this.onTagRemove(kind, e.target)));
    ['ranker', 'policy'].forEach((id) => $(id).addEventListener('change', () => this.renderHints()));
    $('run').addEventListener('click', () => this.recommend());
    $('clear').addEventListener('click', () => { this.state.profile.clear(); this.render(); });
  }

  update(patch) {
    Object.assign(this.state, patch);
    this.render();
  }

  setMode(mode) {
    const profile = this.state.profile;
    if (mode === 'v1') profile.likes = profile.likes.slice(-1);
    if (mode !== 'v3') profile.dislikes = [];
    this.update({ mode });
  }

  setBranch(branch) {
    this.update({ branch: this.state.branch === branch ? null : branch });
  }

  onCardAction(button) {
    if (!button) return;
    const { action, id } = button.dataset;
    if (action === 'seed') this.state.profile.setSeed(id);
    else this.state.profile.toggle(action === 'like' ? 'likes' : 'dislikes', id);
    this.render();
  }

  onTagRemove(kind, target) {
    if (!target.dataset.remove) return;
    this.state.profile[kind] = this.state.profile[kind].filter((id) => id !== target.dataset.remove);
    this.render();
  }

  visible() {
    const { query, branch } = this.state;
    const text = (item) => `${item.name} ${item.producer} ${item.country} ${item.id}`.toLowerCase();
    return this.items.filter((item) => (!branch || item.taste[0] === branch) && (!query || text(item).includes(query)));
  }

  actionsFor(item) {
    const profile = this.state.profile;
    if (this.state.mode === 'v1') return view.toggle('seed', item.id, profile.has('likes', item.id), 'Затравка');
    const like = view.toggle('like', item.id, profile.has('likes', item.id), '👍 Нравится');
    return this.state.mode === 'v3' ? like + view.toggle('dislike', item.id, profile.has('dislikes', item.id), '👎 Не нравится') : like;
  }

  stateClass(item) {
    const profile = this.state.profile;
    if (profile.has('dislikes', item.id)) return 'is-dislike';
    if (profile.has('likes', item.id)) return this.state.mode === 'v1' ? 'is-seed' : 'is-like';
    return '';
  }

  render() {
    const cards = this.visible().map((item) => view.card(item, { state: this.stateClass(item), actions: this.actionsFor(item) }));
    $('catalog').innerHTML = cards.join('') || '<p class="empty">Ничего не найдено</p>';
    this.renderMode();
    this.renderProfile();
    this.renderHints();
  }

  renderMode() {
    const mode = this.state.mode;
    document.querySelectorAll('#modes button').forEach((b) => b.setAttribute('aria-pressed', b.dataset.mode === mode));
    document.querySelectorAll('#branches .chip').forEach((b) => b.setAttribute('aria-pressed', b.dataset.branch === this.state.branch));
    $('mode-hint').textContent = MODE_HINTS[mode];
    $('ranker-field').classList.toggle('hidden', mode === 'v1');
    $('policy-field').classList.toggle('hidden', mode !== 'v3');
    $('dislikes-block').classList.toggle('hidden', mode !== 'v3');
  }

  renderProfile() {
    const seed = this.state.mode === 'v1';
    $('likes-label').textContent = seed ? 'Затравка' : 'Лайки (в порядке установки)';
    $('likes').innerHTML = this.tags(this.state.profile.likes, seed ? 'seed' : 'like');
    $('dislikes').innerHTML = this.tags(this.state.profile.dislikes, 'dislike');
  }

  tags(ids, kind) {
    const tag = (id) => `<span class="tag ${kind}">${view.escape(this.byId[id].name)}<button data-remove="${id}" aria-label="убрать">×</button></span>`;
    return ids.map(tag).join('') || '<span class="muted">пусто — отметьте ликёры в каталоге</span>';
  }

  renderHints() {
    const find = (list, key) => list.find((o) => o.key === key)?.description || '';
    $('ranker-hint').textContent = find(this.options.rankers, $('ranker').value);
    $('policy-hint').textContent = find(this.options.policies, $('policy').value);
  }

  payload() {
    const { mode, profile } = this.state;
    const base = { mode, likes: profile.likes, dislikes: profile.dislikes, top_n: $('top-n').value };
    return { ...base, ranker: $('ranker').value, policy: $('policy').value };
  }

  async recommend() {
    $('messages').innerHTML = '';
    try {
      const data = await postJson('/api/recommend', this.payload());
      $('results').innerHTML = data.results.map((rec) => view.result(rec)).join('');
    } catch (error) {
      this.showError(error);
    }
  }

  showError(error) {
    $('results').innerHTML = '';
    $('messages').innerHTML = view.errors(error instanceof ApiError ? error.messages : [String(error)]);
  }
}

async function main() {
  const [catalog, options] = await Promise.all([getJson('/api/catalog'), getJson('/api/options')]);
  new App(catalog, options).start();
}

main();
