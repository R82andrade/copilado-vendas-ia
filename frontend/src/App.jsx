import React, { lazy, Suspense, useEffect, useState } from 'react';
import { HashRouter, Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from './layouts/Layout.jsx';
import { LoginPage } from './pages/LoginPage.jsx';
import { api, TOKEN_KEY } from './services/api.js';

const DashboardPage = lazy(() => import('./pages/DashboardPage.jsx').then((module) => ({ default: module.DashboardPage })));
const ClientsPage = lazy(() => import('./pages/ClientsPage.jsx').then((module) => ({ default: module.ClientsPage })));
const ClientProfilePage = lazy(() => import('./pages/ClientsPage.jsx').then((module) => ({ default: module.ClientProfilePage })));
const ConversationsPage = lazy(() => import('./pages/ConversationsPage.jsx').then((module) => ({ default: module.ConversationsPage })));
const AIAnalysesPage = lazy(() => import('./pages/AIAnalysesPage.jsx').then((module) => ({ default: module.AIAnalysesPage })));
const SuggestionsPage = lazy(() => import('./pages/SuggestionsPage.jsx').then((module) => ({ default: module.SuggestionsPage })));
const ProductsPage = lazy(() => import('./pages/ProductsPage.jsx').then((module) => ({ default: module.ProductsPage })));
const OrdersPage = lazy(() => import('./pages/OrdersPage.jsx').then((module) => ({ default: module.OrdersPage })));
const UsersPage = lazy(() => import('./pages/UsersPage.jsx').then((module) => ({ default: module.UsersPage })));

const ROLE_KEY = 'vendas-api-role';

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [account, setAccount] = useState(() => ({
    username: localStorage.getItem('vendas-api-username') || 'Usuário',
    role: localStorage.getItem(ROLE_KEY) || '',
  }));

  useEffect(() => {
    const onExpired = () => {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(ROLE_KEY);
      localStorage.removeItem('vendas-api-username');
      setToken('');
    };
    window.addEventListener('auth:expired', onExpired);
    return () => window.removeEventListener('auth:expired', onExpired);
  }, []);

  async function login(username, password) {
    const result = await api.login(username, password);
    localStorage.setItem(TOKEN_KEY, result.token);
    localStorage.setItem(ROLE_KEY, result.role);
    localStorage.setItem('vendas-api-username', result.username);
    setAccount({ username: result.username, role: result.role });
    setToken(result.token);
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(ROLE_KEY);
    localStorage.removeItem('vendas-api-username');
    setToken('');
  }

  if (!token) return <LoginPage onLogin={login} />;

  return (
    <HashRouter>
      <Suspense fallback={<div className="page-loading"><span className="spinner" />Abrindo página…</div>}>
        <Routes>
          <Route element={<Layout account={account} onLogout={logout} />}>
            <Route index element={<DashboardPage />} />
            <Route path="clientes" element={<ClientsPage />} />
            <Route path="clientes/:id" element={<ClientProfilePage />} />
            <Route path="conversas" element={<ConversationsPage />} />
            <Route path="analises-ia" element={<AIAnalysesPage />} />
            <Route path="sugestoes" element={<SuggestionsPage />} />
            <Route path="produtos" element={<ProductsPage />} />
            <Route path="historico" element={<OrdersPage />} />
            <Route path="configuracoes" element={<UsersPage account={account} />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </Suspense>
    </HashRouter>
  );
}
