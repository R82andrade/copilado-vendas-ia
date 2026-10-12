import React, { useMemo } from 'react';
import { ClipboardList, ShoppingBag } from 'lucide-react';
import { api } from '../services/api.js';
import { useApiData } from '../hooks/useApiData.js';

const money = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

async function loadOrders() {
  const [orders, clients, products] = await Promise.all([api.pedidos.list(), api.clientes.list(), api.produtos.list()]);
  return { orders, clients, products };
}

export function OrdersPage() {
  const { data, loading, error, refresh } = useApiData(loadOrders, []);
  const clients = useMemo(() => new Map((data?.clients || []).map((item) => [item.id, item.nome])), [data]);
  const products = useMemo(() => new Map((data?.products || []).map((item) => [item.id, item.nome])), [data]);
  if (loading) return <div className="page-loading"><span className="spinner" />Carregando pedidos…</div>;
  if (error) return <section className="page-error"><h2>Não foi possível carregar o histórico</h2><p>{error}</p><button className="button button-primary" onClick={refresh}>Tentar novamente</button></section>;
  const total = data.orders.reduce((sum, item) => sum + Number(item.total || 0), 0);
  return <div className="page-stack">
    <div className="page-heading"><div><span className="eyebrow">VENDAS</span><h1>Histórico de pedidos</h1><p>Pedidos registrados no sistema e seus itens.</p></div></div>
    <section className="metrics-grid order-metrics"><article className="metric-card"><div className="metric-icon blue"><ShoppingBag size={19} /></div><span className="metric-title">Pedidos registrados</span><strong className="metric-value">{data.orders.length}</strong><span className="metric-note">Total de pedidos na base</span></article><article className="metric-card"><div className="metric-icon green"><ClipboardList size={19} /></div><span className="metric-title">Valor total registrado</span><strong className="metric-value order-total">{money.format(total)}</strong><span className="metric-note">Soma dos pedidos existentes</span></article></section>
    <section className="surface table-surface"><div className="table-toolbar"><div><h2>Pedidos</h2><span>{data.orders.length} registros</span></div></div>{data.orders.length ? <div className="table-scroll"><table className="data-table"><thead><tr><th>Pedido</th><th>Cliente</th><th>Itens</th><th>Data</th><th>Total</th></tr></thead><tbody>{data.orders.slice().reverse().map((order) => <tr key={order.id}><td><b>#{order.id}</b></td><td>{clients.get(order.cliente_id) || `Cliente #${order.cliente_id}`}</td><td><span className="order-items">{order.itens.map((item) => `${products.get(item.produto_id) || `Produto #${item.produto_id}`} × ${item.quantidade}`).join(', ')}</span></td><td>{new Date(`${order.data_pedido}T12:00:00`).toLocaleDateString('pt-BR')}</td><td><b>{money.format(order.total)}</b></td></tr>)}</tbody></table></div> : <div className="empty-block"><ClipboardList size={24} /><b>Nenhum pedido registrado</b><span>O histórico será preenchido quando pedidos forem criados pela API.</span></div>}</section>
  </div>;
}
