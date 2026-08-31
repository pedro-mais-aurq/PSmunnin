"use client";

import {
  useEffect,
  useRef,
  useState,
} from "react";

import { api } from "@/lib/api";
import type {
  ContactChannel,
  ContactMessage,
  Lead,
} from "@/lib/api";

type MessagePreviewProps = {
  lead: Lead | null;
  onClose: () => void;
};

export function MessagePreview({
  lead,
  onClose,
}: MessagePreviewProps) {
  const [
    channel,
    setChannel,
  ] = useState<
    ContactChannel
  >("email");

  const [
    message,
    setMessage,
  ] = useState<
    ContactMessage | null
  >(null);

  const [
    loading,
    setLoading,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState("");

  const [
    copyFeedback,
    setCopyFeedback,
  ] = useState("");

  const requestController =
    useRef<
      AbortController | null
    >(null);

  useEffect(() => {
    requestController
      .current
      ?.abort();

    setChannel("email");
    setMessage(null);
    setError("");
    setCopyFeedback("");

    return () => {
      requestController
        .current
        ?.abort();
    };
  }, [lead?.id]);

  if (!lead) {
    return null;
  }

  const leadId = lead.id;

  async function generate() {
    requestController
      .current
      ?.abort();

    const controller =
      new AbortController();

    requestController.current =
      controller;

    setLoading(true);
    setError("");
    setCopyFeedback("");

    try {
      const result =
        await api.generateMessage(
          leadId,
          channel,
          controller.signal,
        );

      setMessage(result);
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
          : "Não foi possível gerar a mensagem.",
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

  async function copyMessage() {
    if (!message) {
      return;
    }

    const completeMessage =
      message.subject
        ? (
          `${message.subject}`
          + `\n\n${message.body}`
        )
        : message.body;

    try {
      await navigator
        .clipboard
        .writeText(
          completeMessage
        );

      setCopyFeedback(
        "Mensagem copiada."
      );
    } catch {
      setCopyFeedback(
        "Não foi possível copiar automaticamente."
      );
    }
  }

  return (
    <section
      className={
        "parchment-panel "
        + "message-panel"
      }
      id="message"
      aria-labelledby={
        "message-title"
      }
    >
      <div
        className={
          "section-heading "
          + "horizontal-heading"
        }
      >
        <div>
          <p className="eyebrow">
            Contato manual
          </p>

          <h2 id="message-title">
            {lead.name}
          </h2>
        </div>

        <button
          className={
            "ghost-button compact"
          }
          type="button"
          onClick={onClose}
        >
          Fechar
        </button>
      </div>

      <div
        className={
          "message-controls"
        }
      >
        <label>
          Canal

          <select
            value={channel}
            onChange={(event) => {
              setChannel(
                event.target.value as ContactChannel
              );

              setMessage(null);
              setError("");
              setCopyFeedback("");
            }}
          >
            <option value="email">
              E-mail
            </option>

            <option value="whatsapp">
              WhatsApp
            </option>
          </select>
        </label>

        <button
          className={
            "primary-button"
          }
          type="button"
          onClick={generate}
          disabled={loading}
        >
          {loading
            ? "Gerando..."
            : "Gerar mensagem"}
        </button>
      </div>

      {error && (
        <p
          className="form-error"
          role="alert"
        >
          {error}
        </p>
      )}

      {message && (
        <div
          className={
            "message-output"
          }
        >
          <label>
            Assunto

            <input
              value={
                message.subject
              }
              readOnly
            />
          </label>

          <label>
            Mensagem

            <textarea
              value={message.body}
              rows={14}
              readOnly
            />
          </label>

          <button
            className={
              "ghost-button"
            }
            type="button"
            onClick={copyMessage}
          >
            Copiar mensagem
          </button>

          {copyFeedback && (
            <p
              className={
                "copy-feedback"
              }
              aria-live="polite"
            >
              {copyFeedback}
            </p>
          )}
        </div>
      )}
    </section>
  );
}
