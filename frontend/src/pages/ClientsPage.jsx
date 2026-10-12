import React, { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, AtSign, ChevronRight, CirclePlus, ClipboardList, Mail, MessageSquareText, Pencil, Phone, Search, ShoppingBag, Trash2, UserRound, Users } from 'lucide-react';
import { api } from '../services/api.js';
import { useApiData } from '../hooks/useApiData.js';

const emptyClient = { nome: '', cpf: '', telefone: '', email: '' };
const money = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

function ClientForm({ client, onSave, onClose, busy }) {
  async function submit(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await onSave({
      nome: form.get('nome').trim(),
      cpf: form.get('cpf').trim() || null,
      telefone: form.get('telefone').trim() || null,
      email: form.get('email').trim() || null,
    });
  }
  return <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
    <section className="modal-card" role="dialog" aria-modal="true" aria-labelledby="client-modal-title">
      <div className="modal-heading"><div><span className="eyebrow">BASE DE CLIENTES</span><h2 id="client-modal-title">{client ? 'Editar cliente' : 'Novo cliente'}</h2></div><button className="icon-button close-button" type="button" onClick={onClose} aria-label="Fechar">×</button></div>
      <form key={client?.id || 'new-client'} onSubmit={submit} className="client-form">
        <label>Nome completo<input name="nome" required maxLength="150" defaultValue={client?.nome || ''} autoFocus /></label>
        <div className="form-two-col">
          <label>CPF<input name="cpf" inputMode="numeric" maxLength="14" defaultValue={client?.cpf || ''} /></label>
          <label>Telefone<input name="telefone" type="tel" maxLength="20" defaultValue={client?.telefone || ''} /></label>
        </div>
        <label>E-mail<input name="email" type="email" maxLength="255" defaultValue={client?.email || ''} /></label>
        <div className="modal-actions"><button className="button button-secondary" type="button" onClick={onClose}>Cancelar</button><button className="button button-primary" disabled={busy}>{busy ? 'Salvando…' : 'Salvar cliente'}</button></div>
      </form>
    </section>
  </div>;
}

export function ClientsPage() {
  const { data: clients, loading, error, refresh } = useApiData(api.clientes.list, []);
  const [query, setQuery] = useState('');
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);
  const [actionError, setActionError] = useState('');
  const [notice, setNotice] = useState('');
  const filtered = useMemo(() => (clients || []).filter((client) =>
    [client.nome, client.cpf, client.telefone, client.email].some((value) => value?.toLowerCase().includes(query.trim().toLowerCase()))
  ), [clients, query]);

  async function saveClient(form) {
    setSaving(true); setActionError(''); setNotice('');
    try {
      if (editing?.id) await api.clientes.update(editing.id, form);
      else await api.clientes.create(form);
      setEditing(null); setNotice(editing ? 'Cadastro atualizado.' : 'Cliente cadastrado.');
      await refresh();
    } catch (reason) { setActionError(reason.message); }
    finally { setSaving(false); }
  }

  async function removeClient(client) {
    if (!window.confirm(`Excluir o cadastro de ${client.nome}?`)) return;
    setActionError(''); setNotice('');
    try { await api.clientes.remove(client.id); setNotice('Cliente excluído.'); await refresh(); }
    catch (reason) { setActionError(reason.message); }
  }

  return <div className="page-stack">
    <div className="page-heading">
      <div><span className="eyebrow">RELACIONAMENTO</span><h1>Clientes</h1><p>Consulte e mantenha atualizada a base de clientes.</p></div>
      <button className="button button-primary" onClick={() => { setEditing({ ...emptyClient }); setActionError(''); }}><CirclePlus size={17} /> Novo cliente</button>
    </div>
    <section className="surface table-surface">
      <div className="table-toolbar"><div><h2>Base de clientes</h2><span>{loading ? 'Carregando…' : `${clients?.length ?? 0} cadastros`}</span></div><label className="table-search"><Search size={17} /><span className="sr-only">Buscar cliente</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Nome, CPF, telefone ou e-mail" /></label></div>
      {notice && <div className="inline-success" role="status">{notice}</div>}
      {(error || actionError) && <div className="inline-error" role="alert">{error || actionError}</div>}
      {loading ? <div className="page-loading"><span className="spinner" />Buscando clientes…</div> : filtered.length ? <div className="table-scroll"><table className="data-table">
        <thead><tr><th>Cliente</th><th>Contato</th><th>CPF</th><th>Cadastro</th><th><span className="sr-only">Ações</span></th></tr></thead>
        <tbody>{filtered.map((client) => <tr key={client.id}>
          <td><Link className="client-name-cell" to={`/clientes/${client.id}`}><span className="table-avatar">{client.nome.slice(0, 1).toUpperCase()}</span><span><b>{client.nome}</b><small>Cliente #{client.id}</small></span><ChevronRight className="row-chevron" size={15} /></Link></td>
          <td><span className="contact-stack">{client.email && <span><Mail size={14} />{client.email}</span>}{client.telefone && <span><Phone size={14} />{client.telefone}</span>}{!client.email && !client.telefone && <span className="muted-copy">Sem contato cadastrado</span>}</span></td>
          <td>{client.cpf || <span className="muted-copy">—</span>}</td>
          <td>{client.data_cadastro ? new Date(`${client.data_cadastro}T12:00:00`).toLocaleDateString('pt-BR') : '—'}</td>
          <td><div className="row-actions"><button type="button" className="icon-button" aria-label={`Editar ${client.nome}`} onClick={() => { setEditing(client); setActionError(''); }}><Pencil size={16} /></button><button type="button" className="icon-button destructive" aria-label={`Excluir ${client.nome}`} onClick={() => removeClient(client)}><Trash2 size={16} /></button></div></td>
        </tr>)}</tbody>
      </table></div> : <div className="empty-block"><Users size={24} /><b>{query ? 'Nenhum cliente corresponde à busca' : 'Sua base começa aqui'}</b><span>{query ? 'Tente outro nome ou dado de contato.' : 'Cadastre o primeiro cliente para acompanhar o relacionamento.'}</span></div>}
    </section>
    {editing && <ClientForm client={editing.id ? editing : null} onSave={saveClient} onClose={() => setEditing(null)} busy={saving} />}
  </div>;
}

export function ClientProfilePage() {
  const { id } = useParams();
  const loadProfile = async () => {
    const [clientResult, conversationsResult, ordersResult] = await Promise.allSettled([
      api.clientes.get(id),
      api.conversas.list({ cliente_id: id }),
      api.pedidos.list(),
    ]);
    if (clientResult.status === 'rejected') throw clientResult.reason;

    return {
      client: clientResult.value,
      conversations: conversationsResult.status === 'fulfilled' ? conversationsResult.value : [],
      conversationsError: conversationsResult.status === 'rejected' ? conversationsResult.reason.message : '',
      orders: ordersResult.status === 'fulfilled'
        ? ordersResult.value.filter((order) => order.cliente_id === Number(id))
        : [],
      ordersError: ordersResult.status === 'rejected' ? ordersResult.reason.message : '',
    };
  };
  const { data, loading, error } = useApiData(loadProfile, [id]);
  if (loading) return <div className="page-loading"><span className="spinner" />Carregando perfil…</div>;
  if (error) return <section className="page-error"><h2>Não foi possível abrir este perfil</h2><p>{error}</p><Link className="text-link" to="/clientes"><ArrowLeft size={15} /> Voltar para clientes</Link></section>;
  const { client, conversations, conversationsError, orders, ordersError } = data;
  const recentOrders = [...orders].sort((a, b) => new Date(b.data_pedido) - new Date(a.data_pedido));
  return <div className="page-stack">
    <Link className="back-link" to="/clientes"><ArrowLeft size={16} /> Todos os clientes</Link>
    <section className="surface profile-header"><span className="profile-avatar">{client.nome.slice(0, 1).toUpperCase()}</span><div><span className="eyebrow">PERFIL DO CLIENTE · #{client.id}</span><h1>{client.nome}</h1><p>Cadastrado em {new Date(`${client.data_cadastro}T12:00:00`).toLocaleDateString('pt-BR')}</p></div></section>
    <section className="surface profile-details"><div className="section-heading"><div><h2>Informações de contato</h2><p>Dados cadastrados na base comercial.</p></div></div><div className="profile-fields">
      <div><span><AtSign size={16} /> E-mail</span><b>{client.email || 'Não informado'}</b></div>
      <div><span><Phone size={16} /> Telefone</span><b>{client.telefone || 'Não informado'}</b></div>
      <div><span><UserRound size={16} /> CPF</span><b>{client.cpf || 'Não informado'}</b></div>
    </div></section>
    <section className="profile-history-grid" aria-label="Histórico do cliente">
      <article className="surface profile-history-card">
        <div className="section-heading"><div><h2>Conversas</h2><p>Atendimentos vinculados a este cliente.</p></div><MessageSquareText size={18} className="muted-icon" /></div>
        {conversationsError ? <div className="inline-error" role="alert">{conversationsError}</div> : conversations.length ? <div className="profile-history-list">
          {conversations.map((conversation) => <Link className="profile-history-row" to={`/conversas?selected=${conversation.id}`} key={conversation.id}>
            <span className="profile-history-icon"><MessageSquareText size={15} /></span><span className="profile-history-copy"><b>{conversation.assunto}</b><small>{conversation.canal} · {new Date(conversation.ultima_atualizacao).toLocaleString('pt-BR')}</small></span><span className={`status-pill status-${conversation.status}`}>{conversation.status.replaceAll('_', ' ')}</span>
          </Link>)}
        </div> : <div className="profile-history-empty">Nenhuma conversa registrada para este cliente.</div>}
      </article>
      <article className="surface profile-history-card">
        <div className="section-heading"><div><h2>Pedidos</h2><p>Compras registradas para este cliente.</p></div><ShoppingBag size={18} className="muted-icon" /></div>
        {ordersError ? <div className="inline-error" role="alert">{ordersError}</div> : recentOrders.length ? <div className="profile-history-list">
          {recentOrders.map((order) => <div className="profile-history-row" key={order.id}>
            <span className="profile-history-icon"><ClipboardList size={15} /></span><span className="profile-history-copy"><b>Pedido #{order.id}</b><small>{new Date(`${order.data_pedido}T12:00:00`).toLocaleDateString('pt-BR')} · {order.itens.length} {order.itens.length === 1 ? 'item' : 'itens'}</small></span><b className="profile-order-total">{money.format(order.total)}</b>
          </div>)}
        </div> : <div className="profile-history-empty">Nenhum pedido registrado para este cliente.</div>}
      </article>
    </section>
  </div>;
}
