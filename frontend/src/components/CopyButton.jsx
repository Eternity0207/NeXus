import { useState } from 'react';
import { useToast } from './useToast';

async function copyToClipboard(text) {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch { /* fall through */ }
  try {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.position = 'absolute';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(ta);
    return ok;
  } catch { return false; }
}

/**
 * Inline copy-to-clipboard button.
 *
 * <CopyButton value={repo.repo_id} label="Copy full ID" />
 */
export default function CopyButton({ value, label = 'Copy', compact = false, title }) {
  const toast = useToast();
  const [copied, setCopied] = useState(false);

  const handle = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    const ok = await copyToClipboard(String(value ?? ''));
    if (ok) {
      setCopied(true);
      toast.success(`${label} copied`);
      setTimeout(() => setCopied(false), 1500);
    } else {
      toast.error('Unable to copy');
    }
  };

  return (
    <button
      type="button"
      onClick={handle}
      className={`copy-btn ${compact ? 'copy-btn-compact' : ''} ${copied ? 'copy-btn-done' : ''}`}
      title={title || label}
      aria-label={label}
    >
      <span className="copy-icon" aria-hidden="true">
        {copied ? '✓' : '⧉'}
      </span>
      {!compact && <span className="copy-label">{copied ? 'Copied' : 'Copy'}</span>}
    </button>
  );
}
