import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ArrowDown, ArrowUpRight, Bot, CheckCheck, CirclePlus, Clock3, MessageSquareText, Search, Send, Sparkles, UserRound } from 'lucide-react';
import { api } from '../services/api.js';
import { useApiData } from '../hooks/useApiData.js';

const statusLabels = {
  aberta: 'Aberta', pendente: 'Pendente', em_atendimento: 'Em atendimento', finalizada: 'Finalizada',
};
const outcomeLabels = {
  sem_resultado: 'Sem resultado', aguardando_retorno: 'Aguardando retorno', venda_realizada: 'Venda realizada',
};
const emptyItems = [];

async function loadConversations(filters) {
  const [pageResult, clientsResult, agentsResult, whatsappResult] = await Promise.allSettled([
    api.conversas.page(filters),
    api.clientes.list(),
    api.usuarios.agents(),
    api.canais.whatsappStatus(),
  ]);
  if (pageResult.status === 'rejected') {
    throw new Error(`Fila de conversas (/conversas/pagina): ${pageResult.reason.message}`);
  }
  if (clientsResult.status === 'rejected') {
    throw new Error(`Clientes (/clientes/): ${clientsResult.reason.message}`);
  }

  const warnings = [];
  if (agentsResult.status === 'rejected') {
    warnings.push(`Não foi possível carregar a lista de atendentes: ${agentsResult.reason.message}`);
  }
  if (whatsappResult.status === 'rejected') {
    warnings.push(`Não foi possível verificar a conexão do WhatsApp: ${whatsappResult.reason.message}`);
  }
  return {
    page: pageResult.value,
    clientes: clientsResult.value,
    agents: agentsResult.status === 'fulfilled' ? agentsResult.value : null,
    whatsapp: whatsappResult.status === 'fulfilled' ? whatsappResult.value : null,
    warnings,
  };
}

export function ConversationsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedId, setSelectedId] = useState(() => Number(searchParams.get('selected')) || null);
  const [query, setQuery] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [channelFilter, setChannelFilter] = useState('');
  const [responsibleFilter, setResponsibleFilter] = useState('');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [overdueOnly, setOverdueOnly] = useState(false);
  const [offset, setOffset] = useState(0);
  const pageSize = 25;
  const { data, loading, error, refresh } = useApiData(
    () => loadConversations({
      q: searchQuery,
      status: statusFilter,
      canal: channelFilter,
      responsavel: responsibleFilter,
      desde: fromDate,
      ate: toDate,
      atrasadas: overdueOnly,
      limit: pageSize,
      offset,
    }),
    [searchQuery, statusFilter, channelFilter, responsibleFilter, fromDate, toDate, overdueOnly, offset],
  );
  const [mobilePanel, setMobilePanel] = useState(() => searchParams.get('selected') ? 'thread' : 'queue');
  const [fallbackConversation, setFallbackConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [beforeMessageId, setBeforeMessageId] = useState(null);
  const [hasOlderMessages, setHasOlderMessages] = useState(false);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const [agents, setAgents] = useState([]);
  const [assigning, setAssigning] = useState(false);
  const [message, setMessage] = useState('');
  const [messageSender, setMessageSender] = useState('cliente');
  const [actionError, setActionError] = useState('');
  const [sending, setSending] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState('');
  const [createBusy, setCreateBusy] = useState(false);
  const [aiStatus, setAiStatus] = useState(null);
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [aiSuggestions, setAiSuggestions] = useState([]);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState('');
  const [draftSuggestionId, setDraftSuggestionId] = useState(null);
  const [decisionBusy, setDecisionBusy] = useState(null);

  const clientsById = useMemo(() => new Map((data?.clientes || []).map((client) => [client.id, client])), [data]);
  const filtered = data?.page.items || emptyItems;
  const selected = filtered.find((item) => item.id === selectedId)
    || (fallbackConversation?.id === selectedId ? fallbackConversation : null)
    || filtered[0]
    || null;
  useEffect(() => {
    const timer = window.setTimeout(() => {
      setOffset(0);
      setSearchQuery(query.trim());
    }, 300);
    return () => window.clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    if (data?.agents) setAgents(data.agents);
  }, [data]);

  useEffect(() => {
    if (selected && selected.id !== selectedId) setSelectedId(selected.id);
  }, [selected, selectedId]);

  useEffect(() => {
    const requestedId = Number(searchParams.get('selected')) || null;
    if (requestedId && requestedId !== selectedId) {
      setSelectedId(requestedId);
      setMobilePanel('thread');
    }
  }, [searchParams, selectedId]);

  useEffect(() => {
    api.ia.status().then(setAiStatus).catch(() => setAiStatus({ configurada: false }));
  }, []);

  useEffect(() => {
    if (!selectedId || filtered.some((item) => item.id === selectedId)) {
      setFallbackConversation(null);
      return undefined;
    }
    let active = true;
    api.conversas.get(selectedId)
      .then((conversation) => { if (active) setFallbackConversation(conversation); })
      .catch((reason) => { if (active) setActionError(reason.message); });
    return () => { active = false; };
  }, [selectedId, filtered]);

  async function loadMessages(conversationId) {
    const page = await api.conversas.messagesPage(conversationId);
    setMessages(page.items);
    setHasOlderMessages(page.has_more);
    setBeforeMessageId(page.next_before_id);
  }

  async function loadOlderMessages() {
    if (!selected || !beforeMessageId || loadingOlder) return;
    setLoadingOlder(true);
    try {
      const page = await api.conversas.messagesPage(selected.id, { before_id: beforeMessageId });
      setMessages((current) => [...page.items, ...current]);
      setHasOlderMessages(page.has_more);
      setBeforeMessageId(page.next_before_id);
    } catch (reason) {
      setActionError(reason.message);
    } finally {
      setLoadingOlder(false);
    }
  }

  useEffect(() => {
    let active = true;
    setMessage('');
    setMessageSender(selected?.canal === 'whatsapp' ? 'atendente' : 'cliente');
    setMessages([]);
    setMessagesLoading(Boolean(selected));
    setHasOlderMessages(false);
    setBeforeMessageId(null);
    setAiAnalysis(null);
    setAiSuggestions([]);
    setAiError('');
    setDraftSuggestionId(null);
    setActionError('');
    if (selected) {
      api.conversas.messagesPage(selected.id)
        .then((page) => {
          if (!active) return;
          setMessages(page.items);
          setHasOlderMessages(page.has_more);
          setBeforeMessageId(page.next_before_id);
        })
        .catch((reason) => { if (active) setActionError(reason.message); })
        .finally(() => { if (active) setMessagesLoading(false); });
    }
    return () => { active = false; };
  }, [selected?.id]);

  function chooseConversation(id) {
    setSelectedId(id);
    setMobilePanel('thread');
    setSearchParams({ selected: String(id) }, { replace: true });
    setActionError('');
  }

  async function changeStatus(nextStatus) {
    if (!selected) return;
    setActionError('');
    try { await api.conversas.setStatus(selected.id, nextStatus); await refresh(); }
    catch (reason) { setActionError(reason.message); }
  }

  async function changeOutcome(nextOutcome) {
    if (!selected) return;
    setActionError('');
    try { await api.conversas.setOutcome(selected.id, nextOutcome); await refresh(); }
    catch (reason) { setActionError(reason.message); }
  }

  async function changeResponsible(username) {
    if (!selected) return;
    setAssigning(true);
    setActionError('');
    try {
      await api.conversas.setResponsible(selected.id, username || null);
      await refresh();
    } catch (reason) {
      setActionError(reason.message);
    } finally {
      setAssigning(false);
    }
  }

  async function sendMessage(event) {
    event.preventDefault();
    if (!selected || !message.trim()) return;
    setSending(true); setActionError('');
    try {
      await api.conversas.sendMessage(selected.id, message.trim(), messageSender, messageSender === 'atendente' ? draftSuggestionId : null);
      setMessage('');
      setAiAnalysis(null);
      if (draftSuggestionId) setAiSuggestions((current) => current.map((item) => item.id === draftSuggestionId ? { ...item, status: 'enviada' } : item));
      setDraftSuggestionId(null);
      await Promise.all([refresh(), loadMessages(selected.id)]);
    }
    catch (reason) { setActionError(reason.message); }
    finally { setSending(false); }
  }

  async function createConversation(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const clienteId = Number(form.get('cliente_id'));
    if (!clienteId) {
      setCreateError('Selecione um cliente.');
      return;
    }
    setCreateBusy(true);
    setCreateError('');
    try {
      const conversation = await api.conversas.create({
        cliente_id: clienteId,
        assunto: form.get('assunto').trim() || 'Atendimento',
        canal: form.get('canal'),
      });
      setCreating(false);
      await refresh();
      chooseConversation(conversation.id);
    } catch (reason) {
      setCreateError(reason.message);
    } finally {
      setCreateBusy(false);
    }
  }

  async function analyzeConversation() {
    if (!selected) return;
    setAiLoading(true);
    setAiError('');
    try {
      const result = await api.ia.analyzeConversation(selected.id);
      setAiAnalysis(result.analise);
      setAiSuggestions(result.sugestoes);
    } catch (reason) {
      setAiError(reason.message);
    } finally {
      setAiLoading(false);
    }
  }

  async function decideSuggestion(suggestion, decision) {
    setDecisionBusy(suggestion.id);
    setAiError('');
    try {
      const updated = await api.ia.decideSuggestion(suggestion.id, decision);
      setAiSuggestions((current) => current.map((item) => item.id === updated.id ? updated : item));
      return updated;
    } catch (reason) {
      setAiError(reason.message);
      return null;
    } finally {
      setDecisionBusy(null);
    }
  }

  async function useReplySuggestion(suggestion) {
    const accepted = suggestion.status === 'pendente'
      ? await decideSuggestion(suggestion, 'aceita')
      : suggestion;
    if (!accepted || accepted.status !== 'aceita') return;
    setDraftSuggestionId(accepted.id);
    setMessageSender('atendente');
    setMessage(accepted.conteudo);
    setMobilePanel('thread');
  }

  if (loading) return <div className="page-loading"><span className="spinner" />Carregando atendimentos…</div>;
  if (error) return <section className="page-error"><h2>Não foi possível carregar as conversas</h2><p>{error}</p><button className="button button-primary" onClick={refresh}>Tentar novamente</button></section>;

  return <div className="page-stack conversation-page">
    <div className="page-heading"><div><span className="eyebrow">ATENDIMENTO</span><h1>Conversas</h1><p>Acompanhe a fila e responda com contexto.</p></div><div className="heading-actions"><span className="conversation-count"><MessageSquareText size={16} /> {data.page.total} registradas</span><span className={`connection-badge${data.whatsapp?.configured ? ' is-connected' : ''}`}><i /> WhatsApp {data.whatsapp ? (data.whatsapp.configured ? 'conectado' : 'não configurado') : 'status indisponível'}</span><button type="button" className="button button-primary" onClick={() => { setCreateError(''); setCreating(true); }}><CirclePlus size={17} /> Novo atendimento</button></div></div>
    {actionError && <div className="inline-error" role="alert">{actionError}</div>}
    {data.warnings.length > 0 && <div className="inline-warning" role="status">{data.warnings.join(' · ')}</div>}
    {creating && <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && setCreating(false)}>
      <section className="modal-card" role="dialog" aria-modal="true" aria-labelledby="conversation-modal-title">
        <div className="modal-heading"><div><span className="eyebrow">ATENDIMENTO</span><h2 id="conversation-modal-title">Novo atendimento</h2></div><button className="icon-button close-button" type="button" onClick={() => setCreating(false)} aria-label="Fechar">×</button></div>
        <form className="client-form" onSubmit={createConversation}>
          <label>Cliente<select name="cliente_id" required defaultValue=""><option value="" disabled>Selecione um cliente</option>{(data.clientes || []).map((client) => <option value={client.id} key={client.id}>{client.nome}</option>)}</select></label>
          <label>Assunto<input name="assunto" maxLength="200" placeholder="Ex.: Dúvida sobre pedido" /></label>
          <label>Canal<select name="canal" defaultValue="chat"><option value="chat">Chat</option><option value="whatsapp">WhatsApp</option><option value="telefone">Telefone</option><option value="email">E-mail</option><option value="loja">Loja</option></select></label>
          {createError && <div className="inline-error" role="alert">{createError}</div>}
          <div className="modal-actions"><button className="button button-secondary" type="button" onClick={() => setCreating(false)}>Cancelar</button><button className="button button-primary" disabled={createBusy || !data.clientes?.length}>{createBusy ? 'Criando...' : 'Criar atendimento'}</button></div>
        </form>
      </section>
    </div>}
    <section className="conversation-workspace surface">
      <nav className="conversation-mobile-tabs" aria-label="Painéis da conversa">{[['queue', 'Fila'], ['thread', 'Conversa'], ['copilot', 'Copiloto']].map(([key, label]) => <button type="button" key={key} className={mobilePanel === key ? 'active' : ''} aria-pressed={mobilePanel === key} onClick={() => setMobilePanel(key)}>{label}</button>)}</nav>
      <aside className={`conversation-queue mobile-panel${mobilePanel === 'queue' ? ' is-visible' : ''}`}>
        <div className="queue-heading"><div><h2>Fila de atendimento</h2><span>{data.page.total} conversas</span></div><button type="button" className="icon-button" onClick={refresh} aria-label="Atualizar fila"><ArrowDown size={17} /></button></div>
        <label className="table-search queue-search"><Search size={16} /><span className="sr-only">Buscar conversa</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Cliente ou assunto" /></label>
        <div className="queue-filters">
          <label><span className="sr-only">Filtrar por status</span><select className="queue-filter" value={statusFilter} onChange={(event) => { setOffset(0); setStatusFilter(event.target.value); }}><option value="">Todos os status</option>{Object.entries(statusLabels).map(([key, label]) => <option value={key} key={key}>{label}</option>)}</select></label>
          <label><span className="sr-only">Filtrar por canal</span><select className="queue-filter" value={channelFilter} onChange={(event) => { setOffset(0); setChannelFilter(event.target.value); }}><option value="">Todos os canais</option>{['whatsapp', 'chat', 'telefone', 'email', 'loja'].map((channel) => <option value={channel} key={channel}>{channel}</option>)}</select></label>
          <label><span className="sr-only">Filtrar por atendente</span><select className="queue-filter" value={responsibleFilter} onChange={(event) => { setOffset(0); setResponsibleFilter(event.target.value); }}><option value="">Todos os atendentes</option><option value="sem_atribuicao">Sem atribuição</option>{data.agents.map((agent) => <option value={agent.username} key={agent.id}>{agent.username}</option>)}</select></label>
          <div className="queue-date-filters"><label><span>De</span><input aria-label="Data inicial" type="date" value={fromDate} onChange={(event) => { setOffset(0); setFromDate(event.target.value); }} /></label><label><span>Até</span><input aria-label="Data final" type="date" value={toDate} onChange={(event) => { setOffset(0); setToDate(event.target.value); }} /></label></div>
          <label className="queue-overdue-filter"><input type="checkbox" checked={overdueOnly} onChange={(event) => { setOffset(0); setOverdueOnly(event.target.checked); }} /> <Clock3 size={13} /> SLA vencido</label>
        </div>
        <div className="queue-list">{filtered.length ? filtered.map((conversation) => {
          const client = clientsById.get(conversation.cliente_id);
          return <button type="button" key={conversation.id} className={`queue-item${selected?.id === conversation.id ? ' selected' : ''}`} onClick={() => chooseConversation(conversation.id)}>
            <span className="table-avatar">{(client?.nome || 'C').slice(0, 1).toUpperCase()}</span>
            <span className="queue-item-copy"><span><b>{client?.nome || `Cliente #${conversation.cliente_id}`}</b><small>{conversation.assunto}</small></span><span className={`status-dot status-${conversation.status}`} title={statusLabels[conversation.status] || conversation.status} /></span>
            <span className="queue-item-meta"><span>{conversation.canal}</span><span>{conversation.responsavel || 'Sem responsável'}</span><span>{new Date(conversation.ultima_atualizacao).toLocaleDateString('pt-BR')}</span></span>
            <span className="queue-item-preview">{conversation.ultima_mensagem || conversation.assunto}{conversation.sla_atrasada && <b className="sla-badge">SLA vencido</b>}</span>
          </button>;
        }) : <div className="empty-queue">Nenhuma conversa encontrada.</div>}</div>
        <div className="queue-pagination"><button type="button" className="button button-secondary" disabled={!offset} onClick={() => setOffset(Math.max(0, offset - pageSize))}>Anterior</button><span>{data.page.total ? `${offset + 1}–${Math.min(offset + filtered.length, data.page.total)} de ${data.page.total}` : '0 resultados'}</span><button type="button" className="button button-secondary" disabled={offset + pageSize >= data.page.total} onClick={() => setOffset(offset + pageSize)}>Próxima</button></div>
      </aside>

      <section className={`conversation-thread mobile-panel${mobilePanel === 'thread' ? ' is-visible' : ''}`} aria-label="Detalhes da conversa">
        {selected ? <>
          <header className="thread-header"><span className="table-avatar large">{(clientsById.get(selected.cliente_id)?.nome || 'C').slice(0, 1).toUpperCase()}</span><div className="thread-person"><h2>{clientsById.get(selected.cliente_id)?.nome || `Cliente #${selected.cliente_id}`}</h2><span>{selected.assunto} · {selected.canal}</span></div>
            <label className="sr-only" htmlFor="conversation-status">Status da conversa</label><select id="conversation-status" className="status-select" value={selected.status} onChange={(event) => changeStatus(event.target.value)}>{Object.entries(statusLabels).map(([key, label]) => <option value={key} key={key}>{label}</option>)}</select>
          </header>
          <div className="thread-outcome"><label htmlFor="conversation-responsible">Responsável</label><select id="conversation-responsible" value={selected.responsavel || ''} disabled={assigning} onChange={(event) => changeResponsible(event.target.value)}><option value="">Sem atribuição</option>{agents.map((agent) => <option value={agent.username} key={agent.id}>{agent.username}</option>)}</select><label htmlFor="conversation-outcome">Resultado</label><select id="conversation-outcome" value={selected.resultado || 'sem_resultado'} onChange={(event) => changeOutcome(event.target.value)}>{Object.entries(outcomeLabels).map(([key, label]) => <option value={key} key={key}>{label}</option>)}</select></div>
          {selected.sla_atrasada && <div className="sla-alert" role="status"><Clock3 size={15} /> Sem resposta do atendente há pelo menos {data.page.sla_minutes} minutos.</div>}
          <div className="thread-date">Histórico registrado</div>
          <div className="message-history">{hasOlderMessages && <button type="button" className="button button-secondary load-older-messages" onClick={loadOlderMessages} disabled={loadingOlder}>{loadingOlder ? 'Carregando…' : 'Carregar mensagens anteriores'}</button>}{messages.length ? messages.map((item) => <article className={`message-bubble ${item.remetente === 'cliente' ? 'incoming' : 'outgoing'}`} key={item.id}>
            <span className="message-author">{item.remetente === 'cliente' ? 'Cliente' : item.remetente}</span><p>{item.texto}</p><time>{new Date(item.data_envio).toLocaleString('pt-BR')}</time>
          </article>) : <div className="empty-thread"><UserRound size={23} /><b>{messagesLoading ? 'Carregando mensagens…' : 'Esta conversa ainda não tem mensagens.'}</b><span>As mensagens aparecerão aqui quando forem registradas.</span></div>}</div>
          <form className="message-composer" onSubmit={sendMessage}><label className="sr-only" htmlFor="reply-message">Mensagem</label><textarea id="reply-message" rows="2" value={message} onChange={(event) => setMessage(event.target.value)} placeholder={messageSender === 'cliente' ? 'Registre a mensagem do cliente…' : 'Escreva uma resposta…'} maxLength="4000" /><div className="composer-footer"><div className="composer-meta"><label htmlFor="message-sender">Registrar como</label><select id="message-sender" value={messageSender} onChange={(event) => { setMessageSender(event.target.value); if (event.target.value === 'cliente' && draftSuggestionId) { setDraftSuggestionId(null); setMessage(''); } }}><option value="cliente">Cliente</option><option value="atendente">Atendente</option></select><span>{messageSender === 'cliente' ? 'Inclua a fala do cliente no histórico para dar contexto à análise.' : selected.canal === 'whatsapp' ? 'A resposta será enviada pelo WhatsApp.' : 'Revise a mensagem antes de enviar.'}</span></div><button className="button button-primary" type="submit" disabled={sending || !message.trim()}>{sending ? 'Enviando…' : messageSender === 'atendente' && selected.canal === 'whatsapp' ? 'Enviar WhatsApp' : 'Registrar'} <Send size={15} /></button></div></form>
        </> : <div className="empty-thread no-conversation"><MessageSquareText size={28} /><h2>Selecione uma conversa</h2><p>Escolha um atendimento na fila para ver o histórico.</p><span><CheckCheck size={15} /> Dados conectados à API</span></div>}
      </section>
      <aside className={'copilot-panel mobile-panel' + (mobilePanel === 'copilot' ? ' is-visible' : '')}>
        <div className="copilot-heading"><span className="copilot-mark"><Bot size={17} /></span><div><h2>Copiloto IA</h2><span className={'connection-badge' + (aiStatus?.configurada ? ' is-connected' : '')}><i /> {aiStatus?.configurada ? 'IA conectada' : 'Configuração necessária'}</span></div><ArrowUpRight size={16} className="muted-icon" /></div>
        <div className="copilot-content">
          {!selected ? <div className="copilot-empty"><span className="sparkle-orb"><Bot size={24} /></span><b>Selecione um atendimento</b><p>A análise usa o histórico da conversa, o catálogo e os pedidos deste cliente.</p></div> : <>
            <button type="button" className="button button-primary copilot-analyze" onClick={analyzeConversation} disabled={aiLoading || !aiStatus?.configurada || !messages.length} title={!aiStatus?.configurada ? 'Configure OPENAI_API_KEY no .env para habilitar a análise.' : !messages.length ? 'Registre uma mensagem antes de analisar.' : undefined}><Sparkles size={15} />{aiLoading ? 'Analisando conversa...' : !aiStatus?.configurada ? 'Configure a IA para analisar' : aiAnalysis ? 'Analisar novamente' : 'Analisar conversa'}</button>
            {!aiStatus?.configurada && <p className="copilot-setup">A análise está desativada porque <code>OPENAI_API_KEY</code> não está configurada. Adicione a chave ao arquivo <code>.env</code> e reinicie a API.</p>}
            {!messages.length && <p className="copilot-setup">{messagesLoading ? 'Carregando mensagens da conversa…' : 'Registre uma mensagem nesta conversa antes de solicitar a análise.'}</p>}
            {aiError && <div className="inline-error copilot-error" role="alert">{aiError}</div>}
            {aiAnalysis && <div className="ai-analysis">
              <section><span className="ai-label">Intenção de compra</span><b>{aiAnalysis.intencao}</b><p>{aiAnalysis.justificativa_intencao}</p></section>
              <section><span className="ai-label">Objeções</span>{aiAnalysis.objecoes.length ? <ul>{aiAnalysis.objecoes.map((item, index) => <li key={index}>{item}</li>)}</ul> : <p>Nenhuma objeção clara no histórico.</p>}</section>
              <section><span className="ai-label">Produtos sugeridos</span>{aiSuggestions.some((item) => item.tipo === 'produto') ? <div className="copilot-suggestions">{aiSuggestions.filter((item) => item.tipo === 'produto').map((suggestion) => <div className="copilot-suggestion" key={suggestion.id}><span>{suggestion.conteudo}</span>{suggestion.status === 'pendente' ? <span className="copilot-suggestion-actions"><button type="button" onClick={() => decideSuggestion(suggestion, 'rejeitada')} disabled={decisionBusy === suggestion.id}>Rejeitar</button><button type="button" onClick={() => decideSuggestion(suggestion, 'aceita')} disabled={decisionBusy === suggestion.id}>Aceitar</button></span> : <small>{suggestion.status}</small>}</div>)}</div> : <p>Sem recomendação com os dados disponíveis.</p>}</section>
              <section><span className="ai-label">Evidências · confiança {aiAnalysis.confianca}</span>{aiAnalysis.evidencias.length ? <ul>{aiAnalysis.evidencias.map((item, index) => <li key={index}>{item}</li>)}</ul> : <p>Dados limitados na conversa.</p>}</section>
              {aiSuggestions.filter((item) => item.tipo === 'resposta').map((suggestion) => <section className="ai-reply" key={suggestion.id}><span className="ai-label">Resposta sugerida</span><p>{suggestion.conteudo}</p><button type="button" className="button button-secondary" disabled={suggestion.status === 'rejeitada' || suggestion.status === 'enviada' || decisionBusy === suggestion.id} onClick={() => useReplySuggestion(suggestion)}>{suggestion.status === 'enviada' ? 'Mensagem enviada' : suggestion.status === 'rejeitada' ? 'Sugestão rejeitada' : suggestion.status === 'aceita' ? 'Usar como rascunho' : 'Usar como rascunho'}</button></section>)}
            </div>}
          </>}
        </div>
        <div className="copilot-footer">A mensagem não é enviada automaticamente. O texto da conversa é processado pela OpenAI somente ao solicitar uma análise.</div>
      </aside>
    </section>
  </div>;
}
