import React, { useMemo, useState } from 'react';
import { CirclePlus, Package, Pencil, Search, Scale, Trash2 } from 'lucide-react';
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

export function ProductsPage() {
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
    <div className="page-heading"><div><span className="eyebrow">OPERAÇÃO COMERCIAL</span><h1>Catálogo de produtos</h1><p>Preços, estoque e descontos usados pela equipe.</p></div><button className="button button-primary" onClick={() => { setEditing({ ...blank }); setActionError(''); }}><CirclePlus size={17} /> Novo produto</button></div>
    <section className="surface table-surface"><div className="table-toolbar"><div><h2>Produtos cadastrados</h2><span>{loading ? 'Carregando…' : `${data?.length ?? 0} itens`}</span></div><label className="table-search"><Search size={16} /><span className="sr-only">Buscar produto</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar no catálogo" /></label></div>
      {notice && <div className="inline-success">{notice}</div>}{(error || actionError) && <div className="inline-error" role="alert">{error || actionError}</div>}
      {loading ? <div className="page-loading"><span className="spinner" />Carregando catálogo…</div> : rows.length ? <div className="table-scroll"><table className="data-table"><thead><tr><th>Produto</th><th>Categoria</th><th>Preço</th><th>Preço com desconto</th><th>Estoque</th><th>Desconto máx.</th><th><span className="sr-only">Ações</span></th></tr></thead><tbody>{rows.map((item) => <tr key={item.id}>
        <td><span className="client-name-cell"><span className="table-avatar"><Package size={15} /></span><span><b>{item.nome}</b><small>{item.marca}</small></span></span></td><td>{item.categoria}</td><td><b>{currency.format(item.preco)}</b></td><td><span className="discounted-price-cell"><b>{currency.format(discountedPrice(item.preco, item.desconto_maximo))}</b><small>com {item.desconto_maximo}% off</small></span></td><td><span className={`stock-label${item.estoque === 0 ? ' out-of-stock' : ''}`}>{item.estoque === 0 ? 'Sem estoque' : item.estoque}</span></td><td>{item.desconto_maximo}%</td>
        <td><div className="row-actions"><button className="icon-button" type="button" aria-label={`Comparar preços de ${item.nome}`} title="Comparar preços no Mercado Livre" onClick={() => openComparison(item)}><Scale size={16} /></button><button className="icon-button" type="button" aria-label={`Editar ${item.nome}`} onClick={() => { setEditing(item); setActionError(''); }}><Pencil size={16} /></button><button className="icon-button destructive" type="button" aria-label={`Excluir ${item.nome}`} onClick={() => remove(item)}><Trash2 size={16} /></button></div></td>
      </tr>)}</tbody></table></div> : <div className="empty-block"><Package size={23} /><b>{query ? 'Nenhum produto encontrado' : 'Nenhum produto cadastrado'}</b><span>{query ? 'Tente uma busca diferente.' : 'O catálogo mostrará os dados registrados pela equipe.'}</span></div>}
    </section>
    {editing && <ProductForm product={editing.id ? editing : null} onClose={() => setEditing(null)} onSave={save} busy={busy} />}
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
