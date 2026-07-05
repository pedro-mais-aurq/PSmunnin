export function ScorePill({ score, priority, size = 'md' }) {
  const color =
    priority === 'high'
      ? 'from-rose-500 to-orange-500 text-black'
      : priority === 'medium'
      ? 'from-amber-400 to-amber-500 text-black'
      : 'from-neutral-700 to-neutral-800 text-neutral-200';
  const sz = size === 'lg' ? 'text-2xl w-16 h-16' : 'text-sm w-12 h-12';
  return (
    <div
      className={`rounded-full bg-gradient-to-br ${color} ${sz} flex items-center justify-center font-bold shadow-lg`}
      title={`Prioridade: ${priority}`}
    >
      {score}
    </div>
  );
}

export function StatusBadge({ status }) {
  const map = {
    pending: 'bg-neutral-700 text-neutral-200',
    running: 'bg-blue-500/20 text-blue-300 border border-blue-500/30',
    done: 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30',
    failed: 'bg-rose-500/20 text-rose-300 border border-rose-500/30',
  };
  const label = { pending: 'Aguardando', running: 'Analisando…', done: 'Concluída', failed: 'Falhou' }[status] || status;
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-full ${map[status] || map.pending}`}>
      {status === 'running' && (
        <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
      )}
      {label}
    </span>
  );
}

export function PriorityBadge({ priority }) {
  const map = {
    high: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
    medium: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
    low: 'bg-neutral-500/15 text-neutral-300 border-neutral-500/30',
  };
  const label = { high: 'Alta prioridade', medium: 'Média prioridade', low: 'Baixa prioridade' }[priority];
  return (
    <span className={`text-[11px] uppercase tracking-widest px-2 py-1 rounded border ${map[priority]}`}>
      {label}
    </span>
  );
}
