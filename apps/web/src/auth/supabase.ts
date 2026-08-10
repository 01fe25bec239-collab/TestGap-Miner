import {
  createBrowserClient,
  createServerClient,
  type CookieMethodsServer,
  type CookieOptions,
} from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";
import type {
  AuthProvider,
  ProviderCodeExchange,
  ProviderSession,
  ProviderSessionEvent,
} from "./types";
import { AuthRuntimeError } from "./types";

function readPublicConfiguration() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const publishableKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  if (!url || !publishableKey) {
    throw new AuthRuntimeError("CONFIGURATION_UNAVAILABLE", true);
  }
  return { url, publishableKey };
}

function providerCookieOptions(origin: string) {
  return {
    path: "/",
    sameSite: "lax" as const,
    secure: origin !== "http://localhost:3000",
    httpOnly: false,
  };
}

type WritableCookieMethods = CookieMethodsServer &
  Required<Pick<CookieMethodsServer, "setAll">>;

type CookieMutation = Readonly<{
  name: string;
  value: string;
  options: CookieOptions;
}>;

type CookieMutationBatch = Readonly<{
  cookies: readonly CookieMutation[];
  headers: Readonly<Record<string, string>>;
}>;

class ProviderCookieMutationJournal {
  readonly cookieAccess: WritableCookieMethods;
  #flowId: string | null = null;
  #prepared = false;
  #settled = false;
  #batches: CookieMutationBatch[] = [];

  constructor(
    incomingCookies: readonly Readonly<{ name: string; value: string }>[],
    private readonly storageKey: string,
    private readonly applyCookies: NonNullable<CookieMethodsServer["setAll"]>,
  ) {
    const snapshot = incomingCookies.map(({ name, value }) => ({ name, value }));
    this.cookieAccess = {
      getAll: () => snapshot.map(({ name, value }) => ({ name, value })),
      setAll: (cookies, headers) => {
        if (this.#settled) throw new Error("Provider cookie journal is closed");
        this.#batches.push({
          cookies: cookies.map(({ name, value, options }) => ({
            name,
            value,
            options: { ...options },
          })),
          headers: { ...headers },
        });
      },
    };
  }

  begin(flowId: string) {
    if (this.#flowId || this.#settled) throw new Error("Provider cookie journal already used");
    this.#flowId = flowId;
  }

  async prepare() {
    this.#validate();
    this.#prepared = true;
  }

  async commit() {
    if (!this.#prepared || this.#settled) throw new Error("Provider cookie commit not prepared");
    await this.#apply(this.#batches);
    this.#close();
  }

  async discard() {
    if (this.#settled) return;
    this.#validate();
    await this.#apply(
      this.#batches
        .map(({ cookies, headers }) => ({
          cookies: cookies.filter(({ name }) => this.#isPkceCookie(name)),
          headers,
        }))
        .filter(({ cookies }) => cookies.length > 0),
    );
    this.#close();
  }

  #validate() {
    if (!this.#flowId) throw new Error("Provider cookie journal has no callback flow");
    if (typeof this.applyCookies !== "function") {
      throw new Error("Provider cookie response commit is unavailable");
    }
    for (const { cookies, headers } of this.#batches) {
      for (const { name, value, options } of cookies) {
        if (
          typeof name !== "string" ||
          typeof value !== "string" ||
          !name ||
          /[\r\n]/.test(name) ||
          /[\r\n]/.test(value) ||
          !options ||
          typeof options !== "object" ||
          !Object.values(options).every(
            (option) =>
              option === undefined ||
              typeof option === "string" ||
              typeof option === "number" ||
              typeof option === "boolean" ||
              option instanceof Date,
          ) ||
          (!this.#isSessionCookie(name) && !this.#isPkceCookie(name))
        ) {
          throw new Error("Invalid provider cookie mutation");
        }
      }
      for (const [name, value] of Object.entries(headers)) {
        if (!name || /[\r\n]/.test(name) || /[\r\n]/.test(value)) {
          throw new Error("Invalid provider response metadata");
        }
      }
    }
  }

  #isSessionCookie(name: string) {
    return isCookieChunk(name, this.storageKey);
  }

  #isPkceCookie(name: string) {
    return (
      isCookieChunk(name, `${this.storageKey}-code-verifier`) ||
      isCookieChunk(name, `${this.storageKey}-flows-code-verifier`) ||
      isCookieChunk(name, `${this.storageKey}-flow-${this.#flowId}-code-verifier`)
    );
  }

  async #apply(batches: readonly CookieMutationBatch[]) {
    if (!batches.length) return;
    await this.applyCookies(
      batches.flatMap(({ cookies }) =>
        cookies.map(({ name, value, options }) => ({ name, value, options: { ...options } })),
      ),
      Object.assign({}, ...batches.map(({ headers }) => headers)),
    );
  }

  #close() {
    this.#batches = [];
    this.#settled = true;
  }
}

function isCookieChunk(name: string, storageItem: string) {
  return name === storageItem || new RegExp(`^${escapeRegExp(storageItem)}\\.\\d+$`).test(name);
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function defaultProviderStorageKey(url: string) {
  return `sb-${new URL(url).hostname.split(".")[0]}-auth-token`;
}

type DeferredCallbackBoundary = Readonly<{
  begin(flowId: string): void;
  prepare(): Promise<void>;
  commit(): Promise<void>;
  discard(): Promise<void>;
  validateOriginalSession(
    session: ProviderSession,
  ): Promise<{ userReference: string } | null>;
}>;

export function createAuthBrowserClient(origin = globalThis.location?.origin ?? "") {
  const { url, publishableKey } = readPublicConfiguration();
  return createBrowserClient(url, publishableKey, {
    cookieOptions: providerCookieOptions(origin),
    auth: {
      persistSession: true,
      flowType: "pkce",
      detectSessionInUrl: false,
      experimental: { appendPkceFlowIdToRedirects: true },
    },
  });
}

export function createAuthServerClientWithCookies(
  origin: string,
  cookieAccess: CookieMethodsServer,
) {
  const { url, publishableKey } = readPublicConfiguration();
  return createServerClient(url, publishableKey, {
    cookieOptions: providerCookieOptions(origin),
    cookies: {
      getAll: cookieAccess.getAll,
      setAll: cookieAccess.setAll,
    },
    auth: {
      persistSession: true,
      flowType: "pkce",
      detectSessionInUrl: false,
    },
  });
}

export async function createAuthCallbackProviderWithCookies(
  origin: string,
  cookieAccess: WritableCookieMethods,
): Promise<AuthProvider> {
  const { url } = readPublicConfiguration();
  const incomingCookies = ((await cookieAccess.getAll()) ?? []).map(({ name, value }) => ({
    name,
    value,
  }));
  const journal = new ProviderCookieMutationJournal(
    incomingCookies,
    defaultProviderStorageKey(url),
    cookieAccess.setAll,
  );
  const client = createAuthServerClientWithCookies(origin, journal.cookieAccess);
  const validateOriginalSession = async (session: ProviderSession) => {
    let mutated = false;
    const validationClient = createAuthServerClientWithCookies(origin, {
      getAll: () => incomingCookies.map(({ name, value }) => ({ name, value })),
      setAll: () => {
        mutated = true;
      },
    });
    const { data, error } = await validationClient.auth.getUser();
    return !error && !mutated && data.user?.id === session.userReference
      ? { userReference: data.user.id }
      : null;
  };
  return createSupabaseAuthProvider(client, {
    begin: (flowId) => journal.begin(flowId),
    prepare: () => journal.prepare(),
    commit: () => journal.commit(),
    discard: () => journal.discard(),
    validateOriginalSession,
  });
}

function toProviderSession(session: {
  user: { id: string };
  access_token: string;
  expires_at?: number;
}): ProviderSession {
  return {
    userReference: session.user.id,
    accessToken: session.access_token,
    expiresAt: (session.expires_at ?? 0) * 1_000,
  };
}

export function createSupabaseAuthProvider(
  client: SupabaseClient,
  callbackBoundary?: DeferredCallbackBoundary,
): AuthProvider {
  return {
    async beginGitHubOAuth(callbackUrl) {
      const { data, error } = await client.auth.signInWithOAuth({
        provider: "github",
        options: { redirectTo: callbackUrl, skipBrowserRedirect: true },
      });
      if (error || !data.url) throw new AuthRuntimeError("TEMPORARY_PROVIDER_FAILURE", true);

      const flowId = data.flowId;
      if (!flowId || !/^[A-Za-z0-9_-]{8,64}$/.test(flowId)) {
        throw new AuthRuntimeError("CONFIGURATION_UNAVAILABLE", true);
      }
      return { redirectUrl: data.url, flowId };
    },

    async exchangeCode(code, flowId) {
      if (!callbackBoundary) {
        throw new AuthRuntimeError("CONFIGURATION_UNAVAILABLE", true);
      }
      callbackBoundary.begin(flowId);
      const { data, error } = await client.auth.exchangeCodeForSession(code, { flowId });
      if (error || !data.session) {
        await callbackBoundary.discard();
        const name = error?.name ?? "";
        throw new AuthRuntimeError(
          name.includes("PKCE") ? "PKCE_VALIDATION_FAILED" : "SESSION_EXCHANGE_FAILED",
        );
      }
      return {
        session: toProviderSession(data.session),
        prepareSessionCommit: () => callbackBoundary.prepare(),
        commitSession: () => callbackBoundary.commit(),
        discardSession: () => callbackBoundary.discard(),
      } satisfies ProviderCodeExchange;
    },

    async getSession() {
      const { data, error } = await client.auth.getSession();
      if (error) throw new AuthRuntimeError("TEMPORARY_PROVIDER_FAILURE", true);
      return data.session ? toProviderSession(data.session) : null;
    },

    async validateCurrentUser() {
      const { data, error } = await client.auth.getUser();
      return error || !data.user ? null : { userReference: data.user.id };
    },

    async validatePreExistingSession(session) {
      if (callbackBoundary) return callbackBoundary.validateOriginalSession(session);
      const { data, error } = await client.auth.getUser();
      return !error && data.user?.id === session.userReference
        ? { userReference: data.user.id }
        : null;
    },

    async refresh() {
      const { data, error } = await client.auth.refreshSession();
      if (error || !data.session) {
        throw new AuthRuntimeError(
          "REFRESH_FAILED",
          Boolean(error?.status && error.status >= 500),
        );
      }
      return toProviderSession(data.session);
    },

    async signOutLocal() {
      const { error } = await client.auth.signOut({ scope: "local" });
      if (error) throw new AuthRuntimeError("SIGN_OUT_FAILED", true);
    },

    onSessionChange(listener) {
      const { data } = client.auth.onAuthStateChange((event, session) => {
        if (
          event === "INITIAL_SESSION" ||
          event === "SIGNED_IN" ||
          event === "SIGNED_OUT" ||
          event === "TOKEN_REFRESHED" ||
          event === "USER_UPDATED"
        ) {
          listener(event satisfies ProviderSessionEvent, session ? toProviderSession(session) : null);
        }
      });
      return () => data.subscription.unsubscribe();
    },
  };
}
