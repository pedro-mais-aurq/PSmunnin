"use client";

import {
  useEffect,
  useState,
} from "react";

import { api } from "@/lib/api";
import type {
  Lead,
  Search,
  SearchDetail,
} from "@/lib/api";

import {
  LeadList,
} from "./LeadList";

import {
  MessagePreview,
} from "./MessagePreview";

import {
  MetricsGrid,
} from "./MetricsGrid";

import {
  PipelineStatus,
} from "./PipelineStatus";

import {
  SearchForm,
} from "./SearchForm";

const POLLING_INTERVAL_MS =
  3_000;

function isProcessing(
  search: Search | null,
): boolean {
  return (
    search?.status === "pending"
    || search?.status === "running"
  );
}

function statusDescription(
  search: Search | null,
): string {
  if (!search) {
    return (
      "Crie uma pesquisa para "
      + "iniciar a prospecção."
    );
  }

  if (
    search.status === "pending"
  ) {
    return (
      "A pesquisa foi criada "
      + "e aguarda o início "
      + "do processamento."
    );
  }

  if (
    search.status === "running"
  ) {
    return (
      `${search.total_found} `
      + "empresas encontradas; "
      + "a análise está em andamento."
    );
  }

  if (
    search.status === "done"
  ) {
    return (
      `${search.total_analyzed} `
      + "empresas analisadas "
      + "e disponíveis para revisão."
    );
  }

  return (
    search.error
    ?? "A pesquisa não pôde ser concluída."
  );
}

export function DashboardClient() {
  const [
    activeSearch,
    setActiveSearch,
  ] = useState<
    Search | null
  >(null);

  const [
    detail,
    setDetail,
  ] = useState<
    SearchDetail | null
  >(null);

  const [
    requestError,
    setRequestError,
  ] = useState("");

  const [
    loadingLatest,
    setLoadingLatest,
  ] = useState(true);

  const [
    selectedLead,
    setSelectedLead,
  ] = useState<
    Lead | null
  >(null);

  useEffect(() => {
    const controller =
      new AbortController();

    async function loadLatestSearch() {
      try {
        const searches =
          await api.listSearches(
            controller.signal
          );

        if (
          !controller
            .signal
            .aborted
          && searches.length > 0
        ) {
          setActiveSearch(
            searches[0]
          );
        }
      } catch (error) {
        if (
          !controller
            .signal
            .aborted
        ) {
          setRequestError(
            error instanceof Error
              ? error.message
              : "Não foi possível carregar as pesquisas.",
          );
        }
      } finally {
        if (
          !controller
            .signal
            .aborted
        ) {
          setLoadingLatest(
            false
          );
        }
      }
    }

    loadLatestSearch();

    return () => {
      controller.abort();
    };
  }, []);

  const activeSearchId =
    activeSearch?.id;

  useEffect(() => {
    if (!activeSearchId) {
      return;
    }

    const searchId: string =
      activeSearchId;

    let stopped = false;

    let timeoutId:
      | ReturnType<
          typeof globalThis.setTimeout
        >
      | undefined;

    const controller =
      new AbortController();

    async function fetchDetail() {
      try {
        const result =
          await api.getSearch(
            searchId,
            controller.signal,
          );

        if (stopped) {
          return;
        }

        setDetail(result);
        setActiveSearch(
          result.search
        );
        setRequestError("");

        if (
          isProcessing(
            result.search
          )
        ) {
          timeoutId =
            globalThis.setTimeout(
              fetchDetail,
              POLLING_INTERVAL_MS,
            );
        }
      } catch (error) {
        if (
          stopped
          || controller
            .signal
            .aborted
        ) {
          return;
        }

        setRequestError(
          error instanceof Error
            ? error.message
            : "Não foi possível consultar a pesquisa.",
        );
      }
    }

    fetchDetail();

    return () => {
      stopped = true;
      controller.abort();

      if (
        timeoutId !== undefined
      ) {
        globalThis.clearTimeout(
          timeoutId
        );
      }
    };
  }, [activeSearchId]);

  function handleCreated(
    search: Search,
  ) {
    setSelectedLead(null);
    setRequestError("");
    setActiveSearch(search);

    setDetail({
      search,
      leads: [],
    });
  }

  const search =
    detail?.search
    ?? activeSearch;

  const leads =
    detail?.leads
    ?? [];

  const progressSteps = [
    "Pesquisa",
    "Coleta",
    "Análise",
    "Resultados",
  ];

  const completedSteps =
    !search
      ? 0
      : search.status
        === "pending"
        ? 1
        : search.status
          === "running"
          ? 2
          : search.status
            === "done"
            ? 4
            : 1;

  return (
    <section
      className="content-scroll"
    >
      <header
        className={
          "hero parchment-panel"
        }
        id="dashboard"
      >
        <div
          className="hero-copy"
        >
          <p className="eyebrow">
            Painel do operador
          </p>

          <h1>
            Prospecção inteligente.
          </h1>

          <p
            className={
              "hero-description"
            }
          >
            Inicie buscas,
            acompanhe o processamento
            e revise oportunidades
            reais sem adicionar
            complexidade ao MVP.
          </p>

          <div
            className="hero-actions"
          >
            <a
              className={
                "primary-button"
              }
              href="#search"
            >
              Iniciar nova busca
            </a>

            <a
              className={
                "ghost-button"
              }
              href="#leads"
            >
              Revisar leads
            </a>
          </div>
        </div>

        <div
          className="hero-card"
          aria-label={
            "Resumo da pesquisa"
          }
        >
          <span
            className={
              "card-kicker"
            }
          >
            Execução atual
          </span>

          <strong>
            {loadingLatest
              ? "Carregando..."
              : search
                ? (
                  `${search.nicho}`
                  + ` · ${search.regiao}`
                )
                : "Nenhuma pesquisa"}
          </strong>

          <div
            className={
              "progress-line"
            }
          >
            {progressSteps.map(
              (step, index) => (
                <span
                  className={
                    index
                    < completedSteps
                      ? "is-complete"
                      : ""
                  }
                  key={step}
                >
                  {step}
                </span>
              )
            )}
          </div>

          <p>
            {statusDescription(
              search
            )}
          </p>
        </div>
      </header>

      <MetricsGrid
        detail={detail}
      />

      <section
        className={
          "workspace-grid"
        }
      >
        <article
          className={
            "parchment-panel "
            + "search-panel"
          }
          id="search"
        >
          <div
            className={
              "section-heading"
            }
          >
            <p className="eyebrow">
              Nova coleta
            </p>

            <h2>
              Buscar empresas
            </h2>
          </div>

          <SearchForm
            disabled={
              isProcessing(
                search
              )
            }
            onCreated={
              handleCreated
            }
          />
        </article>

        <article
          className={
            "parchment-panel "
            + "pipeline-panel"
          }
          id="pipeline"
        >
          <div
            className={
              "section-heading"
            }
          >
            <p className="eyebrow">
              Fluxo
            </p>

            <h2>
              Estado do pipeline
            </h2>
          </div>

          <PipelineStatus
            search={search}
            requestError={
              requestError
            }
          />
        </article>
      </section>

      <section
        className={
          "parchment-panel "
          + "leads-panel"
        }
        id="leads"
      >
        <div
          className={
            "section-heading"
          }
        >
          <p className="eyebrow">
            Prioridade comercial
          </p>

          <h2>
            Leads para revisão
          </h2>
        </div>

        {isProcessing(
          search
        ) ? (
          <div
            className={
              "empty-state"
            }
            aria-live="polite"
          >
            <strong>
              Pesquisa em andamento.
            </strong>

            <p>
              Os resultados
              aparecerão
              automaticamente
              após a análise.
            </p>
          </div>
        ) : (
          <LeadList
            leads={leads}
            onSelectLead={
              setSelectedLead
            }
          />
        )}
      </section>

      <MessagePreview
        lead={selectedLead}
        onClose={() =>
          setSelectedLead(null)
        }
      />
    </section>
  );
}
