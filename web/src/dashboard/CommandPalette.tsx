import { useEffect, useMemo, useRef, useState } from 'react';

export interface Command {
  id: string;
  title: string;
  detail: string;
  run: () => void;
}

export function CommandPalette({ commands, close }: { commands: Command[]; close: () => void }) {
  const [query, setQuery] = useState('');
  const [index, setIndex] = useState(0);
  const dialog = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const filtered = useMemo(() => commands.filter(command =>
    `${command.title} ${command.detail}`.toLowerCase().includes(query.toLowerCase())), [commands, query]);

  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    input.current?.focus();
    return () => previous?.focus();
  }, []);

  function execute(i: number) {
    const command = filtered[i];
    if (!command) return;
    close();
    command.run();
  }

  return (
    <div className="ns-modal-backdrop" onMouseDown={event => { if (event.target === event.currentTarget) close(); }}>
      <div ref={dialog} className="ns-palette" role="dialog" aria-modal="true" aria-label="Command palette"
        onKeyDown={event => {
          if (event.key === 'Escape') { event.preventDefault(); close(); }
          if (event.key === 'ArrowDown') { event.preventDefault(); setIndex(i => Math.min(filtered.length - 1, i + 1)); }
          if (event.key === 'ArrowUp') { event.preventDefault(); setIndex(i => Math.max(0, i - 1)); }
          if (event.key === 'Enter') { event.preventDefault(); execute(index); }
          if (event.key === 'Tab') {
            const focusable = Array.from(dialog.current?.querySelectorAll<HTMLElement>('input, button') || []);
            if (!focusable.length) return;
            const current = focusable.indexOf(document.activeElement as HTMLElement);
            const next = (current + (event.shiftKey ? -1 : 1) + focusable.length) % focusable.length;
            event.preventDefault();
            focusable[next].focus();
          }
        }}>
        <div className="ns-palette-search">
          <span aria-hidden="true">⌕</span>
          <input ref={input} value={query}
            onChange={event => { setQuery(event.target.value); setIndex(0); }}
            aria-label="Search commands" placeholder="Samples, models, budget, export…"
            aria-controls="ns-command-results" aria-activedescendant={filtered[index] ? `command-${filtered[index].id}` : undefined}
            role="combobox" aria-expanded="true" aria-autocomplete="list" />
          <button onClick={close} aria-label="Close command palette">Esc</button>
        </div>
        <div id="ns-command-results" role="listbox" className="ns-palette-results">
          {filtered.map((command, i) => (
            <button key={command.id} id={`command-${command.id}`} role="option" aria-selected={index === i}
              onMouseEnter={() => setIndex(i)} onClick={() => execute(i)}>
              <span>{command.title}<small>{command.detail}</small></span><span aria-hidden="true">↵</span>
            </button>
          ))}
          {!filtered.length && <p>No commands match. Try “budget” or a dataset name.</p>}
        </div>
        <footer><span>↑ ↓ navigate</span><span>↵ apply</span><span>esc close</span></footer>
      </div>
    </div>
  );
}
