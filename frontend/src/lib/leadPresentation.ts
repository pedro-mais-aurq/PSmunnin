import type {
  ContactInfo,
  Lead,
  WebsiteStatus,
} from "./api";

const EMPTY_CONTACTS: ContactInfo = {
  phone: [],
  mobile: [],
  whatsapp: [],
  email: [],
  instagram: [],
  facebook: [],
  linkedin: [],
};

/**
 * Contrato Alpha 0.1, seção 10 — fallback obrigatório
 * para leads antigos sem `contacts` persistido.
 */
export function getLeadContacts(
  lead: Lead,
): ContactInfo {
  if (lead.contacts) {
    return lead.contacts;
  }

  return {
    ...EMPTY_CONTACTS,
    phone: lead.phone
      ? [lead.phone]
      : [],
  };
}

/**
 * Contrato Alpha 0.1, seção 10 — fallback obrigatório
 * para `website_status` ausente em registros antigos.
 * Nunca infere `not_found` a partir de dado ausente.
 */
export function getWebsiteStatus(
  lead: Lead,
): WebsiteStatus {
  if (lead.website_status) {
    return lead.website_status;
  }

  return lead.website
    ? "confirmed"
    : "unknown";
}

export function hasDirectContact(
  contacts: ContactInfo,
): boolean {
  return (
    contacts.phone.length > 0
    || contacts.mobile.length > 0
    || contacts.whatsapp.length > 0
    || contacts.email.length > 0
  );
}

/**
 * Contrato Alpha 0.1, seção 11.1 — textos normativos de status.
 */
export function websiteBadgeText(
  status: WebsiteStatus,
  websiteReachable: boolean | null,
): string {
  if (status === "confirmed") {
    return websiteReachable === false
      ? "Site cadastrado, inacessível"
      : "Site confirmado";
  }

  if (status === "not_found") {
    return "Site não encontrado";
  }

  return "Verificação inconclusiva";
}

export function websiteBadgeTone(
  status: WebsiteStatus,
  websiteReachable: boolean | null,
): "positive" | "warning" | "neutral" {
  if (
    status === "confirmed"
    && websiteReachable !== false
  ) {
    return "positive";
  }

  if (
    status === "confirmed"
    && websiteReachable === false
  ) {
    return "warning";
  }

  if (status === "not_found") {
    return "neutral";
  }

  return "neutral";
}

function stripNonDigits(
  value: string,
): string {
  return value.replace(/\D/g, "");
}

export function buildTelLink(
  value: string,
): string {
  return `tel:${stripNonDigits(value)}`;
}

export function buildWhatsappLink(
  value: string,
): string {
  return `https://wa.me/${stripNonDigits(value)}`;
}

export function buildMailtoLink(
  value: string,
): string {
  return `mailto:${value.trim()}`;
}

export function buildExternalLink(
  value: string,
): string {
  const trimmedValue = value.trim();

  if (/^https?:\/\//i.test(trimmedValue)) {
    return trimmedValue;
  }

  return `https://${trimmedValue}`;
}
