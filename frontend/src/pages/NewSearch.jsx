import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createSearch } from '@/lib/api';
import { PSM } from '@/constants/testIds';
import { Sparkles, Loader2 } from 'lucide-react';

const EXAMPLES = [
  { nicho: 'restaurantes', regiao: 'Curitiba' },
  { nicho: 'academias', regiao: 'Florianópolis' },
  { nicho: 'clínicas', regiao: 'Belo Horizonte' },
  { nicho: 'padarias', regiao: 'Porto Alegre' },
];

export default function NewSearch() {
  const nav = useNavigate();
  const [nicho, setNicho] = useState('');
  const [regiao, setRegiao] = useState('');
  const [limit, setLimit] = useState(25);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    if (nicho.trim().length < 2 || regiao.trim().length < 2) {
      setError('Preencha nicho e região.');
      return;
    }
    setSubmitting(true);
    try {
      const search = await createSearch({ nicho: nicho.trim(), regiao: regiao.trim(), limit });
      nav(`/pesquisas/${search.id}`);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Erro ao criar pesquisa');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-8">
        <div className="inline-flex items-center gap-2 text-xs uppercase tracking-widest text-amber-500/90 mb-3">
          <Sparkles className="w-3.5 h-3.5" />
          Nova prospecção
        </div>
        <h1 className="text-3xl font-semibold text-white tracking-tight">
          Encontre empresas com presença digital fraca
        </h1>
        <p className="text-neutral-400 mt-2">
          Informe o nicho e a região. O sistema busca as empresas no OpenStreetMap,
          analisa sites, HTTPS, SEO básico e performance, e ordena pelas melhores
          oportunidades de venda para seus serviços.
        </p>
      </div>

      <form onSubmit={submit} className="rounded-xl border border-white/5 bg-white/[0.03] p-6 space-y-5">
        <div>
          <label className="block text-sm font-medium text-neutral-200 mb-1.5">
            Nicho
          </label>
          <input
            data-testid={PSM.formNicho}
            type="text"
            value={nicho}
            onChange={(e) => setNicho(e.target.value)}
            placeholder="ex.: restaurantes, academias, clínicas, padarias…"
            className="w-full rounded-md bg-black/40 border border-white/10 px-3.5 py-2.5 text-white placeholder:text-neutral-600 focus:outline-none focus:border-amber-500/60 focus:ring-1 focus:ring-amber-500/30"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-neutral-200 mb-1.5">
            Região (cidade)
          </label>
          <input
            data-testid={PSM.formRegiao}
            type="text"
            value={regiao}
            onChange={(e) => setRegiao(e.target.value)}
            placeholder="ex.: Curitiba, São Paulo, Recife…"
            className="w-full rounded-md bg-black/40 border border-white/10 px-3.5 py-2.5 text-white placeholder:text-neutral-600 focus:outline-none focus:border-amber-500/60 focus:ring-1 focus:ring-amber-500/30"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-neutral-200 mb-1.5">
            Máximo de empresas: <span className="text-amber-500 font-semibold">{limit}</span>
          </label>
          <input
            data-testid={PSM.formLimit}
            type="range"
            min={5}
            max={60}
            step={5}
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="w-full accent-amber-500"
          />
          <div className="flex justify-between text-xs text-neutral-500 mt-1">
            <span>5</span><span>60</span>
          </div>
        </div>

        {error && (
          <div data-testid={PSM.formError} className="text-sm text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-md px-3 py-2">
            {error}
          </div>
        )}

        <button
          type="submit"
          data-testid={PSM.formSubmit}
          disabled={submitting}
          className="w-full inline-flex items-center justify-center gap-2 px-5 py-3 rounded-md bg-amber-500 text-black font-medium hover:bg-amber-400 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
        >
          {submitting ? (
            <><Loader2 className="w-4 h-4 animate-spin" /> Iniciando…</>
          ) : (
            <>Iniciar prospecção</>
          )}
        </button>
      </form>

      <div className="mt-6">
        <div className="text-xs uppercase tracking-widest text-neutral-500 mb-2">Exemplos rápidos</div>
        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={`${ex.nicho}-${ex.regiao}`}
              type="button"
              onClick={() => { setNicho(ex.nicho); setRegiao(ex.regiao); }}
              className="text-xs px-3 py-1.5 rounded-full border border-white/10 bg-white/[0.03] text-neutral-300 hover:border-amber-500/40 hover:text-white transition-colors"
            >
              {ex.nicho} · {ex.regiao}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
