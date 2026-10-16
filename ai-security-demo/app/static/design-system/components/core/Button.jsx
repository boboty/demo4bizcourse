import React from 'react';

/**
 * BenYan AI — Button
 * Variants: primary (emerald), secondary (ink outline), ghost, dark, soft.
 * Sizes: sm, md, lg. Optional leading/trailing icon nodes.
 */
export function Button({
  children,
  variant = 'primary',
  size = 'md',
  iconLeft = null,
  iconRight = null,
  disabled = false,
  full = false,
  style = {},
  ...rest
}) {
  const sizes = {
    sm: { height: 'var(--control-h-sm)', padding: '0 14px', fontSize: 'var(--text-sm)', radius: 'var(--radius-sm)', gap: '7px' },
    md: { height: 'var(--control-h-md)', padding: '0 20px', fontSize: 'var(--text-md)', radius: 'var(--radius-md)', gap: '9px' },
    lg: { height: 'var(--control-h-lg)', padding: '0 28px', fontSize: 'var(--text-lg)', radius: 'var(--radius-md)', gap: '10px' },
  };
  const variants = {
    primary: { background: 'var(--brand)', color: 'var(--text-on-brand)', border: '1px solid transparent', boxShadow: 'var(--shadow-sm)' },
    secondary: { background: 'var(--surface-card)', color: 'var(--text-body)', border: '1px solid var(--border-strong)', boxShadow: 'var(--shadow-xs)' },
    ghost: { background: 'transparent', color: 'var(--text-brand)', border: '1px solid transparent', boxShadow: 'none' },
    dark: { background: 'var(--ink-800)', color: '#fff', border: '1px solid transparent', boxShadow: 'var(--shadow-sm)' },
    soft: { background: 'var(--surface-brand-soft)', color: 'var(--emerald-800)', border: '1px solid var(--emerald-200)', boxShadow: 'none' },
  };
  const s = sizes[size] || sizes.md;
  const v = variants[variant] || variants.primary;

  return (
    <button
      type="button"
      disabled={disabled}
      style={{
        display: full ? 'flex' : 'inline-flex',
        width: full ? '100%' : 'auto',
        alignItems: 'center',
        justifyContent: 'center',
        gap: s.gap,
        height: s.height,
        padding: s.padding,
        fontSize: s.fontSize,
        fontFamily: 'var(--font-sans)',
        fontWeight: 'var(--fw-semibold)',
        letterSpacing: '-0.005em',
        lineHeight: 1,
        borderRadius: s.radius,
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.45 : 1,
        transition: 'transform var(--dur-fast) var(--ease-standard), filter var(--dur-fast) var(--ease-standard), box-shadow var(--dur-fast) var(--ease-standard)',
        whiteSpace: 'nowrap',
        ...v,
        ...style,
      }}
      onMouseEnter={(e) => { if (!disabled) e.currentTarget.style.filter = 'brightness(0.94)'; }}
      onMouseLeave={(e) => { e.currentTarget.style.filter = 'none'; e.currentTarget.style.transform = 'none'; }}
      onMouseDown={(e) => { if (!disabled) e.currentTarget.style.transform = 'translateY(1px)'; }}
      onMouseUp={(e) => { e.currentTarget.style.transform = 'none'; }}
      {...rest}
    >
      {iconLeft ? <span style={{ display: 'inline-flex', fontSize: '1.05em' }}>{iconLeft}</span> : null}
      {children}
      {iconRight ? <span style={{ display: 'inline-flex', fontSize: '1.05em' }}>{iconRight}</span> : null}
    </button>
  );
}
