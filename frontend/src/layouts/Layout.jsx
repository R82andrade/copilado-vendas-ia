import React, { useEffect, useRef, useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
  Activity, BarChart3, Bell, Bot, Boxes, ChevronDown, ClipboardList,
  LayoutDashboard, LogOut, MessageSquareText, Settings, Users,
} from 'lucide-react';
import { api } from '../services/api.js';

const navigation = [
  { label: 'Dashboard', path: '/', icon: LayoutDashboard, end: true },
  { label: 'Clientes', path: '/clientes', icon: Users },
  { label: 'Conversas', path: '/conversas', icon: MessageSquareText },
  { label: 'Análises da IA', path: '/analises-ia', icon: BarChart3 },
  { label: 'Sugestões', path: '/sugestoes', icon: Bot },
  { label: 'Produtos', path: '/produtos', icon: Boxes },
  { label: 'Histórico', path: '/historico', icon: ClipboardList },
];

export function Layout({ account, onLogout }) {
  const navigate = useNavigate();
  const searchInput = useRef(null);
  const [search, setSearch] = useState('');
  const [results, setResults] = useState([]);

  useEffect(() => {
    const term = search.trim().toLocaleLowerCase('pt-BR');
    if (term.length < 2) { setResults([]); return undefined; }
    let active = true;
    const timer = setTimeout(async () => {
      try {
        const [clients, conversations] = await Promise.all([api.clientes.list(), api.conversas.list()]);
        if (!active) return;
        const matches = clients.filter((client) => [client.nome, client.cpf, client.telefone, client.email]
          .some((value) => value?.toLocaleLowerCase('pt-BR').includes(term)))
          .slice(0, 5).map((client) => ({ label: client.nome, detail: client.telefone || client.email || `Cliente #${client.id}`, to: `/clientes/${client.id}` }));
        const clientNames = new Map(clients.map((client) => [client.id, client.nome]));
        const conversationMatches = conversations.filter((conversation) =>
          `${conversation.assunto} ${clientNames.get(conversation.cliente_id) || ''}`.toLocaleLowerCase('pt-BR').includes(term))
          .slice(0, 4).map((conversation) => ({ label: conversation.assunto, detail: clientNames.get(conversation.cliente_id) || `Cliente #${conversation.cliente_id}`, to: `/conversas?selected=${conversation.id}` }));
        setResults([...matches, ...conversationMatches].slice(0, 7));
      } catch { if (active) setResults([]); }
    }, 250);
    return () => { active = false; clearTimeout(timer); };
  }, [search]);

  useEffect(() => {
    function handleShortcut(event) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        searchInput.current?.focus();
      }
    }
    window.addEventListener('keydown', handleShortcut);
    return () => window.removeEventListener('keydown', handleShortcut);
  }, []);

  function openResult(to) { setSearch(''); setResults([]); navigate(to); }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <NavLink to="/" className="brand-lockup">
          <span className="brand-icon"><Activity size={20} strokeWidth={2.5} /></span>
          <span><strong>copiloto</strong><small>VENDAS COM IA</small></span>
        </NavLink>
        <div className="workspace-label">ESPAÇO DE TRABALHO</div>
        <nav className="side-nav" aria-label="Navegação principal">
          {navigation.map(({ label, path, icon: Icon, end }) => (
            <NavLink key={path} to={path} end={end} className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
              <Icon size={18} /><span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <NavLink to="/configuracoes" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
            <Settings size={18} /><span>Configurações</span>
          </NavLink>
          <div className="sidebar-note"><Bot size={17} /><span>O copiloto sugere.<br /><b>Você decide.</b></span></div>
        </div>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <div className="breadcrumb"><span>Copiloto</span><span className="crumb-separator">/</span><strong>Painel comercial</strong></div>
          <div className="topbar-actions">
            <div className="global-search-wrap">
              <label className="global-search"><span className="sr-only">Busca global por cliente ou conversa</span><input ref={searchInput} value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar clientes..." autoComplete="off" /><kbd>Ctrl K</kbd></label>
              {results.length > 0 && <div className="search-results" role="listbox">{results.map((result, index) => <button type="button" role="option" aria-selected="false" key={`${result.to}-${index}`} onClick={() => openResult(result.to)}><Search size={14} /><span><b>{result.label}</b><small>{result.detail}</small></span></button>)}</div>}
            </div>
            <button className="icon-button" type="button" aria-label="Notificações indisponíveis"><Bell size={18} /></button>
            <div className="account-menu">
              <span className="avatar">{account.username.slice(0, 1).toUpperCase()}</span>
              <span className="account-copy"><b>{account.username}</b><small>{account.role || 'Equipe comercial'}</small></span>
              <ChevronDown size={15} />
              <button type="button" className="account-logout" onClick={onLogout}><LogOut size={15} /> Sair</button>
            </div>
          </div>
        </header>
        <main className="page-content"><Outlet /></main>
      </div>
    </div>
  );
}
