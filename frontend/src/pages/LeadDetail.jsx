import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { getLead, generateMessage } from '@/lib/api';
import { PSM } from '@/constants/testIds';
import { ScorePill, PriorityBadge } from '@/components/Badges';
import {
  ArrowLeft, Globe, GlobeLock, MapPin, Phone, ExternalLink, Copy, Check,
  Mail, MessageCircle, AlertTriangle, CheckCircle2, XCircle, Clock,
} from 'lucide-react';

export default function LeadDetail() {
  const { id } = useParams();
  const [lead, setLead] = useState(null);
  const [loading, setLoading] = useState(true);
  const [channel, setChannel] = useState('email');
  const [message, setMessage] = useState(null);
  const [genLoading, setGenLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const l = await getLead(id);
        setLead(l);
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  const generate = async (ch) => {
    setChannel(ch);
    setGenLoading(true);
    try {
      const m = await generateMessage(id, ch);
      setMessage(m);
    } finally {
      setGenLoading(false);
    }
  };

  const copyMessage = async () => {
    if (!message) return;
    const text = `${message.subject}\n\n${message.body}`;
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) return <div className="text-neutral-500">Carregando…</div>;
  if (!lead) return <div className="text-rose-400">Lead não encontrado</div>;

  return (
    <div className="space-y-6">
      <Link
        to={`/pesquisas/${lead.search_id}`}
        data-testid={PSM.leadBack}
        className="inline-flex items-center gap-1.5 text-sm text-neutral-400 hover:text-white transition-colors"
      >
        <ArrowLeft className="w-4 h-4" /> Voltar aos leads
      </Link>

      <div className="flex items-start gap-6 flex-wrap">
        <div data-testid={PSM.leadDetailScore}>
          <ScorePill score={lead.score} priority={lead.priority} size="lg" />
        </div>
        <div className="flex-1 min-w-0">
          <h1 data-testid={PSM.leadDetailName} className="text-3xl font-semibold text-white tracking-tight">
            {lead.name}
          </h1>
          <div className="mt-2 flex items-center gap-2 flex-wrap">
            <PriorityBadge priority={lead.priority} />
            {lead.category && (
              <span className="text-xs px-2 py-1 rounded bg-white/5 text-neutral-300 capitalize">
                {lead.category.replace('_', ' ')}
              </span>
            )}
          </div>
          <div className="mt-3 space-y-1.5 text-sm text-neutral-300">
            {lead.address && (
              <div className="flex items-center gap-2"><MapPin className="w-4 h-4 text-neutral-500" /> {lead.address}</div>
            )}
            {lead.phone && (
              <div className="flex items-center gap-2"><Phone className="w-4 h-4 text-neutral-500" /> {lead.phone}</div>
            )}
            {lead.website && (
              <a
                href={lead.website}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 text-amber-400 hover:text-amber-300"
              >
                <ExternalLink className="w-4 h-4" /> {lead.website}
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Digital presence analysis */}
      <section className="rounded-xl border border-white/5 bg-white/[0.03] p-5">
        <h2 className="text-sm uppercase tracking-widest text-neutral-400 mb-4">Análise da presença digital</h2>
        <div className="grid gap-3 md:grid-cols-2">
          <Metric
            ok={lead.has_website}
            label="Possui site"
            icon={lead.has_website ? <Globe className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
            value={lead.has_website ? 'Sim' : 'Não'}
          />
          {lead.has_website && (
            <>
              <Metric
                ok={lead.website_reachable}
                label="Site acessível"
                icon={<Globe className="w-4 h-4" />}
                value={lead.website_reachable ? `HTTP ${lead.status_code || ''}` : 'Fora do ar'}
              />
              <Metric
                ok={lead.https}
                label="HTTPS"
                icon={<GlobeLock className="w-4 h-4" />}
                value={lead.https === null ? '—' : lead.https ? 'Ativado' : 'Sem HTTPS'}
              />
              <Metric
                ok={lead.response_ms !== null && lead.response_ms <= 3000}
                label="Tempo de resposta"
                icon={<Clock className="w-4 h-4" />}
                value={lead.response_ms !== null ? `${lead.response_ms} ms` : '—'}
              />
              <Metric ok={lead.has_viewport} label="Responsivo (viewport)" value={lead.has_viewport ? 'Sim' : 'Não'} />
              <Metric ok={lead.has_title} label="Tag <title>" value={lead.has_title ? 'Sim' : 'Não'} />
              <Metric ok={lead.has_meta_description} label="Meta description (SEO)" value={lead.has_meta_description ? 'Sim' : 'Não'} />
              <Metric ok={lead.has_favicon} label="Favicon" value={lead.has_favicon ? 'Sim' : 'Não'} />
            </>
          )}
        </div>

        {lead.issues.length > 0 && (
          <div data-testid={PSM.leadDetailIssues} className="mt-5 rounded-md border border-amber-500/20 bg-amber-500/[0.05] p-4">
            <div className="flex items-center gap-2 text-amber-400 text-sm font-medium mb-2">
              <AlertTriangle className="w-4 h-4" /> Oportunidades de melhoria
            </div>
            <ul className="text-sm text-neutral-200 space-y-1">
              {lead.issues.map((iss) => (
                <li key={iss} className="flex items-start gap-2">
                  <span className="text-amber-500 mt-1">•</span>
                  <span>{iss}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {/* Contact message generator */}
      <section className="rounded-xl border border-white/5 bg-white/[0.03] p-5">
        <h2 className="text-sm uppercase tracking-widest text-neutral-400 mb-4">Sugestão de contato</h2>
        <div className="flex gap-2 mb-4">
          <button
            data-testid={PSM.leadMessageEmail}
            onClick={() => generate('email')}
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-md text-sm border transition-colors ${
              channel === 'email' && message
                ? 'bg-amber-500 text-black border-amber-500'
                : 'border-white/10 text-neutral-200 hover:bg-white/5'
            }`}
          >
            <Mail className="w-4 h-4" /> E-mail
          </button>
          <button
            data-testid={PSM.leadMessageWhatsapp}
            onClick={() => generate('whatsapp')}
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-md text-sm border transition-colors ${
              channel === 'whatsapp' && message
                ? 'bg-amber-500 text-black border-amber-500'
                : 'border-white/10 text-neutral-200 hover:bg-white/5'
            }`}
          >
            <MessageCircle className="w-4 h-4" /> WhatsApp
          </button>
          {!message && (
            <button
              data-testid={PSM.leadGenerateMessage}
              onClick={() => generate('email')}
              disabled={genLoading}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-md text-sm bg-amber-500 text-black font-medium hover:bg-amber-400 disabled:opacity-60"
            >
              {genLoading ? 'Gerando…' : 'Gerar mensagem'}
            </button>
          )}
        </div>

        {message ? (
          <div className="rounded-md border border-white/10 bg-black/40 p-4 space-y-3">
            {channel === 'email' && (
              <div className="text-xs uppercase tracking-widest text-neutral-500">
                Assunto: <span className="text-neutral-200 normal-case">{message.subject}</span>
              </div>
            )}
            <pre
              data-testid={PSM.leadMessageBody}
              className="whitespace-pre-wrap font-sans text-sm text-neutral-100 leading-relaxed"
            >
              {message.body}
            </pre>
            <div className="flex justify-end">
              <button
                data-testid={PSM.leadMessageCopy}
                onClick={copyMessage}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md border border-white/10 text-sm hover:bg-white/5"
              >
                {copied ? (
                  <><Check className="w-4 h-4 text-emerald-400" /> Copiado</>
                ) : (
                  <><Copy className="w-4 h-4" /> Copiar</>
                )}
              </button>
            </div>
          </div>
        ) : (
          <div className="text-sm text-neutral-500">
            Clique em <em>Gerar mensagem</em> para criar um contato personalizado com base nos pontos identificados.
          </div>
        )}
      </section>
    </div>
  );
}

function Metric({ ok, label, value, icon }) {
  const color =
    ok === true ? 'text-emerald-400' :
    ok === false ? 'text-rose-400' :
    'text-neutral-500';
  const iconEl = icon || (ok === true ? <CheckCircle2 className="w-4 h-4" /> : ok === false ? <XCircle className="w-4 h-4" /> : <Clock className="w-4 h-4" />);
  return (
    <div className="flex items-center justify-between rounded-md bg-black/30 border border-white/5 px-3 py-2.5">
      <div className="flex items-center gap-2 text-sm text-neutral-300">
        <span className={color}>{iconEl}</span>
        {label}
      </div>
      <div className={`text-sm ${color} font-medium`}>{value}</div>
    </div>
  );
}
