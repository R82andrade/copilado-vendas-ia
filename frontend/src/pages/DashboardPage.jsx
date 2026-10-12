import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight, ArrowUpRight, Bot, Boxes, CheckCheck, ClipboardList,
  MessageSquareText, Package, ShoppingBag, Sparkles, Users,
} from 'lucide-react';
import {
  Area, AreaChart, CartesianGrid, Line, LineChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts';
import { api } from '../services/api.js';
import { useApiData } from '../hooks/useApiData.js';
import { MetricCard } from '../components/MetricCard.jsx';

const PERIODS = [
  { value: 7, label: '7 dias' },
  { value: 30, label: '30 dias' },
  { value: 90, label: '90 dias' },
  { value: 365, label: '12 meses' },
];
const LOW_STOCK_LIMIT = 10;
const money = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

async function loadDashboard() {
  const resources = await Promise.allSettled([
    api.clientes.list(), api.conversas.list(), api.produtos.list(), api.pedidos.list(),
    api.ia.analyses(), api.ia.suggestions(),
  ]);
  const [clientes, conversas, produtos, pedidos, analises, sugestoes] = resources.map((result) => result.status === 'fulfilled' ? result.value : null);
  return {
    clientes, conversas, produtos, pedidos, analises, sugestoes,
    partialError: resources.some((result) => result.status === 'rejected'),
  };
}

function parseDate(value) {
  if (!value) return null;
  const date = /^\d{4}-\d{2}-\d{2}$/.test(value)
    ? new Date(`${value}T00:00:00`)
    : new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function inRange(value, start, end) {
  const date = parseDate(value);
  return date !== null && date >= start && date < end;
}

function sumOrders(orders) {
  return orders.reduce((total, order) => total + Number(order.total || 0), 0);
}

function countByDate(items, field, start, end, days) {
  if (days === 365) {
    const buckets = [];
    const cursor = new Date(start.getFullYear(), start.getMonth(), 1);
    while (cursor < end) {
      buckets.push({
        key: `${cursor.getFullYear()}-${String(cursor.getMonth() + 1).padStart(2, '0')}`,
        label: new Intl.DateTimeFormat('pt-BR', { month: 'short' }).format(cursor).replace('.', ''),
        total: 0,
      });
      cursor.setMonth(cursor.getMonth() + 1);
    }
    const lookup = new Map(buckets.map((bucket) => [bucket.key, bucket]));
    for (const item of items) {
      const date = parseDate(item[field]);
      if (!date || date < start || date >= end) continue;
      const bucket = lookup.get(`${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`);
      if (bucket) bucket.total += 1;
    }
    return buckets;
  }

  const bucketSize = days === 90 ? 7 : 1;
  const bucketCount = Math.ceil(days / bucketSize);
  const buckets = Array.from({ length: bucketCount }, (_, index) => {
    const bucketStart = new Date(start.getTime() + index * bucketSize * 24 * 60 * 60 * 1000);
    const label = days === 90
      ? new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short' }).format(bucketStart).replace('.', '')
      : new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short' }).format(bucketStart).replace('.', '');
    return { start: bucketStart, label, total: 0 };
  });
  for (const item of items) {
    const date = parseDate(item[field]);
    if (!date || date < start || date >= end) continue;
    const index = Math.floor((date.getTime() - start.getTime()) / (bucketSize * 24 * 60 * 60 * 1000));
    if (buckets[index]) buckets[index].total += 1;
  }
  return buckets;
}

function compareNote(current, previous, formatter = (value) => String(value)) {
  const difference = current - previous;
  if (difference === 0) return 'Sem variação vs. período anterior';
  return `${difference > 0 ? '+' : '−'}${formatter(Math.abs(difference))} vs. período anterior`;
}

function periodMetrics(data, start, end, previousStart) {
  const previousEnd = start;
  const currentClients = (data.clientes || []).filter((item) => inRange(item.data_cadastro, start, end));
  const previousClients = (data.clientes || []).filter((item) => inRange(item.data_cadastro, previousStart, previousEnd));
  const currentConversations = (data.conversas || []).filter((item) => inRange(item.data_criacao, start, end));
  const previousConversations = (data.conversas || []).filter((item) => inRange(item.data_criacao, previousStart, previousEnd));
  const currentOrders = (data.pedidos || []).filter((item) => inRange(item.data_pedido, start, end));
  const previousOrders = (data.pedidos || []).filter((item) => inRange(item.data_pedido, previousStart, previousEnd));
  const currentAnalyses = (data.analises || []).filter((item) => inRange(item.criado_em, start, end));
  const previousAnalyses = (data.analises || []).filter((item) => inRange(item.criado_em, previousStart, previousEnd));
  const currentDecisions = (data.sugestoes || []).flatMap((suggestion) =>
    (suggestion.decisoes || []).filter((decision) => inRange(decision.decidido_em, start, end)));
  const previousDecisions = (data.sugestoes || []).flatMap((suggestion) =>
    (suggestion.decisoes || []).filter((decision) => inRange(decision.decidido_em, previousStart, previousEnd)));

  function conversion(conversations, orders) {
    const attendedClients = new Set(conversations.map((item) => item.cliente_id));
    const purchasingClients = new Set(orders.filter((item) => attendedClients.has(item.cliente_id)).map((item) => item.cliente_id));
    return { rate: attendedClients.size ? (purchasingClients.size / attendedClients.size) * 100 : 0, attended: attendedClients.size, purchasing: purchasingClients.size };
  }

  return {
    currentClients, previousClients, currentConversations, previousConversations,
    currentOrders, previousOrders, currentAnalyses, previousAnalyses,
    currentDecisions, previousDecisions,
    currentRevenue: sumOrders(currentOrders),
    previousRevenue: sumOrders(previousOrders),
    currentConversion: conversion(currentConversations, currentOrders),
    previousConversion: conversion(previousConversations, previousOrders),
  };
}

function ChartEmpty({ message = 'Os dados aparecem aqui quando houver registros no período.' }) {
  return <div className="chart-empty">{message}</div>;
}

function decisionLabel(decision) {
  return { aceita: 'aceitou sugestão', rejeitada: 'rejeitou sugestão', enviada: 'enviou resposta sugerida' }[decision] || decision;
}

export function DashboardPage() {
  const { data, loading, error, refresh } = useApiData(loadDashboard, []);
  const [days, setDays] = useState(30);
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const timer = window.setInterval(() => {
      setNow(new Date());
      refresh();
    }, 60_000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const windowDates = useMemo(() => {
    const end = new Date(now);
    const start = new Date(end.getTime() - days * 24 * 60 * 60 * 1000);
    const previousStart = new Date(start.getTime() - days * 24 * 60 * 60 * 1000);
    return { start, end, previousStart };
  }, [now, days]);

  if (loading) return <div className="page-loading"><span className="spinner" />Carregando dados reais do painel…</div>;
  if (error) return <section className="page-error"><h2>Não foi possível abrir o painel</h2><p>{error}</p><button className="button button-primary" onClick={refresh}>Tentar novamente</button></section>;

  const clients = data.clientes || [];
  const conversations = data.conversas || [];
  const products = data.produtos || [];
  const orders = data.pedidos || [];
  const analytics = data.analises || [];
  const suggestions = data.sugestoes || [];
  const activeConversations = conversations.filter((item) => item.status !== 'finalizada');
  const lowStockProducts = products.filter((product) => Number(product.estoque) <= LOW_STOCK_LIMIT);
  const metrics = periodMetrics(data, windowDates.start, windowDates.end, windowDates.previousStart);
  const customerChart = countByDate(clients, 'data_cadastro', windowDates.start, windowDates.end, days);
  const conversationChart = countByDate(conversations, 'data_criacao', windowDates.start, windowDates.end, days);
  const hasCustomerHistory = customerChart.some((item) => item.total > 0);
  const hasConversationHistory = conversationChart.some((item) => item.total > 0);
  const clientNames = new Map(clients.map((client) => [client.id, client.nome]));
  const pendingSuggestions = suggestions.filter((suggestion) => suggestion.status === 'pendente');
  const ticketAverage = metrics.currentOrders.length ? metrics.currentRevenue / metrics.currentOrders.length : null;
  const previousTicketAverage = metrics.previousOrders.length ? metrics.previousRevenue / metrics.previousOrders.length : null;

  const activities = [
    ...conversations.filter((item) => inRange(item.ultima_atualizacao, windowDates.start, windowDates.end)).map((item) => ({
      key: `conversation-${item.id}`,
      date: parseDate(item.ultima_atualizacao),
      label: clientNames.get(item.cliente_id) || `Cliente #${item.cliente_id}`,
      detail: `${item.assunto} · conversa ${item.status.replaceAll('_', ' ')}`,
      to: `/conversas?selected=${item.id}`,
      icon: MessageSquareText,
      kind: 'Conversa',
    })),
    ...orders.filter((item) => inRange(item.data_pedido, windowDates.start, windowDates.end)).map((item) => ({
      key: `order-${item.id}`,
      date: parseDate(item.data_pedido),
      label: clientNames.get(item.cliente_id) || `Cliente #${item.cliente_id}`,
      detail: `Pedido #${item.id} · ${money.format(item.total)}`,
      to: '/historico',
      icon: ShoppingBag,
      kind: 'Pedido',
    })),
    ...suggestions.flatMap((suggestion) => (suggestion.decisoes || [])
      .filter((decision) => inRange(decision.decidido_em, windowDates.start, windowDates.end))
      .map((decision) => ({
        key: `decision-${decision.id}`,
        date: parseDate(decision.decidido_em),
        label: decision.decidido_por,
        detail: `${decisionLabel(decision.decisao)} · ${suggestion.conteudo}`,
        to: `/sugestoes?analise=${suggestion.analise_id}`,
        icon: CheckCheck,
        kind: 'Decisão IA',
      }))),
  ].sort((a, b) => b.date - a.date).slice(0, 8);

  const analysisCountNote = data.analises
    ? compareNote(metrics.currentAnalyses.length, metrics.previousAnalyses.length)
    : 'Indisponível';
  const decisionCountNote = data.sugestoes
    ? `${metrics.currentDecisions.filter((item) => item.decisao === 'aceita').length} aceitas · ${metrics.currentDecisions.filter((item) => item.decisao === 'rejeitada').length} rejeitadas · ${metrics.currentDecisions.filter((item) => item.decisao === 'enviada').length} enviadas · ${pendingSuggestions.length} pendentes`
    : 'Indisponível';

  return <div className="page-stack">
    <div className="page-heading dashboard-heading">
      <div><span className="eyebrow">VISÃO GERAL</span><h1>Bom dia. Vamos vender melhor?</h1><p>Indicadores comerciais calculados a partir dos registros da equipe.</p></div>
      <div className="dashboard-controls">
        <label className="dashboard-period">Período
          <select value={days} onChange={(event) => setDays(Number(event.target.value))}>
            {PERIODS.map((period) => <option key={period.value} value={period.value}>{period.label}</option>)}
          </select>
        </label>
        <button className="button button-secondary" onClick={() => { setNow(new Date()); refresh(); }}>Atualizar painel</button>
      </div>
    </div>
    <p className="dashboard-comparison-note">Período atual comparado aos {PERIODS.find((period) => period.value === days)?.label} imediatamente anteriores. Conversão considera clientes com conversa e pedido no período, associados pelo cadastro do cliente. Atualização automática a cada minuto.</p>
    {data.partialError && <div className="inline-warning" role="status">Alguns indicadores não carregaram. Confira a conexão; os dados indisponíveis aparecem como traço.</div>}

    <section className="metrics-grid dashboard-metrics" aria-label="Indicadores comerciais">
      <MetricCard title="Clientes cadastrados" value={data.clientes ? clients.length : '—'} note="Total na base" icon={Users} />
      <MetricCard title="Novos clientes" value={data.clientes ? metrics.currentClients.length : '—'} note={data.clientes ? compareNote(metrics.currentClients.length, metrics.previousClients.length) : 'Indisponível'} icon={ArrowUpRight} tone="green" />
      <MetricCard title="Conversas iniciadas" value={data.conversas ? metrics.currentConversations.length : '—'} note={data.conversas ? compareNote(metrics.currentConversations.length, metrics.previousConversations.length) : 'Indisponível'} icon={MessageSquareText} tone="orange" />
      <MetricCard title="Pedidos no período" value={data.pedidos ? metrics.currentOrders.length : '—'} note={data.pedidos ? `${money.format(metrics.currentRevenue)} · ${compareNote(metrics.currentOrders.length, metrics.previousOrders.length)}` : 'Indisponível'} icon={ShoppingBag} tone="violet" />
      <MetricCard title="Conversão de clientes atendidos" value={data.conversas && data.pedidos && metrics.currentConversion.attended ? `${metrics.currentConversion.rate.toFixed(1)}%` : '—'} note={data.conversas && data.pedidos ? metrics.currentConversion.attended ? `${metrics.currentConversion.purchasing}/${metrics.currentConversion.attended} clientes · ${compareNote(metrics.currentConversion.rate, metrics.previousConversion.rate, (value) => `${value.toFixed(1)} p.p.`)}` : 'Sem clientes atendidos no período' : 'Indisponível'} icon={ArrowUpRight} tone="green" />
      <MetricCard title="Ticket médio" value={data.pedidos ? ticketAverage === null ? '—' : money.format(ticketAverage) : '—'} note={data.pedidos ? ticketAverage === null ? 'Nenhum pedido no período' : previousTicketAverage === null ? 'Sem pedidos no período anterior' : compareNote(ticketAverage, previousTicketAverage, (value) => money.format(value)) : 'Indisponível'} icon={ClipboardList} tone="violet" />
      <MetricCard title="Estoque baixo" value={data.produtos ? lowStockProducts.length : '—'} note={`Produtos com até ${LOW_STOCK_LIMIT} unidades`} icon={Boxes} tone="orange" />
      <MetricCard title="Análises da IA" value={data.analises ? metrics.currentAnalyses.length : '—'} note={analysisCountNote} icon={Bot} tone="violet" />
      <MetricCard title="Decisões da IA" value={data.sugestoes ? metrics.currentDecisions.length : '—'} note={decisionCountNote} icon={Sparkles} tone="orange" />
    </section>

    <section className="dashboard-charts">
      <article className="surface chart-card">
        <div className="section-heading"><div><h2>Novos clientes</h2><p>Cadastros · {PERIODS.find((period) => period.value === days)?.label}</p></div><span className="chart-legend"><i className="legend-dot blue" /> Clientes</span></div>
        {!data.clientes ? <ChartEmpty message="Não foi possível carregar os clientes." /> : hasCustomerHistory ? <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><AreaChart data={customerChart} margin={{ top: 8, right: 12, bottom: 0, left: -20 }}>
          <defs><linearGradient id="clientFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#3978f6" stopOpacity={0.2} /><stop offset="100%" stopColor="#3978f6" stopOpacity={0.01} /></linearGradient></defs><CartesianGrid stroke="#edf1f5" vertical={false} /><XAxis dataKey="label" interval={days === 30 ? 4 : days === 365 ? 1 : 0} axisLine={false} tickLine={false} tick={{ fill: '#8995a5', fontSize: 11 }} /><YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={{ fill: '#8995a5', fontSize: 12 }} /><Tooltip contentStyle={{ border: '1px solid #e7ebf0', borderRadius: 10 }} /><Area type="monotone" dataKey="total" name="Clientes" stroke="#3978f6" strokeWidth={2.5} fill="url(#clientFill)" />
        </AreaChart></ResponsiveContainer></div> : <ChartEmpty />}
      </article>
      <article className="surface chart-card">
        <div className="section-heading"><div><h2>Conversas iniciadas</h2><p>Atendimentos · {PERIODS.find((period) => period.value === days)?.label}</p></div><span className="chart-legend"><i className="legend-dot mint" /> Conversas</span></div>
        {!data.conversas ? <ChartEmpty message="Não foi possível carregar as conversas." /> : hasConversationHistory ? <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><LineChart data={conversationChart} margin={{ top: 8, right: 12, bottom: 0, left: -20 }}>
          <CartesianGrid stroke="#edf1f5" vertical={false} /><XAxis dataKey="label" interval={days === 30 ? 4 : days === 365 ? 1 : 0} axisLine={false} tickLine={false} tick={{ fill: '#8995a5', fontSize: 11 }} /><YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={{ fill: '#8995a5', fontSize: 12 }} /><Tooltip contentStyle={{ border: '1px solid #e7ebf0', borderRadius: 10 }} /><Line type="monotone" dataKey="total" name="Conversas" stroke="#15ad8c" strokeWidth={2.5} dot={{ r: 3, fill: '#15ad8c', strokeWidth: 0 }} />
        </LineChart></ResponsiveContainer></div> : <ChartEmpty />}
      </article>
    </section>

    <section className="dashboard-bottom dashboard-activity-grid">
      <article className="surface activity-card">
        <div className="section-heading"><div><h2>Atividade recente</h2><p>Conversas, pedidos e decisões · {PERIODS.find((period) => period.value === days)?.label}</p></div><Link className="text-link" to="/conversas">Ver conversas <ArrowRight size={15} /></Link></div>
        {activities.length ? <div className="activity-list">{activities.map((activity) => {
          const Icon = activity.icon;
          return <Link to={activity.to} className="activity-row dashboard-activity-row" key={activity.key}>
            <span className="activity-avatar"><Icon size={15} /></span>
            <span className="activity-copy"><b>{activity.label}</b><small>{activity.detail}</small></span>
            <span className="dashboard-activity-meta"><span>{activity.kind}</span><time>{activity.date.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })}</time></span>
          </Link>;
        })}</div> : <div className="empty-block"><MessageSquareText size={21} /><b>Nenhuma atividade no período</b><span>Conversas, pedidos e decisões recentes aparecerão aqui.</span></div>}
      </article>
      <article className="surface products-card">
        <div className="section-heading"><div><h2>Estoque baixo</h2><p>Até {LOW_STOCK_LIMIT} unidades disponíveis</p></div><Package size={18} className="muted-icon" /></div>
        {data.produtos ? lowStockProducts.length ? <div className="low-stock-list">{lowStockProducts.slice(0, 6).map((product) => <Link to="/produtos" className="low-stock-row" key={product.id}><span><b>{product.nome}</b><small>{product.marca} · {product.categoria}</small></span><strong className={Number(product.estoque) === 0 ? 'out-of-stock' : ''}>{product.estoque} un.</strong></Link>)}</div> : <div className="empty-block low-stock-empty"><Package size={20} /><b>Nenhum alerta de estoque</b><span>Todos os produtos têm mais de {LOW_STOCK_LIMIT} unidades.</span></div> : <ChartEmpty message="Não foi possível carregar os produtos." />}
        <Link className="text-link" to="/produtos">Abrir catálogo <ArrowRight size={15} /></Link>
      </article>
    </section>
  </div>;
}
