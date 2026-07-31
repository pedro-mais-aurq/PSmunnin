import type {
  SearchDetail,
} from "@/lib/api";

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
        "Sem site",
      value:
        detail
          ? leads.filter(
              (lead) =>
                !lead.has_website
            ).length
          : "—",
      hint:
        "alta oportunidade",
    },
    {
      label:
        "Prioridade alta",
      value:
        detail
          ? leads.filter(
              (lead) =>
                lead.priority
                === "high"
            ).length
          : "—",
      hint:
        "melhores oportunidades",
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
