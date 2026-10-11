const API_BASE = window.__API_BASE__ || 'http://localhost:8000';
const STORAGE_KEY = 'vendas-api-token';

const state = {
  token: localStorage.getItem(STORAGE_KEY) || '',
  conversations: [],
  selectedId: null,
  filters: {
    status: '',
    canal: '',
    cliente_id: '',
  },
};

const els = {
  loginPanel: document.getElementById('login-panel'),
  filtersPanel: document.getElementById('filters-panel'),
  loginForm: document.getElementById('login-form'),
  dashboard: document.getElementById('dashboard'),
  loading: document.getElementById('loading'),
  conversationList: document.getElementById('conversation-list'),
  conversationDetail: document.getElementById('conversation-detail'),
  statusFilter: document.getElementById('status-filter'),
  canalFilter: document.getElementById('canal-filter'),
  refreshButton: document.getElementById('refresh-button'),
  logoutButton: document.getElementById('logout-button'),
};

function fetchJson(url, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (state.token) {
    headers.Authorization = `Bearer ${state.token}`;
  }

  return fetch(`${API_BASE}${url}`, {
    ...options,
    headers,
  }).then(async (response) => {
    const text = await response.text();
    const payload = text ? JSON.parse(text) : null;

    if (!response.ok) {
      throw new Error(payload?.detail || 'Erro na requisição');
    }

    return payload;
  });
}

function updateAuthUI() {
  const isLogged = Boolean(state.token);
  els.loginPanel.classList.toggle('hidden', isLogged);
  els.filtersPanel.classList.toggle('hidden', !isLogged);
  els.dashboard.classList.toggle('hidden', !isLogged);
  els.loading.classList.toggle('hidden', isLogged || Boolean(state.conversations.length));
}

function buildQueryString() {
  const params = new URLSearchParams();
  if (state.filters.status) params.set('status', state.filters.status);
  if (state.filters.canal) params.set('canal', state.filters.canal);
  if (state.filters.cliente_id) params.set('cliente_id', state.filters.cliente_id);
  const query = params.toString();
  return query ? `?${query}` : '';
}

async function loadConversations() {
  try {
    els.loading.classList.remove('hidden');
    const data = await fetchJson(`/conversas/${buildQueryString()}`);
    state.conversations = data;
    if (!state.selectedId && data.length) {
      state.selectedId = data[0].id;
    }
    renderConversations();
    renderConversationDetail();
  } catch (error) {
    alert(error.message);
  } finally {
    els.loading.classList.add('hidden');
  }
}

function renderConversations() {
  if (!state.conversations.length) {
    els.conversationList.innerHTML = '<div class="empty-state">Nenhuma conversa encontrada.</div>';
    return;
  }

  els.conversationList.innerHTML = state.conversations
    .map((conversation) => {
      const isActive = conversation.id === state.selectedId ? 'active' : '';
      return `
        <div class="conversation-item ${isActive}" data-id="${conversation.id}">
          <div class="conversation-item-header">
            <strong>#${conversation.id}</strong>
            <span class="badge status-${conversation.status}">${conversation.status}</span>
          </div>
          <div><strong>${conversation.assunto}</strong></div>
          <div class="conversation-meta">Cliente: ${conversation.cliente_id} • Canal: ${conversation.canal}</div>
        </div>
      `;
    })
    .join('');

  document.querySelectorAll('.conversation-item').forEach((item) => {
    item.addEventListener('click', () => {
      state.selectedId = Number(item.dataset.id);
      renderConversations();
      renderConversationDetail();
    });
  });
}

function renderConversationDetail() {
  const conversation = state.conversations.find((item) => item.id === state.selectedId);

  if (!conversation) {
    els.conversationDetail.innerHTML = '<p>Selecione uma conversa para ver o histórico.</p>';
    return;
  }

  const messages = conversation.mensagens || [];
  const options = ['aberta', 'pendente', 'em_atendimento', 'finalizada']
    .map((status) => `<option value="${status}" ${status === conversation.status ? 'selected' : ''}>${status}</option>`)
    .join('');

  els.conversationDetail.innerHTML = `
    <div class="detail-header">
      <div>
        <h3>${conversation.assunto}</h3>
        <small>Cliente ${conversation.cliente_id} • Canal ${conversation.canal}</small>
      </div>
      <select id="status-select">${options}</select>
    </div>

    <div class="message-list">
      ${messages.length ? messages.map((message) => `
        <div class="message ${message.remetente === 'cliente' ? '' : 'mine'}">
          <small>${message.remetente} • ${new Date(message.data_envio).toLocaleString('pt-BR')}</small>
          <div>${message.texto}</div>
        </div>
      `).join('') : '<div class="empty-state">Ainda não há mensagens nesta conversa.</div>'}
    </div>

    <form id="message-form" class="message-form">
      <textarea id="message-input" placeholder="Escreva a resposta..."></textarea>
      <button type="submit" class="primary">Enviar</button>
    </form>
  `;

  const statusSelect = document.getElementById('status-select');
  statusSelect.addEventListener('change', async (event) => {
    const nextStatus = event.target.value;
    await fetchJson(`/conversas/${conversation.id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status: nextStatus }),
    });
    await loadConversations();
  });

  const form = document.getElementById('message-form');
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const textarea = document.getElementById('message-input');
    const text = textarea.value.trim();
    if (!text) return;

    await fetchJson(`/conversas/${conversation.id}/mensagens/`, {
      method: 'POST',
      body: JSON.stringify({
        remetente: 'atendente',
        texto: text,
      }),
    });

    textarea.value = '';
    await loadConversations();
  });
}

els.loginForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const username = document.getElementById('username').value;
  const password = document.getElementById('password').value;

  try {
    const result = await fetchJson('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });

    state.token = result.token;
    localStorage.setItem(STORAGE_KEY, result.token);
    updateAuthUI();
    await loadConversations();
  } catch (error) {
    alert(error.message);
  }
});

els.refreshButton.addEventListener('click', loadConversations);

els.logoutButton.addEventListener('click', () => {
  state.token = '';
  localStorage.removeItem(STORAGE_KEY);
  updateAuthUI();
  els.conversationList.innerHTML = '';
  els.conversationDetail.innerHTML = '<p>Selecione uma conversa para ver o histórico.</p>';
});

els.statusFilter.addEventListener('change', (event) => {
  state.filters.status = event.target.value;
  loadConversations();
});

els.canalFilter.addEventListener('change', (event) => {
  state.filters.canal = event.target.value;
  loadConversations();
});

updateAuthUI();
if (state.token) {
  loadConversations();
}
