import React from 'react';
import { Link } from 'react-router-dom';

export const NotFoundPage: React.FC = () => {
  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <div style={styles.code}>404</div>
        <h1 style={styles.title}>Page Not Found</h1>
        <p style={styles.text}>The page you are looking for does not exist or has been moved.</p>
        <Link to="/" style={styles.button}>
          Back to Home
        </Link>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: '64px 24px',
    maxWidth: '500px',
    margin: '0 auto',
    width: '100%',
    textAlign: 'center',
  },
  card: {
    backgroundColor: 'var(--bg-surface)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border-default)',
    padding: '40px',
    boxShadow: 'var(--shadow-sm)',
  },
  code: {
    fontSize: '48px',
    fontWeight: 800,
    color: 'var(--color-primary)',
    marginBottom: '8px',
  },
  title: {
    fontSize: '20px',
    fontWeight: 600,
    marginBottom: '8px',
  },
  text: {
    fontSize: '14px',
    color: 'var(--text-muted)',
    marginBottom: '24px',
  },
  button: {
    display: 'inline-block',
    backgroundColor: 'var(--color-primary)',
    color: 'var(--color-primary-text)',
    padding: '10px 20px',
    borderRadius: 'var(--radius-md)',
    fontWeight: 500,
    fontSize: '14px',
    textDecoration: 'none',
  },
};
