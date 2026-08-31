import type {
  SearchDetail,
} from "@/lib/api";

import {
  getLeadContacts,
  getWebsiteStatus,
  hasDirectContact,
} from "@/lib/leadPresentation";

type MetricsGridProps = {
  detail:
    | SearchDetail
    | null;
};

export function MetricsGrid({
  detail,
}: MetricsGridProps) {
  const leads =
    detail?.leads ?? [];

  const items = [
    {
      label:
        "Empresas encontradas",
      value:
        detail
          ?.search
          .total_found
        ?? "—",
      hint:
        "última pesquisa",
    },
    {
      label:
        "Empresas analisadas",
      value:
        detail
          ?.search
          .total_analyzed
        ?? "—",
      hint:
        "análises concluídas",
    },
    {
      label:
        "Site não encontrado",
      value:
        detail
          ? leads.filter(
              (lead) =>
                getWebsiteStatus(lead)
                === "not_found"
            ).length
          : "—",
      hint:
        "alta oportunidade",
    },
    {
      label:
        "Com contato direto",
      value:
        detail
          ? leads.filter(
              (lead) =>
                hasDirectContact(
                  getLeadContacts(lead)
                )
            ).length
          : "—",
      hint:
        "telefone, celular, WhatsApp ou e-mail",
    },
  ];

  return (
    <section
      className="metrics-grid"
      aria-label={
        "Métricas principais"
      }
    >
      {items.map((item) => (
        <article
          className="metric-card"
          key={item.label}
        >
          <span>
            {item.label}
          </span>

          <strong>
            {item.value}
          </strong>

          <small>
            {item.hint}
          </small>
        </article>
      ))}
    </section>
  );
}
