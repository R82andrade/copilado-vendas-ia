import React from 'react';
import { Construction } from 'lucide-react';

export function PlaceholderPage({ title }) {
  return <section className="page-stack">
    <div className="page-heading"><div><span className="eyebrow">COPILOTO DE VENDAS</span><h1>{title}</h1><p>Esta área será conectada aos recursos disponíveis no backend.</p></div></div>
    <div className="surface placeholder-state"><span className="placeholder-icon"><Construction size={22} /></span><h2>Em preparação</h2><p>Não exibimos informações demonstrativas como se fossem dados reais.</p></div>
  </section>;
}
