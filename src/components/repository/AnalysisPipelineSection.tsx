import React from 'react';

export const AnalysisPipelineSection: React.FC = () => {
  const steps = [
    {
      num: '01',
      title: 'Archive Validation',
      subtitle: 'Security & Format Inspection',
      description: 'DevMind will unpack the ZIP archive, inspect file trees, verify checksum integrity, and filter binary or generated files.',
    },
    {
      num: '02',
      title: 'Code & Symbol Analysis',
      subtitle: 'AST & Dependency Extraction',
      description: 'The analysis engine will parse source files into Abstract Syntax Trees (ASTs), extract symbol definitions, and construct internal dependency graphs.',
    },
    {
      num: '03',
      title: 'Intelligence Synthesis',
      subtitle: 'Context & Vector Indexing',
      description: 'Code structures, documentation, and security boundaries will be indexed into DevMind contextual memory for AI query resolution.',
    },
  ];

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h3 style={styles.title}>How Repository Analysis Works</h3>
        <p style={styles.subtitle}>
          Overview of the processing pipeline DevMind will execute upon connecting the backend analysis service.
        </p>
      </div>

      <div style={styles.grid}>
        {steps.map((step) => (
          <div key={step.num} style={styles.card}>
            <div style={styles.cardTop}>
              <span style={styles.stepNum}>{step.num}</span>
              <span style={styles.willDoBadge}>Pipeline Plan</span>
            </div>
            <h4 style={styles.stepTitle}>{step.title}</h4>
            <span style={styles.stepSub}>{step.subtitle}</span>
            <p style={styles.stepDesc}>{step.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    marginTop: '40px',
  },
  header: {
    marginBottom: '20px',
  },
  title: {
    fontSize: '18px',
    fontWeight: 700,
    color: 'var(--text-main)',
    marginBottom: '4px',
  },
  subtitle: {
    fontSize: '13.5px',
    color: 'var(--text-muted)',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
    gap: '20px',
  },
  card: {
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-lg)',
    padding: '24px',
    boxShadow: 'var(--shadow-xs)',
    display: 'flex',
    flexDirection: 'column',
  },
  cardTop: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '16px',
  },
  stepNum: {
    fontSize: '14px',
    fontWeight: 800,
    color: 'var(--color-primary)',
    backgroundColor: 'var(--color-primary-light)',
    padding: '4px 10px',
    borderRadius: 'var(--radius-md)',
  },
  willDoBadge: {
    fontSize: '11px',
    fontWeight: 600,
    color: 'var(--text-muted)',
    backgroundColor: 'var(--bg-app)',
    padding: '2px 8px',
    borderRadius: 'var(--radius-full)',
    border: '1px solid var(--border-subtle)',
  },
  stepTitle: {
    fontSize: '15px',
    fontWeight: 700,
    color: 'var(--text-main)',
    marginBottom: '2px',
  },
  stepSub: {
    fontSize: '12px',
    fontWeight: 500,
    color: 'var(--text-muted)',
    marginBottom: '12px',
  },
  stepDesc: {
    fontSize: '13px',
    color: 'var(--text-muted)',
    lineHeight: '1.5',
  },
};
