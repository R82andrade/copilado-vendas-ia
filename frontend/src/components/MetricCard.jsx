import React from 'react';

export function MetricCard({ title, value, note, icon: Icon, tone = 'blue' }) {
  return <article className="metric-card">
    <div className={`metric-icon ${tone}`}><Icon size={19} /></div>
    <span className="metric-title">{title}</span>
    <strong className="metric-value">{value}</strong>
    <span className="metric-note">{note}</span>
  </article>;
}
