import type { SupabaseClient } from "@supabase/supabase-js";
import type { CookieMethodsServer } from "@supabase/ssr";
import { beforeEach, describe, expect, it, vi } from "vitest";

const ssr = vi.hoisted(() => ({
  createBrowserClient: vi.fn(),
  createServerClient: vi.fn(),
}));

vi.mock("@supabase/ssr", () => ssr);

import {
  createAuthBrowserClient,
  createAuthCallbackProviderWithCookies,
  createSupabaseAuthProvider,
} from "./supabase";

const callbackUrl = "http://localhost:3000/auth/callback";
const callbackFlowId = "callback_flow_1234";
const storageKey = "sb-project-auth-token";

type ServerOptions = Readonly<{ cookies: CookieMethodsServer }>;

function serverClient(
  exchange: (cookies: CookieMethodsServer) => Promise<unknown>,
  getUser: (cookies: CookieMethodsServer) => Promise<unknown> = async () => ({
    data: { user: { id: "user-one" } },
    error: null,
  }),
) {
  return (_url: string, _key: string, options: ServerOptions) => ({
    auth: {
      exchangeCodeForSession: () => exchange(options.cookies),
      getSession: vi.fn(async () => ({ data: { session: null }, error: null })),
      getUser: () => getUser(options.cookies),
      refreshSession: vi.fn(),
      signOut: vi.fn(),
      signInWithOAuth: vi.fn(),
      onAuthStateChange: vi.fn(() => ({
        data: { subscription: { unsubscribe: vi.fn() } },
      })),
    },
  });
}

function stagedExchange(cookies: CookieMethodsServer) {
  cookies.setAll?.(
    [
      {
        name: `${storageKey}-flow-${callbackFlowId}-code-verifier`,
        value: "",
        options: { path: "/", maxAge: 0 },
      },
      {
        name: `${storageKey}-flows-code-verifier`,
        value: "opaque-updated-flow-index",
        options: { path: "/" },
      },
      {
        name: storageKey,
        value: "opaque-new-provider-session",
        options: { path: "/", sameSite: "lax" },
      },
      {
        name: `${storageKey}-code-verifier`,
        value: "",
        options: { path: "/", maxAge: 0 },
      },
    ],
    { "Cache-Control": "private, no-store" },
  );
  return Promise.resolve({
    data: {
      session: { user: { id: "user-one" }, access_token: "provider-access", expires_at: 1 },
    },
    error: null,
  });
}

function clientWithAuth() {
  const auth = {
    signInWithOAuth: vi.fn(),
    exchangeCodeForSession: vi.fn(),
  };
  return { auth, client: { auth } as unknown as SupabaseClient };
}

describe("Supabase Auth client configuration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://project.supabase.co");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "publishable-key");
    ssr.createBrowserClient.mockReturnValue({});
  });

  it("configures the initiating browser client to propagate PKCE flow IDs", () => {
    createAuthBrowserClient("http://localhost:3000");

    expect(ssr.createBrowserClient).toHaveBeenCalledWith(
      "https://project.supabase.co",
      "publishable-key",
      expect.objectContaining({
        auth: {
          persistSession: true,
          flowType: "pkce",
          detectSessionInUrl: false,
          experimental: { appendPkceFlowIdToRedirects: true },
        },
      }),
    );
  });
});

describe("deferred Supabase callback cookie commit", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://project.supabase.co");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "publishable-key");
  });

  it("commits the installed SDK session and PKCE mutations once after preparation", async () => {
    ssr.createServerClient.mockImplementation(serverClient(stagedExchange));
    const applied = vi.fn();
    const provider = await createAuthCallbackProviderWithCookies("http://localhost:3000", {
      getAll: () => [
        { name: storageKey, value: "opaque-original-provider-session" },
        {
          name: `${storageKey}-flow-${callbackFlowId}-code-verifier`,
          value: "opaque-verifier-slot",
        },
      ],
      setAll: applied,
    });

    const exchange = await provider.exchangeCode("authorization-code", callbackFlowId);
    expect(applied).not.toHaveBeenCalled();
    await exchange.prepareSessionCommit();
    expect(applied).not.toHaveBeenCalled();
    await exchange.commitSession();

    expect(applied).toHaveBeenCalledTimes(1);
    expect(applied.mock.calls[0][0]).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ name: storageKey, value: "opaque-new-provider-session" }),
        expect.objectContaining({
          name: `${storageKey}-flow-${callbackFlowId}-code-verifier`,
          value: "",
        }),
        expect.objectContaining({ name: `${storageKey}-flows-code-verifier` }),
        expect.objectContaining({ name: `${storageKey}-code-verifier`, value: "" }),
      ]),
    );
    await expect(exchange.commitSession()).rejects.toThrow("not prepared");
  });

  it("discards session installation while preserving exact PKCE cleanup", async () => {
    ssr.createServerClient.mockImplementation(serverClient(stagedExchange));
    const applied = vi.fn();
    const originalCookies = [
      { name: storageKey, value: "opaque-original-provider-session" },
      {
        name: `${storageKey}-flow-${callbackFlowId}-code-verifier`,
        value: "opaque-verifier-slot",
      },
    ];
    const provider = await createAuthCallbackProviderWithCookies("http://localhost:3000", {
      getAll: () => originalCookies,
      setAll: applied,
    });

    const exchange = await provider.exchangeCode("authorization-code", callbackFlowId);
    await exchange.prepareSessionCommit();
    await exchange.discardSession();

    expect(applied).toHaveBeenCalledTimes(1);
    const mutations = applied.mock.calls[0][0] as Array<{ name: string; value: string }>;
    expect(mutations.map(({ name }) => name)).toEqual([
      `${storageKey}-flow-${callbackFlowId}-code-verifier`,
      `${storageKey}-flows-code-verifier`,
      `${storageKey}-code-verifier`,
    ]);
    expect(mutations).not.toEqual(
      expect.arrayContaining([expect.objectContaining({ name: storageKey })]),
    );
    expect(originalCookies[0].value).toBe("opaque-original-provider-session");
  });

  it("applies failed-exchange verifier cleanup without installing a session", async () => {
    ssr.createServerClient.mockImplementation(
      serverClient(async (cookies) => {
        await cookies.setAll?.(
          [
            {
              name: `${storageKey}-flow-${callbackFlowId}-code-verifier`,
              value: "",
              options: { path: "/", maxAge: 0 },
            },
            {
              name: `${storageKey}-flows-code-verifier`,
              value: "",
              options: { path: "/", maxAge: 0 },
            },
          ],
          {},
        );
        return { data: { session: null }, error: { name: "AuthPKCEError" } };
      }),
    );
    const applied = vi.fn();
    const provider = await createAuthCallbackProviderWithCookies("http://localhost:3000", {
      getAll: () => [],
      setAll: applied,
    });

    await expect(
      provider.exchangeCode("authorization-code", callbackFlowId),
    ).rejects.toMatchObject({ code: "PKCE_VALIDATION_FAILED" });
    expect(applied).toHaveBeenCalledTimes(1);
    expect(JSON.stringify(applied.mock.calls[0][0])).not.toContain(
      "opaque-new-provider-session",
    );
  });

  it("isolates original-cookie live validation from the exchanged client", async () => {
    ssr.createServerClient
      .mockImplementationOnce(serverClient(stagedExchange))
      .mockImplementationOnce(
        serverClient(async () => ({ data: { session: null }, error: null })),
      );
    const applied = vi.fn();
    const provider = await createAuthCallbackProviderWithCookies("http://localhost:3000", {
      getAll: () => [{ name: storageKey, value: "opaque-original-provider-session" }],
      setAll: applied,
    });
    const exchange = await provider.exchangeCode("authorization-code", callbackFlowId);
    await exchange.discardSession();

    await expect(
      provider.validatePreExistingSession({
        userReference: "user-one",
        accessToken: "not-used-for-validation",
        expiresAt: 1,
      }),
    ).resolves.toEqual({ userReference: "user-one" });
    expect(ssr.createServerClient).toHaveBeenCalledTimes(2);
  });

  it("fails preserved-session validation closed on mismatch or validation mutation", async () => {
    ssr.createServerClient
      .mockImplementationOnce(serverClient(stagedExchange))
      .mockImplementationOnce(
        serverClient(async () => ({ data: { session: null }, error: null }), async (cookies) => {
          await cookies.setAll?.(
            [{ name: storageKey, value: "opaque-refresh", options: { path: "/" } }],
            {},
          );
          return { data: { user: { id: "user-two" } }, error: null };
        }),
      );
    const provider = await createAuthCallbackProviderWithCookies("http://localhost:3000", {
      getAll: () => [{ name: storageKey, value: "opaque-original-provider-session" }],
      setAll: vi.fn(),
    });

    await expect(
      provider.validatePreExistingSession({
        userReference: "user-one",
        accessToken: "not-used-for-validation",
        expiresAt: 1,
      }),
    ).resolves.toBeNull();
  });

  it("closes each journal with its request and rejects unrelated cookie mutations", async () => {
    ssr.createServerClient.mockImplementation(
      serverClient(async (cookies) => {
        await cookies.setAll?.(
          [{ name: "unrelated-cookie", value: "", options: { maxAge: 0 } }],
          {},
        );
        return {
          data: {
            session: { user: { id: "user-one" }, access_token: "provider-access" },
          },
          error: null,
        };
      }),
    );
    const provider = await createAuthCallbackProviderWithCookies("http://localhost:3000", {
      getAll: () => [],
      setAll: vi.fn(),
    });
    const exchange = await provider.exchangeCode("authorization-code", callbackFlowId);

    await expect(exchange.prepareSessionCommit()).rejects.toThrow(
      "Invalid provider cookie mutation",
    );
  });
});

describe("real Supabase provider boundary", () => {
  it("uses data.flowId directly without parsing redirect_to or adding return state", async () => {
    const { auth, client } = clientWithAuth();
    auth.signInWithOAuth.mockResolvedValue({
      data: {
        url: "https://project.supabase.co/auth/v1/authorize?redirect_to=not-a-url",
        flowId: "direct_flow_1234",
      },
      error: null,
    });

    await expect(createSupabaseAuthProvider(client).beginGitHubOAuth(callbackUrl)).resolves.toEqual({
      redirectUrl: "https://project.supabase.co/auth/v1/authorize?redirect_to=not-a-url",
      flowId: "direct_flow_1234",
    });
    expect(auth.signInWithOAuth).toHaveBeenCalledWith({
      provider: "github",
      options: { redirectTo: callbackUrl, skipBrowserRedirect: true },
    });
    expect(JSON.stringify(auth.signInWithOAuth.mock.calls[0][0])).not.toMatch(/state|intended|return/);
  });

  it("fails closed when data.flowId is missing even if data.url contains one", async () => {
    const { auth, client } = clientWithAuth();
    auth.signInWithOAuth.mockResolvedValue({
      data: {
        url: `https://project.supabase.co/auth/v1/authorize?redirect_to=${encodeURIComponent(`${callbackUrl}?sb_flow_id=url_flow_1234`)}`,
      },
      error: null,
    });

    await expect(
      createSupabaseAuthProvider(client).beginGitHubOAuth(callbackUrl),
    ).rejects.toMatchObject({ code: "CONFIGURATION_UNAVAILABLE" });
  });

  it("preserves independent flow IDs through exact code exchanges", async () => {
    const { auth, client } = clientWithAuth();
    auth.signInWithOAuth
      .mockResolvedValueOnce({
        data: { url: "https://provider.example/one", flowId: "first_flow_1234" },
        error: null,
      })
      .mockResolvedValueOnce({
        data: { url: "https://provider.example/two", flowId: "second_flow_123" },
        error: null,
      });
    auth.exchangeCodeForSession
      .mockResolvedValueOnce({
        data: {
          session: { user: { id: "user-one" }, access_token: "token-one", expires_at: 1 },
        },
        error: null,
      })
      .mockResolvedValueOnce({
        data: {
          session: { user: { id: "user-two" }, access_token: "token-two", expires_at: 2 },
        },
        error: null,
      });
    const callbackBoundary = {
      begin: vi.fn(),
      prepare: vi.fn(async () => undefined),
      commit: vi.fn(async () => undefined),
      discard: vi.fn(async () => undefined),
      validateOriginalSession: vi.fn(async () => null),
    };
    const provider = createSupabaseAuthProvider(client, callbackBoundary);

    const first = await provider.beginGitHubOAuth(callbackUrl);
    const second = await provider.beginGitHubOAuth(callbackUrl);
    await provider.exchangeCode("code-one", first.flowId);
    await provider.exchangeCode("code-two", second.flowId);

    expect(first.flowId).toBe("first_flow_1234");
    expect(second.flowId).toBe("second_flow_123");
    expect(auth.exchangeCodeForSession.mock.calls).toEqual([
      ["code-one", { flowId: "first_flow_1234" }],
      ["code-two", { flowId: "second_flow_123" }],
    ]);
  });
});
