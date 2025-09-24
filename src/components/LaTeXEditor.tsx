import React, { useEffect, useMemo, useState } from 'react';
import { Button } from './ui/button';
import { Check, X } from 'lucide-react';

export interface Change {
  id: string;
  type: 'addition' | 'removal' | 'replacement';
  startLine: number;
  endLine: number;
  content: string;
  accepted?: boolean | null;
  // backend compatibility
  start_line?: number;
  end_line?: number;
  pdf_regions?: Array<{ x: number; y: number; width: number; height: number }>;
}

interface LaTeXEditorProps {
  changes: Change[];
  onContentChange?: (content: string) => void;
}

/* ------------------------------ Normalization ------------------------------ */

type NormChange = {
  id: string;
  type: 'addition' | 'removal' | 'replacement';
  start: number; // 1-indexed inclusive
  end: number;   // 1-indexed inclusive
  content: string;
  contentLines: string[];
};

function normalizePatchContent(raw: string): string {
  if (!raw) return '';
  let s = raw;

  // Canonicalize escaped newlines
  s = s.replace(/\\n/g, '\n');

  // Turn lone 'n' before LaTeX commands into newline+backslash
  const cmd = '(begin|end|item|textbf|textit|section\\*?|subsection\\*?|documentclass|usepackage|href|url)';
  s = s.replace(new RegExp(`\\bn(?=${cmd}\\b)`, 'g'), '\n\\');

  // NEW: If a line *starts* with stray 'n' before Title text, treat as newline
  // Example: "nPersonal Finance Tracker ..." -> "\nPersonal Finance Tracker ..."
  s = s.replace(/(^|\n)n(?=[A-Z])/g, '$1\n');

  // Add missing backslash before known LaTeX commands when preceded by space/beginning
  s = s.replace(new RegExp(`(^|[\\s])(?<!\\\\)(${cmd})\\b`, 'g'), (_m, p1, p2) => `${p1}\\${p2}`);

  // Cleanup
  s = s.replace(/\r/g, '');
  s = s.replace(/\n{3,}/g, '\n\n');
  s = s.split('\n').map(l => l.replace(/[ \t]+$/g, '')).join('\n');

  return s.trim();
}

function normalizeChanges(changes: Change[] = []): NormChange[] {
  return changes.map((c) => {
    const start = (c.startLine ?? c.start_line ?? 1) | 0;
    const end = (c.endLine ?? c.end_line ?? start) | 0;
    const fixed = normalizePatchContent(c.content ?? '');
    return {
      id: c.id,
      type: c.type,
      start: Math.max(1, start),
      end: Math.max(start, end),
      content: fixed,
      contentLines: fixed ? fixed.split('\n') : [],
    };
  });
}

/** Gentle cleaner for editor content (preserves LaTeX). */
function cleanEditorContent(raw: string): string {
  if (!raw) return '';
  let s = raw.replace(/\r/g, '');
  s = s.replace(/\\\\(begin|end)\{itemize\}/g, '\\$1{itemize}');
  s = s.replace(/\\\\item/g, '\\item');
  s = s.replace(/\\n/g, '\n');
  s = s.replace(/\n{4,}/g, '\n\n');
  return s;
}

/* ------------------------ Block finding & line ops ------------------------- */

function eqLine(a: string, b: string) {
  return a.replace(/[ \t]+$/g, '') === b.replace(/[ \t]+$/g, '');
}

/** Find exact block in doc by content; returns [start,end] 1-indexed inclusive, or null. */
function findBlockByContent(docLines: string[], blockLines: string[]): [number, number] | null {
  if (!blockLines.length) return null;
  const N = docLines.length;
  const M = blockLines.length;
  outer: for (let i = 0; i + M <= N; i++) {
    for (let j = 0; j < M; j++) {
      if (!eqLine(docLines[i + j], blockLines[j])) continue outer;
    }
    return [i + 1, i + M];
  }
  return null;
}

function replaceBlock(docLines: string[], start1: number, end1: number, newLines: string[]) {
  const startIdx = Math.max(0, Math.min(docLines.length, start1 - 1));
  const endIdx = Math.max(startIdx - 1, Math.min(docLines.length - 1, end1 - 1));
  const before = docLines.slice(0, startIdx);
  const after = docLines.slice(endIdx + 1);
  return before.concat(newLines, after);
}

/** Insert AFTER a given anchor (1-indexed). If anchor > EOF, appends. */
function insertAfter(docLines: string[], anchor1: number, newLines: string[]) {
  const idx = Math.max(0, Math.min(docLines.length, anchor1)); // after -> not (anchor-1)
  const before = docLines.slice(0, idx);
  const after = docLines.slice(idx);
  return before.concat(newLines, after);
}

/* ----------------------- Change-set fingerprint logic ---------------------- */

function hashString(s: string): number {
  let h = 5381;
  for (let i = 0; i < s.length; i++) h = ((h << 5) + h) ^ s.charCodeAt(i);
  return h >>> 0;
}
function makeFingerprint(changes: Change[]): string {
  const parts = changes.map(c => {
    const start = c.startLine ?? c.start_line ?? 0;
    const end = c.endLine ?? c.end_line ?? start;
    const t = c.type;
    const body = normalizePatchContent(c.content ?? '');
    return `${t}:${start}:${end}:${hashString(body)}:${body.length}`;
  });
  return parts.sort().join('|');
}

/* -------------------------------- Diff view -------------------------------- */

function DiffPreview({ content, normChanges }: { content: string; normChanges: NormChange[] }) {
  const doc = useMemo(() => content.split('\n'), [content]);

  type Range = { start: number; end: number };
  const deletionRanges: Range[] = [];
  const additionsAt = new Map<number, string[]>(); // anchor -> added lines

  // Pair additions/removals for replacement visualization
  const byStart = new Map<number, NormChange[]>();
  normChanges.forEach(ch => {
    if (!byStart.has(ch.start)) byStart.set(ch.start, []);
    byStart.get(ch.start)!.push(ch);
  });

  for (const ch of normChanges) {
    if (ch.type === 'removal' || ch.type === 'replacement') {
      let range: Range | null = null;
      if (ch.contentLines.length) {
        const found = findBlockByContent(doc, ch.contentLines);
        if (found) range = { start: found[0], end: found[1] };
      }
      if (!range) range = { start: ch.start, end: ch.end };
      deletionRanges.push(range);

      if (ch.type === 'replacement') {
        const arr = additionsAt.get(range.start) ?? [];
        arr.push(...ch.contentLines);
        additionsAt.set(range.start, arr);
      }
    } else if (ch.type === 'addition') {
      // If sibling removal exists and we can find it, anchor to its start; otherwise keep start
      const siblings = byStart.get(ch.start) || [];
      const sibRem = siblings.find(s => s.type === 'removal');
      let anchor = ch.start;
      if (sibRem && sibRem.contentLines.length) {
        const found = findBlockByContent(doc, sibRem.contentLines);
        if (found) anchor = found[0];
      }
      const arr = additionsAt.get(anchor) ?? [];
      arr.push(...ch.contentLines);
      additionsAt.set(anchor, arr);
    }
  }

  const delMask = new Set<number>();
  deletionRanges.forEach(r => { for (let i = r.start; i <= r.end; i++) delMask.add(i); });

  type Row = { kind: 'ctx' | 'del' | 'add'; text: string; lineNo?: number; key: string };
  const rows: Row[] = [];

  for (let i = 1; i <= doc.length; i++) {
    const text = doc[i - 1];
    if (delMask.has(i)) rows.push({ kind: 'del', text, lineNo: i, key: `del-${i}` });
    else rows.push({ kind: 'ctx', text, lineNo: i, key: `ctx-${i}` });

    // PREVIEW: show additions AFTER anchor line i
    const adds = additionsAt.get(i);
    if (adds && adds.length) {
      adds.forEach((t, idx) => rows.push({ kind: 'add', text: t, key: `add-${i}-${idx}` }));
    }
  }
  for (const [anchor, adds] of additionsAt) {
    if (anchor > doc.length) {
      adds.forEach((t, idx) => rows.push({ kind: 'add', text: t, key: `add-${anchor}-${idx}` }));
    }
  }

  return (
    <div className="w-full h-full overflow-auto bg-slate-900 rounded border border-slate-700">
      <div className="min-w-full">
        {rows.map((row, idx) => {
          const grid = 'grid grid-cols-[56px_1fr] items-start';
          const gutter = 'select-none text-right pr-3 pl-2 border-r border-slate-700 text-slate-400';
          let cls = 'whitespace-pre-wrap px-3 py-1 border-b border-slate-800';
          if (row.kind === 'del') cls += ' bg-red-900/20 text-red-200 line-through';
          else if (row.kind === 'add') cls += ' bg-green-900/20 text-green-200';
          else cls += ' text-slate-300';

          return (
            <div key={row.key ?? idx} className={grid}>
              <div className={gutter}>{row.lineNo ?? ''}</div>
              <div className={cls}>{row.text === '' ? '\u00A0' : row.text}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* -------------------------------- Component -------------------------------- */

export default function LaTeXEditor({ changes, onContentChange }: LaTeXEditorProps) {
  const [content, setContent] = useState<string>('');
  const [processedIds, setProcessedIds] = useState<Set<string>>(new Set());
  const [lastFingerprint, setLastFingerprint] = useState<string>('');
  const [autoApply, setAutoApply] = useState(false);
  const [tab, setTab] = useState<'edit' | 'diff'>('diff');

  // Load from sessionStorage
  useEffect(() => {
    const projectData = sessionStorage.getItem('currentProject');
    if (projectData) {
      try {
      const project = JSON.parse(projectData);
        if (project?.resume_tex) {
          const cleaned = cleanEditorContent(project.resume_tex);
          setContent(cleaned);
          (window as any).latexEditorContent = cleaned;
          project.resume_tex = cleaned;
          sessionStorage.setItem('currentProject', JSON.stringify(project));
        }
      } catch {}
    }
  }, []);

  // keep global mirror
  useEffect(() => {
    (window as any).latexEditorContent = content;
  }, [content]);

  // listen for external updates
  useEffect(() => {
    const handler = () => {
      const projectData = sessionStorage.getItem('currentProject');
      if (!projectData) return;
      try {
        const project = JSON.parse(projectData);
        if (project?.resume_tex) {
          const cleaned = cleanEditorContent(project.resume_tex);
          setContent(cleaned);
          (window as any).latexEditorContent = cleaned;
          project.resume_tex = cleaned;
          sessionStorage.setItem('currentProject', JSON.stringify(project));
        }
      } catch {}
    };
    window.addEventListener('projectUpdated', handler as EventListener);
    return () => window.removeEventListener('projectUpdated', handler as EventListener);
  }, []);

  // Reset processed when the actual change *content* changes (not just IDs)
  useEffect(() => {
    const fp = makeFingerprint(changes || []);
    if (fp && fp !== lastFingerprint) {
      setProcessedIds(new Set());
      setLastFingerprint(fp);
    }
  }, [changes, lastFingerprint]);

  const activeChanges = useMemo(
    () => (changes || []).filter((c) => !processedIds.has(c.id)),
    [changes, processedIds]
  );
  const normChanges = useMemo(() => normalizeChanges(activeChanges), [activeChanges]);

  // persist once
  const persistProject = async (newContent: string) => {
    const projectData = sessionStorage.getItem('currentProject');
    if (!projectData) return;
    try {
      const project = JSON.parse(projectData);
      project.resume_tex = newContent;
      sessionStorage.setItem('currentProject', JSON.stringify(project));
      try {
        await fetch('http://localhost:8000/project/recreate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(project),
        });
      } catch {}
      window.dispatchEvent(new CustomEvent('projectUpdated', { detail: project }));
    } catch {}
  };

  const handleContentChange = async (newContent: string) => {
    const cleaned = cleanEditorContent(newContent);
    if (cleaned === content) return;
    setContent(cleaned);
    (window as any).latexEditorContent = cleaned;
    await persistProject(cleaned);
    onContentChange?.(cleaned);
  };

  /* -------------------------- Batch apply (robust) -------------------------- */

  const applyChangesInBatch = async (ids: string[], accept: boolean) => {
    if (!ids.length) return;

    const byId = new Map(normChanges.map((c) => [c.id, c]));
    let lines = content.split('\n');
    const processed = new Set<string>();

    // group by start to combine removal+addition (replacement) pairs
    const byStart = new Map<number, NormChange[]>();
    normChanges.forEach((ch) => {
      if (!byStart.has(ch.start)) byStart.set(ch.start, []);
      byStart.get(ch.start)!.push(ch);
    });

    // stable ordering
    const toApply: NormChange[] = ids.map(id => byId.get(id)).filter(Boolean) as NormChange[];
    toApply.sort((a, b) => a.start - b.start || a.end - b.end);

    for (const ch of toApply) {
      if (processed.has(ch.id)) continue;

      if (!accept) {
        processed.add(ch.id);
        window.dispatchEvent(new CustomEvent('changeAccepted', { detail: { changeId: ch.id, accepted: false } }));
        continue;
      }

      const siblings = byStart.get(ch.start) || [];
      const hasAdd = siblings.some(s => s.type === 'addition' && ids.includes(s.id));
      const hasRem = siblings.some(s => s.type === 'removal' && ids.includes(s.id));
      const isReplacement = ch.type === 'replacement' || (hasAdd && hasRem);

      if (isReplacement) {
        const add = (ch.type === 'addition'
          ? ch
          : siblings.find(s => s.type === 'addition' && ids.includes(s.id))) || ch;
        const rem = (ch.type === 'removal'
          ? ch
          : siblings.find(s => s.type === 'removal' && ids.includes(s.id))) || ch;

        // content-first replacement
        let replaced = false;
        if (rem.contentLines.length) {
          const found = findBlockByContent(lines, rem.contentLines);
          if (found) {
            lines = replaceBlock(lines, found[0], found[1], add.contentLines);
            replaced = true;
          }
        }
        if (!replaced) {
          lines = replaceBlock(lines, rem.start, rem.end, add.contentLines);
        }

        siblings
          .filter(s => ids.includes(s.id) && (s.type === 'removal' || s.type === 'addition' || s.type === 'replacement'))
          .forEach(s => {
            processed.add(s.id);
            window.dispatchEvent(new CustomEvent('changeAccepted', { detail: { changeId: s.id, accepted: true } }));
          });
        continue;
      }

      if (ch.type === 'removal') {
        let removed = false;
        if (ch.contentLines.length) {
          const found = findBlockByContent(lines, ch.contentLines);
          if (found) {
            lines = replaceBlock(lines, found[0], found[1], []);
            removed = true;
          }
        }
        if (!removed) {
          lines = replaceBlock(lines, ch.start, ch.end, []);
        }
        processed.add(ch.id);
        window.dispatchEvent(new CustomEvent('changeAccepted', { detail: { changeId: ch.id, accepted: true } }));
        continue;
      }

      if (ch.type === 'addition') {
        // Skip if block already exists verbatim
        const already = ch.contentLines.length ? !!findBlockByContent(lines, ch.contentLines) : false;
        if (!already) {
          // IMPORTANT: Insert AFTER anchor to match the preview
          lines = insertAfter(lines, ch.start, ch.contentLines);
        }
        processed.add(ch.id);
        window.dispatchEvent(new CustomEvent('changeAccepted', { detail: { changeId: ch.id, accepted: true } }));
        continue;
      }
    }

    const newContent = lines.join('\n');
    if (newContent !== content) {
    setContent(newContent);
      (window as any).latexEditorContent = newContent;
      await persistProject(newContent);
      onContentChange?.(newContent);
    }
    setProcessedIds(prev => {
      const s = new Set(prev);
      processed.forEach(id => s.add(id));
      return s;
    });
  };

  const handleApplyChange = (id: string, accepted: boolean) =>
    applyChangesInBatch([id], accepted);

  // auto-apply all (one batch)
  useEffect(() => {
    if (!autoApply || activeChanges.length === 0) return;
    applyChangesInBatch(activeChanges.map((c) => c.id), true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoApply, activeChanges.length]);

  // UI grouping for single-permission replacements
  const groups = useMemo(() => {
    const m = new Map<number, Change[]>();
    activeChanges.forEach((c) => {
      const ln = c.startLine ?? c.start_line ?? 1;
      if (!m.has(ln)) m.set(ln, []);
      m.get(ln)!.push(c);
    });
    return m;
  }, [activeChanges]);

                return (
    <div className="flex h-full bg-slate-900">
      {/* Left: Editor / Diff */}
      <div className="flex-1 flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-slate-700">
          <h2 className="text-lg font-semibold text-slate-200">LaTeX Editor</h2>
          <div className="flex items-center gap-4">
            <div className="text-sm text-slate-400">
              {activeChanges.length} change{activeChanges.length === 1 ? '' : 's'} pending
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={autoApply}
                onChange={(e) => setAutoApply(e.target.checked)}
                className="w-4 h-4 text-blue-600 bg-slate-700 border-slate-600 rounded focus:ring-blue-500"
              />
              Auto-apply
            </label>
            {!autoApply && activeChanges.length > 0 && (
              <button
                onClick={() => applyChangesInBatch(activeChanges.map((c) => c.id), true)}
                className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
              >
                Apply All
              </button>
            )}
            <div className="inline-flex rounded-md overflow-hidden border border-slate-600">
              <button
                className={`px-3 py-1 text-sm ${tab === 'edit' ? 'bg-slate-700 text-slate-100' : 'bg-slate-800 text-slate-300'}`}
                onClick={() => setTab('edit')}
              >
                Edit
              </button>
              <button
                className={`px-3 py-1 text-sm ${tab === 'diff' ? 'bg-slate-700 text-slate-100' : 'bg-slate-800 text-slate-300'}`}
                onClick={() => setTab('diff')}
              >
                Diff
              </button>
            </div>
          </div>
      </div>
      
        <div className="flex-1 overflow-auto p-4">
          {tab === 'edit' ? (
              <textarea
                value={content}
                onChange={(e) => handleContentChange(e.target.value)}
              className="w-full h-full bg-slate-800 text-slate-300 font-mono text-sm p-4 border border-slate-600 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="LaTeX content will appear here..."
              style={{ minHeight: '500px' }}
              />
          ) : (
            <DiffPreview content={content} normChanges={normalizeChanges(activeChanges)} />
          )}
            </div>
      </div>

      {/* Inline-only presentation: sidebar removed */}
    </div>
  );
}
