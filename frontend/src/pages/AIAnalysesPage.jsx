import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Bot, Sparkles } from 'lucide-react';
import { useApiData } from '../hooks/useApiData.js';
import { api } from '../services/api.js';

const confidenceLabels = { baixa: 'Baixa', media: 'Média', alta: 'Alta' };

async function loadAiAnalysesPage() {
  const [analyses, status] = await Promise.all([api.ia.analyses(), api.ia.status()]);
  return { analyses, status };
}

export function AIAnalysesPage() {
  const { data, loading, error, refresh } = useApiData(loadAiAnalysesPage, []);

  if (loading) return <div className="page-loading"><span className="spinner" />Carregando análises…</div>;
  if (error) return <section className="page-error"><h2>Não foi possível carregar as análises</h2><p>{error}</p><button className="button button-primary" onClick={refresh}>Tentar novamente</button></section>;

  return <div className="page-stack">
    <div className="page-heading"><div><span className="eyebrow">COPILOTO DE VENDAS</span><h1>Análises da IA</h1><p>Histórico de análises geradas a partir dos atendimentos e dados comerciais.</p></div><span className="conversation-count"><Bot size={16} /> {data.analyses.length} análises registradas</span></div>
    {!data.status.configurada && <div className="inline-warning" role="status">A chave OPENAI_API_KEY não está configurada. Defina-a no arquivo .env e reinicie o backend para gerar análises.</div>}
    {data.analyses.length ? <div className="ai-analysis-history">{data.analyses.map((analysis) => <article className="surface ai-history-card" key={analysis.id}>
      <header className="ai-history-heading">
        <div><span className="eyebrow">ANÁLISE #{analysis.id} · {confidenceLabels[analysis.confianca] || analysis.confianca} confiança</span><h2>{analysis.cliente_nome} <span>· {analysis.assunto_conversa}</span></h2><p>{new Date(analysis.criado_em).toLocaleString('pt-BR')} · {analysis.criado_por} · {analysis.modelo}</p></div>
        <Link className="text-link" to={`/conversas?selected=${analysis.conversa_id}`}>Abrir conversa <ArrowRight size={15} /></Link>
      </header>
      <div className="ai-history-summary"><span><b>Intenção</b>{analysis.intencao}</span><span><b>Justificativa</b>{analysis.justificativa_intencao}</span></div>
      <div className="ai-history-columns">
        <section><h3>Objeções</h3>{analysis.objecoes.length ? <ul>{analysis.objecoes.map((item, index) => <li key={index}>{item}</li>)}</ul> : <p>Nenhuma objeção clara identificada.</p>}</section>
        <section><h3>Evidências</h3>{analysis.evidencias.length ? <ul>{analysis.evidencias.map((item, index) => <li key={index}>{item}</li>)}</ul> : <p>Sem evidências registradas.</p>}</section>
      </div>
      <section className="ai-history-reply"><h3><Sparkles size={14} /> Resposta sugerida</h3><p>{analysis.resposta_sugerida}</p></section>
      <footer className="ai-history-footer"><span>{analysis.sugestoes.length} sugestões geradas</span><Link className="text-link" to={`/sugestoes?analise=${analysis.id}`}>Ver decisões <ArrowRight size={15} /></Link></footer>
    </article>)}</div> : <div className="surface placeholder-state"><span className="placeholder-icon"><Bot size={22} /></span><h2>Nenhuma análise registrada</h2><p>Abra uma conversa com mensagens e solicite uma análise no painel Copiloto IA. Cada resultado será salvo aqui.</p><Link className="button button-primary" to="/conversas">Abrir conversas</Link></div>}
  </div>;
}
