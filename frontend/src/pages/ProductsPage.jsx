import React, { useMemo, useState } from 'react';
import { CirclePlus, Package, Pencil, Search, Scale, Trash2, Calculator, Settings2 } from 'lucide-react';
import { api } from '../services/api.js';
import { useApiData } from '../hooks/useApiData.js';

const blank = { nome: '', marca: '', categoria: '', preco: '', estoque: '', desconto_maximo: '' };
const currency = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

function parseCatalogPrice(value) {
  const normalized = value.trim().replace(/\s/g, '').replace(/^R\$/i, '');
  const decimal = normalized.includes(',')
    ? normalized.replace(/\./g, '').replace(',', '.')
    : normalized;
  return Number(decimal);
}

function discountedPrice(price, discountPercent) {
  return Math.round((price * (1 - discountPercent / 100) + Number.EPSILON) * 100) / 100;
}

function ProductForm({ product, onClose, onSave, busy }) {
  const [priceError, setPriceError] = useState('');

  async function submit(event) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    const price = parseCatalogPrice(values.get('preco'));
    if (!Number.isFinite(price) || price <= 0) {
      setPriceError('Informe um preço válido maior que zero.');
      return;
    }
    setPriceError('');
    await onSave({
      nome: values.get('nome').trim(), marca: values.get('marca').trim(), categoria: values.get('categoria').trim(),
      preco: price, estoque: Number(values.get('estoque')), desconto_maximo: Number(values.get('desconto_maximo')),
    });
  }
  return <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><section className="modal-card" role="dialog" aria-modal="true" aria-labelledby="product-title">
    <div className="modal-heading"><div><span className="eyebrow">CATÁLOGO</span><h2 id="product-title">{product ? 'Editar produto' : 'Novo produto'}</h2></div><button className="icon-button close-button" type="button" onClick={onClose} aria-label="Fechar">×</button></div>
    <form key={product?.id || 'new-product'} className="client-form" onSubmit={submit}>
      <label>Nome do produto<input name="nome" required minLength="2" maxLength="150" defaultValue={product?.nome || ''} autoFocus /></label>
      <div className="form-two-col"><label>Marca<input name="marca" required minLength="2" maxLength="100" defaultValue={product?.marca || ''} /></label><label>Categoria<input name="categoria" required minLength="2" maxLength="100" defaultValue={product?.categoria || ''} /></label></div>
      <div className="form-two-col"><label>Preço (R$)<input name="preco" type="text" inputMode="decimal" required placeholder="Ex.: 129,90" defaultValue={product?.preco != null ? String(product.preco).replace('.', ',') : ''} /></label><label>Estoque<input name="estoque" type="number" required min="0" step="1" defaultValue={product?.estoque ?? 0} /></label></div>
      {priceError && <div className="inline-error" role="alert">{priceError}</div>}
      <label>Desconto máximo (%)<input name="desconto_maximo" type="number" required min="0" max="100" step="0.01" defaultValue={product?.desconto_maximo ?? 0} /></label>
      <div className="modal-actions"><button type="button" className="button button-secondary" onClick={onClose}>Cancelar</button><button className="button button-primary" disabled={busy}>{busy ? 'Salvando…' : 'Salvar produto'}</button></div>
    </form>
  </section></div>;
}

function financialValue(value) {
  return value == null ? '' : String(value).replace('.', ',');
}

function FinanceModal({ product, account, onClose }) {
  const [data, setData] = useState(null);
  const [discount, setDiscount] = useState('0');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [recommendation, setRecommendation] = useState('');
  const isAdmin = account.role === 'admin';
  const fields = data?.dados_financeiros || {};

  React.useEffect(() => {
    api.financeiro.product(product.id).then(setData).catch((reason) => setError(reason.message)).finally(() => setLoading(false));
  }, [product.id]);

  async function saveFinancial(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const money = (name) => form.get(name).trim() ? parseCatalogPrice(form.get(name)) : null;
    const percent = (name) => form.get(name).trim() ? Number(String(form.get(name)).replace(',', '.')) : null;
    setBusy(true); setError('');
    try {
      await api.financeiro.updateProduct(product.id, {
        custo_aquisicao: money('custo_aquisicao'),
        outros_custos_variaveis: money('outros_custos_variaveis'),
        margem_contribuicao_minima: percent('margem_contribuicao_minima'),
        limite_desconto_comercial: percent('limite_desconto_comercial'),
      });
      setData(await api.financeiro.product(product.id));
    } catch (reason) { setError(reason.message); }
    finally { setBusy(false); }
  }

  async function runSimulation(event) {
    event.preventDefault(); setBusy(true); setError(''); setRecommendation('');
    try { setResult(await api.financeiro.simulate(product.id, { desconto_percentual: Number(discount.replace(',', '.')) })); }
    catch (reason) { setError(reason.message); }
    finally { setBusy(false); }
  }

  async function askCopilot() {
    setBusy(true); setError(''); setRecommendation('');
    try {
      const answer = await api.iaFinanceiro.recommend(product.id, discount);
      setRecommendation(answer.recomendacao);
      if (answer.fatos_calculados) setResult(answer.fatos_calculados);
    } catch (reason) { setError(reason.message); }
    finally { setBusy(false); }
  }

  const amount = (value) => value == null ? '—' : currency.format(Number(value));
  const percentLabel = (value) => value == null ? '—' : `${value}%`;

  return <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
    <section className="modal-card financial-modal" role="dialog" aria-modal="true" aria-labelledby="finance-title">
      <div className="modal-heading"><div><span className="eyebrow">ANÁLISE COMERCIAL</span><h2 id="finance-title">{product.nome}</h2></div><button className="icon-button close-button" type="button" onClick={onClose} aria-label="Fechar">×</button></div>
      {loading ? <div className="page-loading"><span className="spinner" />Carregando dados financeiros…</div> : <>
        {error && <div className="inline-error" role="alert">{error}</div>}
        {isAdmin && <form className="client-form financial-edit-form" onSubmit={saveFinancial}>
          <h3>Custos e limites do produto</h3>
          <div className="form-two-col"><label>Custo de aquisição (R$)<input name="custo_aquisicao" inputMode="decimal" defaultValue={financialValue(fields.custo_aquisicao)} placeholder="Obrigatório para calcular" /></label><label>Outros custos variáveis (R$)<input name="outros_custos_variaveis" inputMode="decimal" defaultValue={financialValue(fields.outros_custos_variaveis)} placeholder="Informe 0 se não houver" /></label></div>
          <div className="form-two-col"><label>Margem mínima (%)<input name="margem_contribuicao_minima" type="number" min="0" max="99.99" step="0.01" defaultValue={financialValue(fields.margem_contribuicao_minima)} placeholder="Usa padrão da loja" /></label><label>Limite comercial (%)<input name="limite_desconto_comercial" type="number" min="0" max="100" step="0.01" defaultValue={financialValue(fields.limite_desconto_comercial)} placeholder="Usa padrão da loja" /></label></div>
          <small>Deixe em branco para herdar o padrão da loja. Para custos, informe 0 somente quando confirmado.</small>
          <button className="button button-secondary" disabled={busy}>{busy ? 'Salvando…' : 'Salvar dados financeiros'}</button>
        </form>}
        <form className="comparison-search finance-simulation-form" onSubmit={runSimulation}>
          <label htmlFor="finance-discount">Simular desconto (%)</label><div className="comparison-own-price-edit"><input id="finance-discount" type="number" min="0" max="100" step="0.01" value={discount} onChange={(event) => setDiscount(event.target.value)} /><button className="button button-primary" disabled={busy}>{busy ? 'Calculando…' : 'Simular'}</button></div>
        </form>
        {data?.situacao === 'dados_insuficientes' && <div className="inline-warning" role="status">Faltam dados para calcular: {data.dados_ausentes.join(', ')}. O responsável comercial deve informar os valores ausentes.</div>}
        {result && <section className={`finance-result finance-${result.situacao}`} aria-live="polite">
          <strong>{result.situacao === 'permitida' ? 'Desconto permitido' : result.situacao === 'bloqueada' ? 'Desconto bloqueado' : 'Dados insuficientes'}</strong>
          {result.motivo && <p>{result.motivo}</p>}
          {result.dados_ausentes?.length > 0 && <p>Dados ausentes: {result.dados_ausentes.join(', ')}</p>}
          <dl><div><dt>Preço original</dt><dd>{amount(result.preco_original)}</dd></div><div><dt>Desconto</dt><dd>{percentLabel(result.desconto_percentual)} · {amount(result.valor_desconto)}</dd></div><div><dt>Preço final</dt><dd>{amount(result.preco_final)}</dd></div><div><dt>Custo de aquisição</dt><dd>{amount(result.custo_aquisicao)}</dd></div><div><dt>Outros custos variáveis</dt><dd>{amount(result.outros_custos_variaveis)}</dd></div><div><dt>Impostos e comissões</dt><dd>{amount(result.imposto_variavel_valor)} + {amount(result.comissao_valor)}</dd></div><div><dt>Lucro bruto</dt><dd>{amount(result.lucro_bruto)} · {percentLabel(result.margem_bruta_percentual)}</dd></div><div><dt>Contribuição estimada</dt><dd>{amount(result.contribuicao_unitaria)} · {percentLabel(result.margem_contribuicao_percentual)}</dd></div><div><dt>Preço mínimo</dt><dd>{amount(result.preco_minimo)}</dd></div><div><dt>Limite permitido</dt><dd>{percentLabel(result.limite_permitido_desconto_percentual)}</dd></div></dl>
        </section>}
        {account.role === 'admin' || account.role === 'vendas' ? <button className="button button-secondary finance-ai-button" type="button" onClick={askCopilot} disabled={busy}><Calculator size={15} />Explicar com Copiloto</button> : null}
        {recommendation && <div className="inline-success finance-recommendation"><b>Sugestão para revisão humana</b><p>{recommendation}</p></div>}
        <p className="comparison-disclaimer">Estimativas por unidade; não representam lucro líquido e dependem dos custos e percentuais informados.</p>
      </>}
    </section>
  </div>;
}

function FinanceConfigModal({ onClose }) {
  const [config, setConfig] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  React.useEffect(() => { api.financeiro.config().then(setConfig).catch((reason) => setError(reason.message)).finally(() => setLoaded(true)); }, []);
  async function submit(event) {
    event.preventDefault(); const form = new FormData(event.currentTarget); setBusy(true); setError('');
    const pct = (name) => String(form.get(name)).trim() ? Number(String(form.get(name)).replace(',', '.')) : null;
    try { setConfig(await api.financeiro.updateConfig({
      imposto_variavel_percentual: pct('imposto_variavel_percentual'),
      comissao_percentual: pct('comissao_percentual'),
      margem_contribuicao_minima: pct('margem_contribuicao_minima'),
      limite_desconto_comercial: pct('limite_desconto_comercial'),
    })); }
    catch (reason) { setError(reason.message); }
    finally { setBusy(false); }
  }
  return <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><section className="modal-card" role="dialog" aria-modal="true" aria-labelledby="finance-config-title">
    <div className="modal-heading"><div><span className="eyebrow">ADMINISTRAÇÃO</span><h2 id="finance-config-title">Política financeira da loja</h2></div><button className="icon-button close-button" type="button" onClick={onClose} aria-label="Fechar">×</button></div>
    {error && <div className="inline-error" role="alert">{error}</div>}
    {!loaded ? <div className="page-loading"><span className="spinner" />Carregando configuração…</div> : <form className="client-form" onSubmit={submit}><div className="form-two-col"><label>Impostos variáveis (%)<input name="imposto_variavel_percentual" type="number" min="0" max="100" step="0.01" defaultValue={financialValue(config?.imposto_variavel_percentual)} required /></label><label>Comissão (%)<input name="comissao_percentual" type="number" min="0" max="100" step="0.01" defaultValue={financialValue(config?.comissao_percentual)} required /></label></div><div className="form-two-col"><label>Margem mínima padrão (%)<input name="margem_contribuicao_minima" type="number" min="0" max="99.99" step="0.01" defaultValue={financialValue(config?.margem_contribuicao_minima)} required /></label><label>Limite comercial padrão (%)<input name="limite_desconto_comercial" type="number" min="0" max="100" step="0.01" defaultValue={financialValue(config?.limite_desconto_comercial)} required /></label></div><small>Confirme alíquotas e comissões com o responsável comercial ou contador.</small><div className="modal-actions"><button type="button" className="button button-secondary" onClick={onClose}>Fechar</button><button className="button button-primary" disabled={busy}>{busy ? 'Salvando…' : 'Salvar política'}</button></div></form>}
  </section></div>;
}

export function ProductsPage({ account = { role: 'leitor' } }) {
  const { data, loading, error, refresh } = useApiData(api.produtos.list, []);
  const [query, setQuery] = useState('');
  const [editing, setEditing] = useState(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState('');
  const [notice, setNotice] = useState('');
  const [comparison, setComparison] = useState(null);
  const [comparisonPrice, setComparisonPrice] = useState('');
  const [comparisonPriceError, setComparisonPriceError] = useState('');
  const [comparisonPriceBusy, setComparisonPriceBusy] = useState(false);
  const [comparisonQuery, setComparisonQuery] = useState('');
  const [financeProduct, setFinanceProduct] = useState(null);
  const [financeConfigOpen, setFinanceConfigOpen] = useState(false);
  const rows = useMemo(() => (data || []).filter((item) => `${item.nome} ${item.marca} ${item.categoria}`.toLowerCase().includes(query.toLowerCase())), [data, query]);

  async function save(form) {
    setBusy(true); setActionError('');
    try {
      if (editing?.id) await api.produtos.update(editing.id, form);
      else await api.produtos.create(form);
      setEditing(null); setNotice(editing ? 'Produto atualizado.' : 'Produto cadastrado.'); await refresh();
    } catch (reason) { setActionError(reason.message); }
    finally { setBusy(false); }
  }
  async function remove(product) {
    if (!window.confirm(`Excluir ${product.nome} do catálogo?`)) return;
    setActionError('');
    try { await api.produtos.remove(product.id); setNotice('Produto excluído.'); await refresh(); }
    catch (reason) { setActionError(reason.message); }
  }

  function openComparison(product) {
    setComparison(product);
    setComparisonPrice(String(product.preco).replace('.', ','));
    setComparisonPriceError('');
    setComparisonQuery(`${product.marca} ${product.nome}`.trim());
  }

  async function saveComparisonPrice(event) {
    event.preventDefault();
    const price = parseCatalogPrice(comparisonPrice);
    if (!Number.isFinite(price) || price <= 0) {
      setComparisonPriceError('Informe um preço válido maior que zero.');
      return;
    }
    setComparisonPriceBusy(true);
    setComparisonPriceError('');
    setActionError('');
    try {
      const updated = await api.produtos.update(comparison.id, {
        nome: comparison.nome,
        marca: comparison.marca,
        categoria: comparison.categoria,
        preco: price,
        estoque: comparison.estoque,
        desconto_maximo: comparison.desconto_maximo,
      });
      setComparison(updated);
      setComparisonPrice(String(updated.preco).replace('.', ','));
      setNotice('Preço do produto atualizado no catálogo.');
      await refresh();
    } catch (reason) {
      setComparisonPriceError(reason.message);
    } finally {
      setComparisonPriceBusy(false);
    }
  }

  const encodedSearch = encodeURIComponent(comparisonQuery.trim());
  const marketplaceSearchLinks = [
    { name: 'Google Shopping', url: `https://www.google.com/search?tbm=shop&q=${encodedSearch}` },
    { name: 'Amazon Brasil', url: `https://www.amazon.com.br/s?k=${encodedSearch}` },
    { name: 'Magalu', url: `https://www.magazineluiza.com.br/busca/${encodedSearch}/` },
    { name: 'Shopee', url: `https://shopee.com.br/search?keyword=${encodedSearch}` },
    { name: 'Mercado Livre', url: `https://lista.mercadolivre.com.br/${encodedSearch}` },
  ];
  const comparisonBasePrice = parseCatalogPrice(comparisonPrice);

  return <div className="page-stack">
    <div className="page-heading"><div><span className="eyebrow">OPERAÇÃO COMERCIAL</span><h1>Catálogo de produtos</h1><p>Preços, estoque e descontos usados pela equipe.</p></div><div className="catalog-heading-actions">{account.role === 'admin' && <button className="button button-secondary" onClick={() => setFinanceConfigOpen(true)}><Settings2 size={16} /> Política financeira</button>}<button className="button button-primary" onClick={() => { setEditing({ ...blank }); setActionError(''); }}><CirclePlus size={17} /> Novo produto</button></div></div>
    <section className="surface table-surface"><div className="table-toolbar"><div><h2>Produtos cadastrados</h2><span>{loading ? 'Carregando…' : `${data?.length ?? 0} itens`}</span></div><label className="table-search"><Search size={16} /><span className="sr-only">Buscar produto</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar no catálogo" /></label></div>
      {notice && <div className="inline-success">{notice}</div>}{(error || actionError) && <div className="inline-error" role="alert">{error || actionError}</div>}
      {loading ? <div className="page-loading"><span className="spinner" />Carregando catálogo…</div> : rows.length ? <div className="table-scroll"><table className="data-table"><thead><tr><th>Produto</th><th>Categoria</th><th>Preço</th><th>Preço com desconto</th><th>Estoque</th><th>Desconto máx.</th><th><span className="sr-only">Ações</span></th></tr></thead><tbody>{rows.map((item) => <tr key={item.id}>
        <td><span className="client-name-cell"><span className="table-avatar"><Package size={15} /></span><span><b>{item.nome}</b><small>{item.marca}</small></span></span></td><td>{item.categoria}</td><td><b>{currency.format(item.preco)}</b></td><td><span className="discounted-price-cell"><b>{currency.format(discountedPrice(item.preco, item.desconto_maximo))}</b><small>com {item.desconto_maximo}% off</small></span></td><td><span className={`stock-label${item.estoque === 0 ? ' out-of-stock' : ''}`}>{item.estoque === 0 ? 'Sem estoque' : item.estoque}</span></td><td>{item.desconto_maximo}%</td>
        <td><div className="row-actions">{['admin', 'vendas'].includes(account.role) && <button className="icon-button" type="button" aria-label={`Análise financeira de ${item.nome}`} title="Análise financeira e simulação" onClick={() => setFinanceProduct(item)}><Calculator size={16} /></button>}<button className="icon-button" type="button" aria-label={`Comparar preços de ${item.nome}`} title="Comparar preços no Mercado Livre" onClick={() => openComparison(item)}><Scale size={16} /></button><button className="icon-button" type="button" aria-label={`Editar ${item.nome}`} onClick={() => { setEditing(item); setActionError(''); }}><Pencil size={16} /></button><button className="icon-button destructive" type="button" aria-label={`Excluir ${item.nome}`} onClick={() => remove(item)}><Trash2 size={16} /></button></div></td>
      </tr>)}</tbody></table></div> : <div className="empty-block"><Package size={23} /><b>{query ? 'Nenhum produto encontrado' : 'Nenhum produto cadastrado'}</b><span>{query ? 'Tente uma busca diferente.' : 'O catálogo mostrará os dados registrados pela equipe.'}</span></div>}
    </section>
    {editing && <ProductForm product={editing.id ? editing : null} onClose={() => setEditing(null)} onSave={save} busy={busy} />}
    {financeProduct && <FinanceModal product={financeProduct} account={account} onClose={() => setFinanceProduct(null)} />}
    {financeConfigOpen && <FinanceConfigModal onClose={() => setFinanceConfigOpen(false)} />}
    {comparison && <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && setComparison(null)}><section className="modal-card price-comparison-modal" role="dialog" aria-modal="true" aria-labelledby="comparison-title">
      <div className="modal-heading"><div><span className="eyebrow">PESQUISA DE MERCADO</span><h2 id="comparison-title">Comparar preços</h2></div><button className="icon-button close-button" type="button" onClick={() => setComparison(null)} aria-label="Fechar">×</button></div>
      <form className="comparison-own-price" onSubmit={saveComparisonPrice}>
        <label htmlFor="comparison-own-price">Preço no seu catálogo (R$)</label>
        <div className="comparison-own-price-edit"><input id="comparison-own-price" type="text" inputMode="decimal" value={comparisonPrice} onChange={(event) => setComparisonPrice(event.target.value)} aria-describedby="comparison-own-price-help" required /><button type="submit" className="button button-secondary" disabled={comparisonPriceBusy}>{comparisonPriceBusy ? 'Salvando…' : 'Salvar preço'}</button></div>
        <small id="comparison-own-price-help">{comparison.marca} · {comparison.nome}. Aceita valores como 1.299,90.</small>
        {comparisonPriceError && <span className="inline-error" role="alert">{comparisonPriceError}</span>}
      </form>
      <div className="comparison-discount-preview"><span>Preço com desconto máximo ({comparison.desconto_maximo}%)</span><b>{Number.isFinite(comparisonBasePrice) && comparisonBasePrice > 0 ? currency.format(discountedPrice(comparisonBasePrice, comparison.desconto_maximo)) : 'Informe um preço válido'}</b></div>
      <form className="comparison-search" onSubmit={(event) => event.preventDefault()}><label htmlFor="comparison-query">Pesquise este produto em lojas e comparadores</label><input id="comparison-query" value={comparisonQuery} onChange={(event) => setComparisonQuery(event.target.value)} minLength="2" maxLength="150" required /></form>
      <div className="marketplace-search-links">{marketplaceSearchLinks.map((site) => <a className={`button button-secondary${comparisonQuery.trim().length < 2 ? ' is-disabled' : ''}`} key={site.name} href={comparisonQuery.trim().length >= 2 ? site.url : undefined} target="_blank" rel="noreferrer" aria-disabled={comparisonQuery.trim().length < 2}><Search size={14} />{site.name}</a>)}</div>
      <p className="comparison-disclaimer">As buscas abrem nos próprios sites, sem senha no sistema. Para comprar, a loja pode pedir login. Confira preço, modelo, condição e frete antes de comparar.</p>
    </section></div>}
  </div>;
}
