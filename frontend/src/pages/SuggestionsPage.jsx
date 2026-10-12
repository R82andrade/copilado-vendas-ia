import React, { useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowRight, Check, MessageSquareText, Package, Sparkles, X } from 'lucide-react';
import { useApiData } from '../hooks/useApiData.js';
import { api } from '../services/api.js';

const statusLabels = { pendente: 'Pendente', aceita: 'Aceita', rejeitada: 'Rejeitada', enviada: 'Enviada' };
const typeLabels = { produto: 'Produto', resposta: 'Resposta' };

export function SuggestionsPage() {
  const { data, loading, error, refresh, setData } = useApiData(api.ia.suggestions, []);
  const [searchParams, setSearchParams] = useSearchParams();
  const [filter, setFilter] = useState(searchParams.get('status') || '');
  const [actionError, setActionError] = useState('');
  const [busyId, setBusyId] = useState(null);
  const analysisId = Number(searchParams.get('analise')) || null;
  const visible = useMemo(() => (data || []).filter((suggestion) =>
    (!filter || suggestion.status === filter) && (!analysisId || suggestion.analise_id === analysisId)
  ), [data, filter, analysisId]);

  async function decide(suggestion, decision) {
    setBusyId(suggestion.id);
    setActionError('');
    try {
      const updated = await api.ia.decideSuggestion(suggestion.id, decision);
      setData((current) => current.map((item) => item.id === updated.id
        ? { ...item, ...updated, assunto_conversa: item.assunto_conversa, cliente_nome: item.cliente_nome }
        : item));
    } catch (reason) {
      setActionError(reason.message);
    } finally {
      setBusyId(null);
    }
  }

  function changeFilter(value) {
    setFilter(value);
    const next = {};
    if (value) next.status = value;
    if (analysisId) next.analise = String(analysisId);
    setSearchParams(next, { replace: true });
  }

  if (loading) return <div className="page-loading"><span className="spinner" />Carregando sugestões…</div>;
  if (error) return <section className="page-error"><h2>Não foi possível carregar as sugestões</h2><p>{error}</p><button className="button button-primary" onClick={refresh}>Tentar novamente</button></section>;

  return <div className="page-stack">
    <div className="page-heading"><div><span className="eyebrow">COPILOTO DE VENDAS</span><h1>Sugestões</h1><p>Revise as recomendações e registre a decisão da equipe.</p></div><label className="suggestion-filter">Filtrar por status<select value={filter} onChange={(event) => changeFilter(event.target.value)}><option value="">Todas</option><option value="pendente">Pendentes</option><option value="aceita">Aceitas</option><option value="rejeitada">Rejeitadas</option><option value="enviada">Enviadas</option></select></label></div>
    {analysisId && <div className="inline-warning" role="status">Exibindo sugestões da análise #{analysisId}. <button className="text-link" type="button" onClick={() => { setSearchParams(filter ? { status: filter } : {}, { replace: true }); }}>Limpar filtro</button></div>}
    {actionError && <div className="inline-error" role="alert">{actionError}</div>}
    {visible.length ? <div className="suggestion-list">{visible.map((suggestion) => <article className="surface suggestion-card" key={suggestion.id}>
      <div className="suggestion-kind-icon">{suggestion.tipo === 'produto' ? <Package size={17} /> : <MessageSquareText size={17} />}</div>
      <div className="suggestion-content"><div className="suggestion-meta"><span>{typeLabels[suggestion.tipo]} · Análise #{suggestion.analise_id}</span><span className={`suggestion-status suggestion-status-${suggestion.status}`}>{statusLabels[suggestion.status]}</span></div>
        <p>{suggestion.conteudo}</p><small>{suggestion.cliente_nome} · {suggestion.assunto_conversa} · {new Date(suggestion.criado_em).toLocaleString('pt-BR')}</small>
        {suggestion.decisoes.length > 0 && <div className="suggestion-decisions">{suggestion.decisoes.map((decision) => <span key={decision.id}>{statusLabels[decision.decisao] || decision.decisao} por {decision.decidido_por} · {new Date(decision.decidido_em).toLocaleString('pt-BR')}{decision.texto_enviado && decision.texto_enviado !== suggestion.conteudo ? ' · mensagem editada' : ''}</span>)}</div>}
      </div>
      {suggestion.status === 'pendente' && <div className="suggestion-actions"><button type="button" className="button button-secondary" disabled={busyId === suggestion.id} onClick={() => decide(suggestion, 'rejeitada')}><X size={14} /> Rejeitar</button><button type="button" className="button button-primary" disabled={busyId === suggestion.id} onClick={() => decide(suggestion, 'aceita')}><Check size={14} /> Aceitar</button></div>}
      <Link className="suggestion-open-link" aria-label="Abrir conversa" to={`/conversas?selected=${suggestion.conversa_id}`}><ArrowRight size={16} /></Link>
    </article>)}</div> : <div className="surface placeholder-state"><span className="placeholder-icon"><Sparkles size={22} /></span><h2>{filter === 'pendente' ? 'Tudo revisado por enquanto' : 'Nenhuma sugestão encontrada'}</h2><p>As sugestões serão registradas aqui após uma análise solicitada em uma conversa.</p><Link className="button button-primary" to="/conversas">Abrir conversas</Link></div>}
  </div>;
}
