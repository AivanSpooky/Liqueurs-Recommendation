// Профиль пользователя на клиенте: упорядоченные лайки (порядок = время) и дизлайки.

export class Profile {
  constructor(likes = [], dislikes = []) {
    this.likes = [...likes];
    this.dislikes = [...dislikes];
  }

  has(kind, id) {
    return this[kind].includes(id);
  }

  toggle(kind, id) {
    const other = kind === 'likes' ? 'dislikes' : 'likes';
    this[other] = this[other].filter((x) => x !== id);
    this[kind] = this.has(kind, id) ? this[kind].filter((x) => x !== id) : [...this[kind], id];
  }

  setSeed(id) {
    this.likes = [id];
    this.dislikes = [];
  }

  clear() {
    this.likes = [];
    this.dislikes = [];
  }
}
