const API_BASE = import.meta.env.VITE_API_BASE_URL || '';
const TOKEN_KEY = 'vendas-api-token';

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (response.status === 204) return null;
  const text = await response.text();
  let payload;
  try { payload = text ? JSON.parse(text) : null; } catch { payload = null; }
  if (!response.ok) {
    const error = new Error(payload?.detail || `Erro de comunicação (${response.status})`);
    error.status = response.status;
    if (response.status === 401) window.dispatchEvent(new Event('auth:expired'));
    throw error;
  }
  return payload;
}

export const api = {
  login: (username, password) => request('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }),
  clientes: {
    list: () => request('/clientes/'),
    get: (id) => request(`/clientes/${id}`),
    create: (data) => request('/clientes/', { method: 'POST', body: JSON.stringify(data) }),
    update: (id, data) => request(`/clientes/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    remove: (id) => request(`/clientes/${id}`, { method: 'DELETE' }),
  },
  conversas: {
    list: (filters = {}) => {
      const params = new URLSearchParams(Object.entries(filters).filter(([, value]) => value));
      return request(`/conversas/${params.size ? `?${params}` : ''}`);
    },
    page: (filters = {}) => {
      const params = new URLSearchParams(Object.entries(filters).filter(([, value]) => value !== '' && value !== null && value !== undefined));
      return request(`/conversas/pagina?${params}`);
    },
    create: (data) => request('/conversas/', { method: 'POST', body: JSON.stringify(data) }),
    get: (id) => request(`/conversas/${id}`),
    setStatus: (id, status) => request(`/conversas/${id}/status`, { method: 'PATCH', body: JSON.stringify({ status }) }),
    setOutcome: (id, resultado) => request(`/conversas/${id}/resultado`, { method: 'PATCH', body: JSON.stringify({ resultado }) }),
    setResponsible: (id, username) => request(`/conversas/${id}/responsavel`, { method: 'PATCH', body: JSON.stringify({ username }) }),
    messagesPage: (id, filters = {}) => {
      const params = new URLSearchParams(Object.entries(filters).filter(([, value]) => value !== '' && value !== null && value !== undefined));
      return request(`/conversas/${id}/mensagens/pagina${params.size ? `?${params}` : ''}`);
    },
    sendMessage: (id, texto, remetente = 'atendente', sugestaoId = null) => request(`/conversas/${id}/mensagens/`, {
      method: 'POST', body: JSON.stringify({ remetente, texto, sugestao_id: sugestaoId }),
    }),
  },
  canais: { whatsappStatus: () => request('/webhooks/whatsapp/status') },
  ia: {
    status: () => request('/ia/status'),
    analyzeConversation: (id) => request(`/ia/conversas/${id}/analise`, { method: 'POST' }),
    analyses: () => request('/ia/analises'),
    suggestions: (filters = {}) => {
      const params = new URLSearchParams(Object.entries(filters).filter(([, value]) => value));
      return request(`/ia/sugestoes/${params.size ? `?${params}` : ''}`);
    },
    decideSuggestion: (id, decision) => request(`/ia/sugestoes/${id}/decisao`, {
      method: 'POST', body: JSON.stringify({ decisao: decision }),
    }),
  },
  financeiro: {
    product: (id) => request(`/financeiro/produtos/${id}`),
    updateProduct: (id, data) => request(`/financeiro/produtos/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    simulate: (id, data) => request(`/financeiro/produtos/${id}/simulacoes`, { method: 'POST', body: JSON.stringify(data) }),
    config: () => request('/financeiro/configuracao'),
    updateConfig: (data) => request('/financeiro/configuracao', { method: 'PUT', body: JSON.stringify(data) }),
  },
  produtos: {
    list: () => request('/produtos/'),
    create: (data) => request('/produtos/', { method: 'POST', body: JSON.stringify(data) }),
    update: (id, data) => request(`/produtos/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    remove: (id) => request(`/produtos/${id}`, { method: 'DELETE' }),
  },
  pedidos: { list: () => request('/pedidos/') },
  iaFinanceiro: {
    recommend: (id, discount) => request(`/ia/produtos/${id}/recomendacao-financeira`, {
      method: 'POST', body: JSON.stringify({ desconto_percentual: Number(discount) }),
    }),
  },
  usuarios: {
    list: () => request('/auth/users'),
    agents: () => request('/auth/agents'),
    create: (data) => request('/auth/users', { method: 'POST', body: JSON.stringify(data) }),
    update: (id, data) => request(`/auth/users/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  },
};

export { TOKEN_KEY };
