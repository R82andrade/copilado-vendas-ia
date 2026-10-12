import React, { useState } from 'react';
import { Activity, ArrowRight, Bot, LockKeyhole } from 'lucide-react';

export function LoginPage({ onLogin }) {
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  async function submit(event) {
    event.preventDefault();
    setError('');
    setLoading(true);
    const form = new FormData(event.currentTarget);
    try { await onLogin(form.get('username').trim(), form.get('password')); }
    catch (reason) { setError(reason.message); }
    finally { setLoading(false); }
  }
  return (
    <main className="login-page">
      <section className="login-art">
        <div className="login-brand"><span className="brand-icon"><Activity size={20} /></span><b>copiloto</b></div>
        <div className="login-message"><span className="eyebrow">INTELIGÊNCIA A FAVOR DO SEU TIME</span><h1>Mais contexto.<br /><em>Melhores conversas.</em></h1><p>Seu copiloto organiza cada atendimento e ajuda sua equipe a vender com confiança.</p></div>
        <div className="login-art-foot"><Bot size={18} /> A IA sugere. A decisão continua sendo sua.</div>
      </section>
      <section className="login-form-side">
        <form className="login-card" onSubmit={submit}>
          <div className="login-icon"><LockKeyhole size={20} /></div>
          <span className="eyebrow">BEM-VINDO DE VOLTA</span>
          <h2>Acesse sua conta</h2>
          <p>Entre para acompanhar clientes e conversas.</p>
          {error && <div className="inline-error" role="alert">{error}</div>}
          <label>Usuário<input autoComplete="username" name="username" required /></label>
          <label>Senha<input autoComplete="current-password" name="password" type="password" required /></label>
          <button className="button button-primary login-submit" disabled={loading}>{loading ? 'Entrando…' : 'Entrar no painel'} <ArrowRight size={17} /></button>
          <small className="login-help">Use as credenciais configuradas no backend.</small>
        </form>
      </section>
    </main>
  );
}
