import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { listSearches, deleteSearch } from '@/lib/api';
import { PSM } from '@/constants/testIds';
import { StatusBadge } from '@/components/Badges';
import { Search as SearchIcon, MapPin, Plus, Trash2 } from 'lucide-react';

export default function Dashboard() {
  const [searches, setSearches] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const data = await listSearches();
      setSearches(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, []);

  const handleDelete = async (id, e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!window.confirm('Excluir esta pesquisa e seus leads?')) return;
    await deleteSearch(id);
    load();
  };

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 data-testid={PSM.dashboardTitle} className="text-3xl font-semibold tracking-tight text-white">
            Suas pesquisas
          </h1>
          <p className="text-neutral-400 mt-1">
            Empresas prospectadas por nicho e região, ordenadas pelo score de oportunidade.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="text-neutral-500 text-sm">Carregando…</div>
      ) : searches.length === 0 ? (
        <div
          data-testid={PSM.emptyState}
          className="rounded-xl border border-dashed border-white/10 bg-white/[0.02] p-12 text-center"
        >
          <div className="w-14 h-14 rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mx-auto mb-4">
            <SearchIcon className="w-6 h-6 text-amber-500" />
          </div>
          <h3 className="text-lg font-medium text-white">Nenhuma pesquisa ainda</h3>
          <p className="text-neutral-400 text-sm mt-1 mb-6">
            Comece informando um nicho (ex.: <em>restaurantes</em>) e uma região (ex.: <em>Curitiba</em>).
          </p>
          <Link
            to="/nova-pesquisa"
            data-testid={PSM.ctaCreateSearch}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-md bg-amber-500 text-black font-medium hover:bg-amber-400 transition-colors"
          >
            <Plus className="w-4 h-4" /> Criar primeira pesquisa
          </Link>
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {searches.map((s) => (
            <Link
              key={s.id}
              to={`/pesquisas/${s.id}`}
              data-testid={PSM.searchListItem}
              className="group block rounded-xl border border-white/5 bg-white/[0.03] hover:bg-white/[0.06] p-5 transition-colors"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-xs uppercase tracking-widest text-amber-500/80 mb-1">
                    {s.nicho}
                  </div>
                  <div className="flex items-center gap-1.5 text-white text-lg font-medium">
                    <MapPin className="w-4 h-4 text-neutral-400" />
                    <span className="truncate">{s.regiao}</span>
                  </div>
                </div>
                <StatusBadge status={s.status} />
              </div>
              <div className="mt-4 flex items-center justify-between text-sm">
                <div className="text-neutral-400">
                  {s.status === 'done' ? (
                    <>
                      <span className="text-white font-medium">{s.total_analyzed}</span> leads analisados
                    </>
                  ) : s.status === 'failed' ? (
                    <span className="text-rose-400">Erro: {s.error || 'desconhecido'}</span>
                  ) : (
                    <>Buscando empresas…</>
                  )}
                </div>
                <button
                  onClick={(e) => handleDelete(s.id, e)}
                  className="opacity-0 group-hover:opacity-100 transition-opacity text-neutral-500 hover:text-rose-400 p-1"
                  aria-label="Excluir pesquisa"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
