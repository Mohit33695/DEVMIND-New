import React, { useState, useEffect, useMemo, useRef } from 'react';
import type { SymbolItem, SymbolKind } from '@/types/repository';

interface SymbolPanelProps {
  symbols: SymbolItem[];
  isLoading?: boolean;
  error?: string | null;
}

export const SymbolPanel: React.FC<SymbolPanelProps> = ({
  symbols,
  isLoading = false,
  error = null,
}) => {
  const [activeTab, setActiveTab] = useState<'all' | SymbolKind>('all');
  const gridRef = useRef<HTMLDivElement>(null);

  // Reset active filter tab to 'all' whenever symbols array prop changes (e.g. selected file switches)
  useEffect(() => {
    setActiveTab('all');
  }, [symbols]);

  // Reset scroll position to top whenever activeTab or symbols change
  useEffect(() => {
    if (gridRef.current) {
      gridRef.current.scrollTop = 0;
    }
  }, [activeTab, symbols]);

  // Categorize symbols
  const categorized = useMemo(() => {
    const classes = symbols.filter((s) => s.kind === 'class');
    const functions = symbols.filter((s) => s.kind === 'function');
    const methods = symbols.filter((s) => s.kind === 'method');
    const imports = symbols.filter((s) => s.kind === 'import');
    return { classes, functions, methods, imports };
  }, [symbols]);

  // Filtered list based on activeTab
  const filteredSymbols = useMemo(() => {
    if (activeTab === 'all') return symbols;
    return symbols.filter((s) => s.kind === activeTab);
  }, [symbols, activeTab]);

  if (isLoading) {
    return (
      <div style={styles.panelContainer}>
        <div style={styles.loadingBox}>
          <span style={styles.spinnerDot} />
          <span>Parsing code intelligence symbols...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return null; // Gracefully suppress errors so file viewer is never blocked
  }

  if (symbols.length === 0) {
    return null; // Don't render empty symbol header if file has no AST symbols
  }

  const getKindBadgeStyle = (kind: SymbolKind) => {
    switch (kind) {
      case 'class':
        return styles.badgeClass;
      case 'function':
        return styles.badgeFunction;
      case 'method':
        return styles.badgeMethod;
      case 'import':
        return styles.badgeImport;
    }
  };

  return (
    <div style={styles.panelContainer}>
      {/* 1. Header Bar */}
      <div style={styles.panelHeader}>
        <div style={styles.headerLeft}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="2.5">
            <polyline points="16 18 22 12 16 6" />
            <polyline points="8 6 2 12 8 18" />
          </svg>
          <span style={styles.headerTitle}>AST Code Symbols</span>
          <span style={styles.symbolCountBadge}>{symbols.length}</span>
        </div>

        {/* Filter Tabs */}
        <div style={styles.filterTabs}>
          <button
            type="button"
            style={{
              ...styles.tabBtn,
              ...(activeTab === 'all' ? styles.tabBtnActive : {}),
            }}
            onClick={() => setActiveTab('all')}
          >
            All ({symbols.length})
          </button>

          {categorized.classes.length > 0 && (
            <button
              type="button"
              style={{
                ...styles.tabBtn,
                ...(activeTab === 'class' ? styles.tabBtnActive : {}),
              }}
              onClick={() => setActiveTab('class')}
            >
              Classes ({categorized.classes.length})
            </button>
          )}

          {categorized.functions.length > 0 && (
            <button
              type="button"
              style={{
                ...styles.tabBtn,
                ...(activeTab === 'function' ? styles.tabBtnActive : {}),
              }}
              onClick={() => setActiveTab('function')}
            >
              Functions ({categorized.functions.length})
            </button>
          )}

          {categorized.methods.length > 0 && (
            <button
              type="button"
              style={{
                ...styles.tabBtn,
                ...(activeTab === 'method' ? styles.tabBtnActive : {}),
              }}
              onClick={() => setActiveTab('method')}
            >
              Methods ({categorized.methods.length})
            </button>
          )}

          {categorized.imports.length > 0 && (
            <button
              type="button"
              style={{
                ...styles.tabBtn,
                ...(activeTab === 'import' ? styles.tabBtnActive : {}),
              }}
              onClick={() => setActiveTab('import')}
            >
              Imports ({categorized.imports.length})
            </button>
          )}
        </div>
      </div>

      {/* 2. Symbols Grid / List */}
      <div key={activeTab} ref={gridRef} style={styles.symbolsGrid}>
        {filteredSymbols.map((item, index) => (
          <div key={`${item.name}-${index}`} style={styles.symbolCard}>
            <div style={styles.cardHeader}>
              <span style={{ ...styles.kindBadge, ...getKindBadgeStyle(item.kind) }}>
                {item.kind}
              </span>
              <span style={styles.symbolName}>{item.name}</span>
              <span style={styles.lineRange}>
                L{item.line_start}{item.line_start !== item.line_end ? `-L${item.line_end}` : ''}
              </span>
            </div>

            {item.signature && (
              <div style={styles.signatureRow}>
                <code>{item.signature}</code>
              </div>
            )}

            {item.docstring && (
              <div style={styles.docstringRow}>
                <span style={styles.docstringText}>{item.docstring}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  panelContainer: {
    backgroundColor: 'var(--bg-app)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    marginBottom: '12px',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
  },
  loadingBox: {
    padding: '12px 16px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '12.5px',
    color: 'var(--text-muted)',
  },
  spinnerDot: {
    width: '12px',
    height: '12px',
    border: '2px solid var(--border-default)',
    borderTopColor: 'var(--color-primary)',
    borderRadius: '50%',
    display: 'inline-block',
    animation: 'spin 0.8s linear infinite',
  },
  panelHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '8px 14px',
    backgroundColor: 'var(--bg-surface)',
    borderBottom: '1px solid var(--border-default)',
    gap: '12px',
    flexWrap: 'wrap',
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  headerTitle: {
    fontSize: '12.5px',
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    color: 'var(--text-main)',
  },
  symbolCountBadge: {
    fontSize: '11px',
    fontWeight: 700,
    color: 'var(--color-primary)',
    backgroundColor: 'var(--color-primary-light)',
    padding: '2px 7px',
    borderRadius: 'var(--radius-full)',
  },
  filterTabs: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    flexWrap: 'wrap',
  },
  tabBtn: {
    padding: '3px 9px',
    fontSize: '11.5px',
    fontWeight: 600,
    color: 'var(--text-muted)',
    backgroundColor: 'transparent',
    border: '1px solid transparent',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
  },
  tabBtnActive: {
    color: 'var(--color-primary)',
    backgroundColor: 'var(--bg-app)',
    borderColor: 'var(--border-default)',
  },
  symbolsGrid: {
    padding: '10px 14px',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    maxHeight: '260px',
    overflowY: 'auto',
    flex: '1 1 auto',
    minHeight: 0,
  },
  symbolCard: {
    padding: '8px 10px',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-sm)',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  cardHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  kindBadge: {
    fontSize: '10px',
    fontWeight: 700,
    textTransform: 'uppercase',
    padding: '1px 6px',
    borderRadius: 'var(--radius-sm)',
  },
  badgeClass: {
    color: '#8B5CF6',
    backgroundColor: '#F3E8FF',
  },
  badgeFunction: {
    color: '#3B82F6',
    backgroundColor: '#EFF6FF',
  },
  badgeMethod: {
    color: '#D97706',
    backgroundColor: '#FEF3C7',
  },
  badgeImport: {
    color: '#10B981',
    backgroundColor: '#ECFDF5',
  },
  symbolName: {
    fontSize: '12.5px',
    fontWeight: 600,
    color: 'var(--text-main)',
  },
  lineRange: {
    fontSize: '11px',
    fontFamily: 'monospace',
    color: 'var(--text-subtle)',
    marginLeft: 'auto',
  },
  signatureRow: {
    fontSize: '11.5px',
    fontFamily: 'monospace',
    color: 'var(--text-muted)',
  },
  docstringRow: {
    fontSize: '11.5px',
    fontStyle: 'italic',
    color: 'var(--text-subtle)',
  },
  docstringText: {
    display: '-webkit-box',
    WebkitLineClamp: 2,
    WebkitBoxOrient: 'vertical',
    overflow: 'hidden',
  },
};
