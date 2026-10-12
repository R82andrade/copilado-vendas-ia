import React from 'react';

export function EmptyState({ icon: Icon, title, children }) {
  return <div className="empty-block">
    {Icon && <Icon size={23} />}
    <b>{title}</b>
    {children && <span>{children}</span>}
  </div>;
}
