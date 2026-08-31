export type SearchStatus =
  | "pending"
  | "running"
  | "done"
  | "failed";

export type LeadPriority =
  | "low"
  | "medium"
  | "high";

export type ContactChannel =
  | "email"
  | "whatsapp";

export type WebsiteStatus =
  | "confirmed"
  | "not_found"
  | "unknown";

export type WebsiteSource =
  | "osm_website"
  | "osm_contact_website"
  | "osm_url"
  | "email_domain"
  | "web_search"
  | null;

export type ContactInfo = {
  phone: string[];
  mobile: string[];
  whatsapp: string[];
  email: string[];
  instagram: string[];
  facebook: string[];
  linkedin: string[];
};

export type SearchCreate = {
  nicho: string;
  regiao: string;
  limit: number;
};

export type Search = {
  id: string;
  nicho: string;
  regiao: string;
  status: SearchStatus;
  total_found: number;
  total_analyzed: number;
  error: string | null;
  created_at: string;
  updated_at: string;
};

export type Lead = {
  id: string;
  search_id: string;
  name: string;
  category: string | null;
  address: string | null;
  phone: string | null;
  website: string | null;
  lat: number | null;
  lon: number | null;
  has_website: boolean;
  website_reachable: boolean | null;
  https: boolean | null;
  response_ms: number | null;
  has_title: boolean | null;
  has_meta_description: boolean | null;
  has_viewport: boolean | null;
  has_favicon: boolean | null;
  status_code: number | null;
  issues: string[];
  score: number;
  priority: LeadPriority;
  created_at: string;

  contacts?: ContactInfo;
  website_status?: WebsiteStatus;
  website_source?: WebsiteSource;
};

export type SearchDetail = {
  search: Search;
  leads: Lead[];
};

export type ContactMessage = {
  subject: string;
  body: string;
  channel:
    | "email"
    | "whatsapp"
    | "generic";
};

const DEFAULT_TIMEOUT_MS = 20_000;

class ApiRequestError extends Error {
  constructor(message: string, readonly status: number | null) {
    super(message);
    this.name = "ApiRequestError";
  }
}

export function isRetryableRequestError(error: unknown): boolean {
  if (error instanceof ApiRequestError) {
    return (
      error.status === null
      || error.status === 408
      || error.status === 429
      || error.status >= 500
    );
  }

  return false;
}

function getApiBaseUrl(): string {
  const configuredUrl =
    process.env
      .NEXT_PUBLIC_API_URL
      ?.trim();

  if (!configuredUrl) {
    throw new Error(
      "NEXT_PUBLIC_API_URL não está configurada."
    );
  }

  return (
    `${configuredUrl.replace(/\/+$/, "")}/api`
  );
}

function errorDetailToMessage(
  detail: unknown,
  fallback: string,
): string {
  if (typeof detail === "string") {
    return detail;
  }

  if (
    detail
    && typeof detail === "object"
  ) {
    const objectDetail = detail as {
      message?: unknown;
      supported_niches?: unknown;
    };

    const message =
      typeof objectDetail.message
      === "string"
        ? objectDetail.message
        : fallback;

    if (
      Array.isArray(
        objectDetail.supported_niches
      )
    ) {
      const niches =
        objectDetail
          .supported_niches
          .map(String)
          .join(", ");

      return (
        `${message} `
        + `Nichos suportados: ${niches}.`
      );
    }

    try {
      return JSON.stringify(detail);
    } catch {
      return fallback;
    }
  }

  return fallback;
}

async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  timeoutMs = DEFAULT_TIMEOUT_MS,
): Promise<T> {
  const controller =
    new AbortController();

  const externalSignal =
    options.signal;

  const abortFromExternalSignal =
    () => {
      controller.abort();
    };

  if (externalSignal) {
    if (externalSignal.aborted) {
      controller.abort();
    } else {
      externalSignal.addEventListener(
        "abort",
        abortFromExternalSignal,
        {
          once: true,
        },
      );
    }
  }

  const timeoutId =
    globalThis.setTimeout(
      () => controller.abort(),
      timeoutMs,
    );

  const headers =
    new Headers(options.headers);

  if (
    options.body
    && !headers.has("Content-Type")
  ) {
    headers.set(
      "Content-Type",
      "application/json",
    );
  }

  try {
    const response = await fetch(
      `${getApiBaseUrl()}${path}`,
      {
        ...options,
        headers,
        signal: controller.signal,
        cache: "no-store",
      },
    );

    const responseText =
      await response.text();

    let responseBody: unknown =
      null;

    if (responseText) {
      try {
        responseBody =
          JSON.parse(responseText);
      } catch {
        responseBody =
          responseText;
      }
    }

    if (!response.ok) {
      const fallback =
        `Erro ${response.status}.`;

      let detail: unknown =
        responseBody;

      if (
        responseBody
        && typeof responseBody
        === "object"
        && "detail" in responseBody
      ) {
        detail = (
          responseBody as {
            detail?: unknown;
          }
        ).detail;
      }

      throw new ApiRequestError(
        errorDetailToMessage(
          detail,
          fallback,
        ),
        response.status,
      );
    }

    return responseBody as T;
  } catch (error) {
    if (controller.signal.aborted) {
      if (
        externalSignal?.aborted
      ) {
        throw new Error(
          "Requisição cancelada."
        );
      }

      throw new ApiRequestError(
        "O backend demorou demais para responder.",
        null,
      );
    }

    // Fetch signals network/CORS failures with TypeError. Classify them here,
    // so a TypeError elsewhere in the dashboard is never treated as retryable.
    if (error instanceof TypeError) {
      throw new ApiRequestError(
        "Não foi possível conectar ao backend. Verifique sua conexão e tente novamente.",
        null,
      );
    }

    throw error;
  } finally {
    globalThis.clearTimeout(
      timeoutId
    );

    externalSignal
      ?.removeEventListener(
        "abort",
        abortFromExternalSignal,
      );
  }
}

export const api = {
  health(
    signal?: AbortSignal,
  ) {
    return apiRequest<{
      status: string;
    }>(
      "/health",
      {
        signal,
      },
    );
  },

  createSearch(
    data: SearchCreate,
    signal?: AbortSignal,
  ) {
    return apiRequest<Search>(
      "/searches",
      {
        method: "POST",
        body: JSON.stringify(
          data
        ),
        signal,
      },
    );
  },

  listSearches(
    signal?: AbortSignal,
  ) {
    return apiRequest<Search[]>(
      "/searches",
      {
        signal,
      },
    );
  },

  getSearch(
    id: string,
    signal?: AbortSignal,
  ) {
    return apiRequest<SearchDetail>(
      `/searches/${
        encodeURIComponent(id)
      }`,
      {
        signal,
      },
    );
  },

  deleteSearch(
    id: string,
    signal?: AbortSignal,
  ) {
    return apiRequest<{
      ok: boolean;
    }>(
      `/searches/${
        encodeURIComponent(id)
      }`,
      {
        method: "DELETE",
        signal,
      },
    );
  },

  getLead(
    id: string,
    signal?: AbortSignal,
  ) {
    return apiRequest<Lead>(
      `/leads/${
        encodeURIComponent(id)
      }`,
      {
        signal,
      },
    );
  },

  generateMessage(
    id: string,
    channel: ContactChannel,
    signal?: AbortSignal,
  ) {
    const query =
      new URLSearchParams({
        channel,
      });

    return apiRequest<ContactMessage>(
      `/leads/${
        encodeURIComponent(id)
      }/message?${
        query.toString()
      }`,
      {
        signal,
      },
    );
  },
};
