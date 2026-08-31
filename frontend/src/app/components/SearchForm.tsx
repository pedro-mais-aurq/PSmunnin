"use client";

import {
  FormEvent,
  useEffect,
  useRef,
  useState,
} from "react";

import { api } from "@/lib/api";
import type {
  Search,
} from "@/lib/api";

type SearchFormProps = {
  disabled?: boolean;
  onCreated: (
    search: Search,
  ) => void;
};

export function SearchForm({
  disabled = false,
  onCreated,
}: SearchFormProps) {
  const [
    nicho,
    setNicho,
  ] = useState("");

  const [
    regiao,
    setRegiao,
  ] = useState("");

  const [
    limit,
    setLimit,
  ] = useState(25);

  const [
    loading,
    setLoading,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState("");

  const requestController =
    useRef<
      AbortController | null
    >(null);

  useEffect(() => {
    return () => {
      requestController
        .current
        ?.abort();
    };
  }, []);

  async function handleSubmit(
    event:
      FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (
      loading
      || disabled
    ) {
      return;
    }

    const normalizedNicho =
      nicho.trim();

    const normalizedRegiao =
      regiao.trim();

    if (
      normalizedNicho.length < 2
    ) {
      setError(
        "Informe um nicho válido."
      );

      return;
    }

    if (
      normalizedRegiao.length < 2
    ) {
      setError(
        "Informe uma região válida."
      );

      return;
    }

    requestController
      .current
      ?.abort();

    const controller =
      new AbortController();

    requestController.current =
      controller;

    setLoading(true);
    setError("");

    try {
      const result =
        await api.createSearch(
          {
            nicho:
              normalizedNicho,
            regiao:
              normalizedRegiao,
            limit,
          },
          controller.signal,
        );

      onCreated(result);
    } catch (requestError) {
      if (
        controller.signal.aborted
      ) {
        return;
      }

      setError(
        requestError
        instanceof Error
          ? requestError.message
          : "Não foi possível iniciar a pesquisa.",
      );
    } finally {
      if (
        requestController.current
        === controller
      ) {
        requestController.current =
          null;
      }

      setLoading(false);
    }
  }

  const formDisabled =
    loading || disabled;

  return (
    <form
      className="search-form"
      onSubmit={handleSubmit}
    >
      <label>
        Nicho

        <input
          value={nicho}
          onChange={(event) =>
            setNicho(
              event.target.value
            )
          }
          minLength={2}
          maxLength={80}
          placeholder="Ex.: dentistas"
          autoComplete="off"
          disabled={formDisabled}
          required
        />
      </label>

      <label>
        Região

        <input
          value={regiao}
          onChange={(event) =>
            setRegiao(
              event.target.value
            )
          }
          minLength={2}
          maxLength={120}
          placeholder={
            "Ex.: Belo Horizonte"
          }
          autoComplete="off"
          disabled={formDisabled}
          required
        />
      </label>

      <label
        className="range-field"
      >
        Máximo de empresas:{" "}
        {limit}

        <input
          type="range"
          min={1}
          max={60}
          step={1}
          value={limit}
          onChange={(event) =>
            setLimit(
              Number(
                event.target.value
              )
            )
          }
          disabled={formDisabled}
        />
      </label>

      <button
        className={
          "primary-button "
          + "form-button"
        }
        type="submit"
        disabled={formDisabled}
      >
        {loading
          ? "Criando pesquisa..."
          : disabled
            ? "Pesquisa em andamento"
            : "Buscar empresas"}
      </button>

      {error && (
        <p
          className="form-error"
          role="alert"
        >
          {error}
        </p>
      )}
    </form>
  );
}
