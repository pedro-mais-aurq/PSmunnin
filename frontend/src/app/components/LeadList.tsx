"use client";

import {
  useState,
} from "react";

import type {
  Lead,
  LeadPriority,
} from "@/lib/api";

import {
  buildExternalLink,
  buildMailtoLink,
  buildTelLink,
  buildWhatsappLink,
  getLeadContacts,
  getWebsiteStatus,
  websiteBadgeText,
  websiteBadgeTone,
} from "@/lib/leadPresentation";

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

function ContactLinkGroup({
  label,
  values,
  buildHref,
}: {
  label: string;
  values: string[];
  buildHref: (value: string) => string;
}) {
  if (values.length === 0) {
    return null;
  }

  return (
    <div className="contact-group">
      <span className="contact-group-label">
        {label}
      </span>

      <div className="contact-chip-row">
        {values.map((value, index) => (
          <a
            className="contact-chip"
            href={buildHref(value)}
            key={`${label}-${index}-${value}`}
            aria-label={`${label}: ${value}`}
          >
            {value}
          </a>
        ))}
      </div>
    </div>
  );
}

function ExternalContactLinkGroup({
  label,
  values,
  buildHref,
}: {
  label: string;
  values: string[];
  buildHref: (value: string) => string;
}) {
  if (values.length === 0) {
    return null;
  }

  return (
    <div className="contact-group">
      <span className="contact-group-label">
        {label}
      </span>

      <div className="contact-chip-row">
        {values.map((value, index) => (
          <a
            className="contact-chip"
            href={buildHref(value)}
            key={`${label}-${index}-${value}`}
            aria-label={`${label}: ${value}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            {value}
          </a>
        ))}
      </div>
    </div>
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
            (lead) => {
              const contacts =
                getLeadContacts(lead);

              const websiteStatus =
                getWebsiteStatus(lead);

              const badgeText =
                websiteBadgeText(
                  websiteStatus,
                  lead.website_reachable
                );

              const badgeTone =
                websiteBadgeTone(
                  websiteStatus,
                  lead.website_reachable
                );

              return (
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

                    <div
                      className={
                        `website-badge `
                        + `website-badge-${badgeTone}`
                      }
                    >
                      <span
                        className="website-badge-dot"
                        aria-hidden="true"
                      />

                      {badgeText}
                    </div>

                    <p>
                      {lead.issues[0]
                        ?? "Nenhum problema técnico identificado."}
                    </p>

                    <div className="contact-groups">
                      <ContactLinkGroup
                        label="Telefone"
                        values={contacts.phone}
                        buildHref={buildTelLink}
                      />

                      <ContactLinkGroup
                        label="Celular"
                        values={contacts.mobile}
                        buildHref={buildTelLink}
                      />

                      <ContactLinkGroup
                        label="WhatsApp"
                        values={contacts.whatsapp}
                        buildHref={buildWhatsappLink}
                      />

                      <ContactLinkGroup
                        label="E-mail"
                        values={contacts.email}
                        buildHref={buildMailtoLink}
                      />

                      <ExternalContactLinkGroup
                        label="Instagram"
                        values={contacts.instagram}
                        buildHref={buildExternalLink}
                      />

                      <ExternalContactLinkGroup
                        label="Facebook"
                        values={contacts.facebook}
                        buildHref={buildExternalLink}
                      />

                      <ExternalContactLinkGroup
                        label="LinkedIn"
                        values={contacts.linkedin}
                        buildHref={buildExternalLink}
                      />
                    </div>

                    <div
                      className={
                        "lead-actions"
                      }
                    >
                      {websiteStatus
                      === "confirmed"
                      && lead.website ? (
                        <a
                          className={
                            "ghost-button "
                            + "compact"
                          }
                          href={
                            buildExternalLink(
                              lead.website
                            )
                          }
                          target="_blank"
                          rel="noopener noreferrer"
                          aria-label={
                            `Abrir site de ${lead.name}`
                          }
                        >
                          Abrir site
                        </a>
                      ) : null}

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
              );
            }
          )}
        </div>
      )}
    </>
  );
}
