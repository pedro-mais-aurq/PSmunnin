import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { getSearch } from '@/lib/api';
import { PSM } from '@/constants/testIds';
import { ScorePill, StatusBadge, PriorityBadge } from '@/components/Badges';
import { ArrowLeft, RefreshCw, Globe, GlobeLock, MapPin, ExternalLink, AlertTriangle } from 'lucide-react';

export default function SearchDetail() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  const load = async () => {
    try {
      const d = await getSearch(id);
      setData(d);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [id]);

  useEffect(() => {
    if (data?.search?.status !== 'done' && data?.search?.status !== 'failed') {
      const t = setInterval(load, 3000);
      return () => clearInterval(t);
    }
  }, [data?.search?.status]);

  if (loading) return <div className="text-neutral-500">Carregando…</div>;
  if (!data) return <div className="text-rose-400">Pesquisa não encontrada</div>;

  const { search, leads } = data;
  const filtered = filter === 'all' ? leads : leads.filter((l) => l.priority === filter);
  const running = search.status !== 'done' && search.status !== 'failed';

  return (
    <div className="space-y-6">
      <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-neutral-400 hover:text-white transition-colors">
        <ArrowLeft className="w-4 h-4" /> Voltar
      </Link>

      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="text-xs uppercase tracking-widest text-amber-500/80">{search.nicho}</div>
          <h1
            data-testid={PSM.searchDetailTitle}
            className="text-3xl font-semibold text-white tracking-tight flex items-center gap-2"
          >
            <MapPin className="w-6 h-6 text-neutral-400" /> {search.regiao}
          </h1>
          <div className="mt-3 flex items-center gap-3">
            <span data-testid={PSM.searchStatus}><StatusBadge status={search.status} /></span>
            {search.status === 'done' && (
              <span className="text-sm text-neutral-400">
                <span className="text-white font-medium">{search.total_analyzed}</span> leads · {search.total_found} encontrados
              </span>
            )}
          </div>
        </div>
        <button
          onClick={load}
          data-testid={PSM.searchRefresh}
          className="inline-flex items-center gap-2 px-3 py-2 rounded-md border border-white/10 text-sm text-neutral-200 hover:bg-white/5"
        >
          <RefreshCw className="w-4 h-4" /> Atualizar
        </button>
      </div>

      {search.status === 'failed' && (
        <div className="rounded-md border border-rose-500/30 bg-rose-500/10 text-rose-300 p-4 text-sm">
          Erro na pesquisa: {search.error || 'desconhecido'}
        </div>
      )}

      {running && (
        <div className="rounded-md border border-blue-500/30 bg-blue-500/10 text-blue-200 p-4 text-sm">
          Coletando empresas e analisando presença digital… isso pode levar alguns segundos.
        </div>
      )}

      {leads.length > 0 && (
        <>
          <div className="flex gap-2 flex-wrap">
            {[
              ['all', `Todos (${leads.length})`],
              ['high', `Alta (${leads.filter(l => l.priority === 'high').length})`],
              ['medium', `Média (${leads.filter(l => l.priority === 'medium').length})`],
              ['low', `Baixa (${leads.filter(l => l.priority === 'low').length})`],
            ].map(([k, label]) => (
              <button
                key={k}
                onClick={() => setFilter(k)}
                className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                  filter === k
                    ? 'border-amber-500/60 bg-amber-500/10 text-amber-300'
                    : 'border-white/10 text-neutral-400 hover:text-white'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="grid gap-3">
            {filtered.map((lead) => (
              <LeadRow key={lead.id} lead={lead} />
            ))}
          </div>
        </>
      )}

      {!running && leads.length === 0 && (
        <div className="rounded-xl border border-dashed border-white/10 p-10 text-center text-neutral-400">
          Nenhuma empresa encontrada para &quot;{search.nicho}&quot; em &quot;{search.regiao}&quot;.
          <div className="text-sm mt-2 text-neutral-500">
            Tente outra grafia ou uma região maior.
          </div>
        </div>
      )}
    </div>
  );
}

function LeadRow({ lead }) {
  return (
    <Link
      to={`/leads/${lead.id}`}
      data-testid={PSM.leadCard}
      className="group flex items-center gap-4 rounded-xl border border-white/5 bg-white/[0.03] hover:bg-white/[0.06] p-4 transition-colors"
    >
      <ScorePill score={lead.score} priority={lead.priority} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-white font-medium truncate">{lead.name}</span>
          <PriorityBadge priority={lead.priority} />
        </div>
        <div className="text-sm text-neutral-400 mt-1 flex items-center gap-3 flex-wrap">
          {lead.category && <span className="capitalize">{lead.category.replace('_', ' ')}</span>}
          {lead.address && <span className="text-neutral-500">· {lead.address}</span>}
        </div>
        <div className="mt-2 flex items-center gap-2 flex-wrap">
          {!lead.has_website ? (
            <span className="text-xs inline-flex items-center gap-1 text-rose-300 bg-rose-500/10 border border-rose-500/20 px-2 py-0.5 rounded">
              <AlertTriangle className="w-3 h-3" /> Sem site
            </span>
          ) : lead.https ? (
            <span className="text-xs inline-flex items-center gap-1 text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded">
              <GlobeLock className="w-3 h-3" /> HTTPS
            </span>
          ) : (
            <span className="text-xs inline-flex items-center gap-1 text-amber-300 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded">
              <Globe className="w-3 h-3" /> HTTP
            </span>
          )}
          {lead.issues.slice(0, 2).map((iss) => (
            <span key={iss} className="text-xs text-neutral-400 bg-white/5 px-2 py-0.5 rounded">
              {iss}
            </span>
          ))}
          {lead.issues.length > 2 && (
            <span className="text-xs text-neutral-500">+{lead.issues.length - 2}</span>
          )}
        </div>
      </div>
      <span
        data-testid={PSM.leadOpen}
        className="opacity-0 group-hover:opacity-100 text-amber-500 transition-opacity"
      >
        <ExternalLink className="w-5 h-5" />
      </span>
    </Link>
  );
}
