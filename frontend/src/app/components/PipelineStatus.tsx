import type {
  Search,
} from "@/lib/api";

type PipelineStatusProps = {
  search: Search | null;
  requestError: string;
};

type StepState =
  | "idle"
  | "active"
  | "complete"
  | "error";

function getStepClass(
  state: StepState,
): string {
  if (state === "active") {
    return "is-active";
  }

  if (state === "complete") {
    return "is-complete";
  }

  if (state === "error") {
    return "is-error";
  }

  return "";
}

export function PipelineStatus({
  search,
  requestError,
}: PipelineStatusProps) {
  const status =
    search?.status;

  const steps: Array<{
    label: string;
    state: StepState;
  }> = [
    {
      label:
        "Pesquisa criada",
      state:
        search
          ? "complete"
          : "idle",
    },
    {
      label:
        "Coleta e análise",
      state:
        status === "pending"
        || status === "running"
          ? "active"
          : status === "done"
            ? "complete"
            : status === "failed"
              ? "error"
              : "idle",
    },
    {
      label:
        "Resultados disponíveis",
      state:
        status === "done"
          ? "complete"
          : status === "failed"
            ? "error"
            : "idle",
    },
    {
      label:
        "Revisão humana",
      state:
        status === "done"
          ? "active"
          : "idle",
    },
  ];

  return (
    <>
      <ol className="timeline">
        {steps.map((step) => (
          <li
            className={
              getStepClass(
                step.state
              )
            }
            key={step.label}
          >
            <span />
            {step.label}
          </li>
        ))}
      </ol>

      {search?.status
        === "failed" && (
        <p
          className={
            "pipeline-error"
          }
          role="alert"
        >
          {search.error
            ?? "A pesquisa falhou."}
        </p>
      )}

      {requestError && (
        <p
          className={
            "pipeline-error"
          }
          role="alert"
        >
          {requestError}
        </p>
      )}
    </>
  );
}
