import React, { useState } from 'react';
import { ShieldCheck, UserPlus, Users } from 'lucide-react';
import { api } from '../services/api.js';
import { useApiData } from '../hooks/useApiData.js';

const roleNames = { admin: 'Administrador', atendimento: 'Atendimento', vendas: 'Vendas', leitor: 'Leitura' };

export function UsersPage({ account }) {
  const loadUsers = account.role === 'admin' ? api.usuarios.list : async () => [];
  const { data, loading, error, refresh } = useApiData(loadUsers, [account.role]);
  const [notice, setNotice] = useState('');
  const [actionError, setActionError] = useState('');
  const [saving, setSaving] = useState(false);
  if (account.role !== 'admin') return <div className="page-error"><h2>Acesso restrito</h2><p>Somente administradores podem gerenciar contas de usuários.</p></div>;

  async function submit(event) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    setSaving(true); setActionError(''); setNotice('');
    try {
      await api.usuarios.create({ username: form.get('username').trim(), password: form.get('password'), role: form.get('role') });
      formElement.reset(); setNotice('Usuário criado.'); await refresh();
    } catch (reason) { setActionError(reason.message); }
    finally { setSaving(false); }
  }

  async function updateRole(id, role) {
    setActionError(''); setNotice('');
    try { await api.usuarios.update(id, { role }); setNotice('Perfil atualizado.'); await refresh(); }
    catch (reason) { setActionError(reason.message); await refresh(); }
  }

  async function toggleActive(user) {
    setActionError(''); setNotice('');
    try { await api.usuarios.update(user.id, { ativo: !user.ativo }); setNotice('Acesso atualizado.'); await refresh(); }
    catch (reason) { setActionError(reason.message); await refresh(); }
  }

  return <div className="page-stack"><div className="page-heading"><div><span className="eyebrow">ADMINISTRAÇÃO</span><h1>Usuários e permissões</h1><p>Crie contas e atribua o perfil de acesso de cada pessoa.</p></div></div>
    <div className="users-grid">
      <section className="surface user-create-card"><div className="section-heading"><div><h2>Novo usuário</h2><p>Senhas devem ter ao menos 12 caracteres.</p></div><UserPlus size={19} className="muted-icon" /></div>
        {actionError && <div className="inline-error" role="alert">{actionError}</div>}{notice && <div className="inline-success" role="status">{notice}</div>}
        <form className="client-form" onSubmit={submit}><label>Usuário<input name="username" minLength="3" required autoComplete="off" /></label><label>Senha inicial<input name="password" type="password" minLength="12" required autoComplete="new-password" /></label><label>Perfil<select name="role" defaultValue="atendimento">{Object.entries(roleNames).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><button className="button button-primary" disabled={saving}>{saving ? 'Criando…' : 'Criar usuário'}</button></form>
      </section>
      <section className="surface user-list-card"><div className="section-heading"><div><h2>Contas cadastradas</h2><p>Perfis validados pelo backend a cada operação.</p></div><Users size={19} className="muted-icon" /></div>
        {loading ? <div className="page-loading"><span className="spinner" />Carregando usuários…</div> : error ? <div className="inline-error" role="alert">{error}</div> : <div className="users-list">{data.map((user) => <article className="user-row" key={user.id}><span className="user-avatar"><ShieldCheck size={16} /></span><span className="user-copy"><b>{user.username}</b><small>{user.ativo ? 'Ativo' : 'Desativado'}</small></span><label className="sr-only" htmlFor={`role-${user.id}`}>Perfil de {user.username}</label><select id={`role-${user.id}`} className="user-role-select" value={user.role} onChange={(event) => updateRole(user.id, event.target.value)} disabled={user.username === account.username}><option value="admin">Administrador</option><option value="atendimento">Atendimento</option><option value="vendas">Vendas</option><option value="leitor">Leitura</option></select><button className="button button-secondary user-active-toggle" type="button" onClick={() => toggleActive(user)} disabled={user.username === account.username}>{user.ativo ? 'Desativar' : 'Ativar'}</button></article>)}</div>}
      </section>
    </div>
    <section className="surface roles-help"><h2>O que cada perfil pode fazer</h2><div className="role-help-grid"><div><b>Administrador</b><span>Acesso completo e gestão de usuários.</span></div><div><b>Atendimento</b><span>Consulta clientes e gerencia conversas.</span></div><div><b>Vendas</b><span>Gerencia clientes, produtos e pedidos.</span></div><div><b>Leitura</b><span>Consulta dados sem alterar registros.</span></div></div></section>
  </div>;
}
