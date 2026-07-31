"use client";

import {
  useState,
} from "react";

import type {
  Lead,
  LeadPriority,
} from "@/lib/api";

type PriorityFilter =
  | "all"
  | LeadPriority;

type LeadListProps = {
  leads: Lead[];
  onSelectLead: (
    lead: Lead,
  ) => void;
};

const priorityLabels: Record<
  LeadPriority,
  string
> = {
  high: "Alta",
  medium: "Média",
  low: "Baixa",
};

function normalizeExternalUrl(
  value: string,
): string {
  const trimmedValue =
    value.trim();

  if (
    /^https?:\/\//i.test(
      trimmedValue
    )
  ) {
    return trimmedValue;
  }

  return (
    `https://${trimmedValue}`
  );
}

export function LeadList({
  leads,
  onSelectLead,
}: LeadListProps) {
  const [
    filter,
    setFilter,
  ] = useState<
    PriorityFilter
  >("all");

  const visibleLeads =
    filter === "all"
      ? leads
      : leads.filter(
          (lead) =>
            lead.priority
            === filter
        );

  return (
    <>
      <div
        className="lead-toolbar"
      >
        <label>
          Filtrar por prioridade

          <select
            value={filter}
            onChange={(event) =>
              setFilter(
                event.target
                  .value as PriorityFilter
              )
            }
          >
            <option value="all">
              Todas
            </option>

            <option value="high">
              Alta
            </option>

            <option value="medium">
              Média
            </option>

            <option value="low">
              Baixa
            </option>
          </select>
        </label>
      </div>

      {visibleLeads.length
      === 0 ? (
        <div
          className="empty-state"
        >
          <strong>
            Nenhum lead disponível.
          </strong>

          <p>
            Conclua uma pesquisa
            ou altere o filtro
            selecionado.
          </p>
        </div>
      ) : (
        <div className="lead-list">
          {visibleLeads.map(
            (lead) => (
              <article
                className="lead-card"
                key={lead.id}
              >
                <div
                  className="lead-copy"
                >
                  <strong>
                    {lead.name}
                  </strong>

                  <span>
                    {lead.category
                      ?? "Categoria não informada"}
                    {" · "}
                    {lead.address
                      ?? "Endereço não informado"}
                  </span>

                  <p>
                    {lead.issues[0]
                      ?? "Nenhum problema técnico identificado."}
                  </p>

                  <div
                    className={
                      "lead-actions"
                    }
                  >
                    {lead.website ? (
                      <a
                        className={
                          "ghost-button "
                          + "compact"
                        }
                        href={
                          normalizeExternalUrl(
                            lead.website
                          )
                        }
                        target="_blank"
                        rel="noreferrer"
                      >
                        Abrir site
                      </a>
                    ) : (
                      <span
                        className={
                          "no-website"
                        }
                      >
                        Sem site
                        cadastrado
                      </span>
                    )}

                    <button
                      className={
                        "primary-button "
                        + "compact"
                      }
                      type="button"
                      onClick={() =>
                        onSelectLead(
                          lead
                        )
                      }
                    >
                      Gerar mensagem
                    </button>
                  </div>
                </div>

                <div
                  className={
                    "score-pill"
                  }
                >
                  <small>
                    {
                      priorityLabels[
                        lead.priority
                      ]
                    }
                  </small>

                  <b>
                    {lead.score}
                  </b>
                </div>
              </article>
            )
          )}
        </div>
      )}
    </>
  );
}
