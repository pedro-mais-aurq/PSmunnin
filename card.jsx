import { Link, Outlet, useLocation } from 'react-router-dom';
import { PSM } from '@/constants/testIds';
import { Feather, Plus, LayoutGrid } from 'lucide-react';

export default function Layout() {
  const loc = useLocation();
  const isActive = (path) => (loc.pathname === path);

  return (
    <div className="min-h-screen bg-[#0b0d12] text-neutral-100 flex flex-col">
      <header className="border-b border-white/5 bg-black/40 backdrop-blur sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" data-testid={PSM.navHome} className="flex items-center gap-3 group">
            <div className="w-9 h-9 rounded-md bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center shadow-lg shadow-amber-500/20">
              <Feather className="w-5 h-5 text-black" strokeWidth={2.5} />
            </div>
            <div className="leading-tight">
              <div className="text-lg font-semibold tracking-tight text-white">PS Munnin</div>
              <div className="text-[11px] uppercase tracking-widest text-amber-500/80">
                lead prospecting
              </div>
            </div>
          </Link>

          <nav className="flex items-center gap-2">
            <Link
              to="/"
              className={`inline-flex items-center gap-2 px-3 py-2 text-sm rounded-md transition-colors ${
                isActive('/')
                  ? 'bg-white/10 text-white'
                  : 'text-neutral-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <LayoutGrid className="w-4 h-4" />
              Pesquisas
            </Link>
            <Link
              to="/nova-pesquisa"
              data-testid={PSM.navNewSearch}
              className="inline-flex items-center gap-2 px-3 py-2 text-sm rounded-md bg-amber-500 text-black font-medium hover:bg-amber-400 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Nova pesquisa
            </Link>
          </nav>
        </div>
      </header>

      <main className="flex-1">
        <div className="max-w-6xl mx-auto px-6 py-8">
          <Outlet />
        </div>
      </main>

      <footer className="border-t border-white/5 py-6 text-center text-xs text-neutral-500">
        PS Munnin MVP · dados de <a className="text-amber-500 hover:underline" href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> · use com responsabilidade
      </footer>
    </div>
  );
}
