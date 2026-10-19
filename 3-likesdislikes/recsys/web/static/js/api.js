// Обёртка над HTTP API: единая обработка ошибок проверки ввода (400) и сети.

export class ApiError extends Error {
  constructor(messages) {
    super(messages.join('; '));
    this.messages = messages;
  }
}

async function parse(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(data.errors || [`ошибка сервера: ${response.status}`]);
  return data;
}

export async function getJson(url) {
  return parse(await fetch(url));
}

export async function postJson(url, payload) {
  const options = { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) };
  return parse(await fetch(url, options));
}
