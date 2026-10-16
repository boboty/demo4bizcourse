import React from 'react';

/**
 * BenYan AI — Card
 * Base surface container. Optional top accent rule and elevation.
 */
export function Card({
  children,
  elevation = 'sm',
  accent = false,
  interactive = false,
  pad = 24,
  style = {},
  ...rest
}) {
  const shadows = { none: 'none', xs: 'var(--shadow-xs)', sm: 'var(--shadow-sm)', md: 'var(--shadow-md)', lg: 'var(--shadow-lg)' };
  return (
    <div
      style={{
        position: 'relative',
        background: 'var(--surface-card)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-lg)',
        boxShadow: shadows[elevation] ?? shadows.sm,
        padding: pad,
        overflow: 'hidden',
        transition: 'transform var(--dur-base) var(--ease-standard), box-shadow var(--dur-base) var(--ease-standard)',
        ...style,
      }}
      onMouseEnter={interactive ? (e) => { e.currentTarget.style.transform = 'translateY(-3px)'; e.currentTarget.style.boxShadow = 'var(--shadow-lg)'; } : undefined}
      onMouseLeave={interactive ? (e) => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = shadows[elevation] ?? shadows.sm; } : undefined}
      {...rest}
    >
      {accent ? <span style={{ position: 'absolute', top: 0, left: 0, height: 3, width: 48, background: 'var(--brand)', borderRadius: '0 0 var(--radius-pill) 0' }} /> : null}
      {children}
    </div>
  );
}
