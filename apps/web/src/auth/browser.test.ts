import { describe, expect, it, vi } from "vitest";
import {
  createAuthBrowserSessionFenceBridge,
  createBrowserAuthAdapter,
  type AuthBrowserSessionFenceBridge,
} from "./browser";
import {
  LocalCorrelationStore,
  type CorrelationCookie,
  type CorrelationStore,
} from "./correlation";
import {
  AuthSessionFenceHostService,
  BrowserLocalSignOutTombstone,
  executeAuthSessionFenceHostRequest,
  type AuthFenceResolution,
  type AuthSessionFence,
} from "./session-fence";
import type {
  AuthProvider,
  ProviderSession,
  ProviderSessionEvent,
} from "./types";

const origin = "http://localhost:3000";
const redirectUrl = "https://provider.example/authorize?state=provider-state";
const attemptReference = "server-sign-in-attempt-reference";
const policyVersion = "test-auth-policy@1.0";

class RecordingProvider implements AuthProvider {
  session: ProviderSession | null = null;
  beginCalls = 0;
  refreshCalls = 0;
  signOutCalls = 0;
  failBegin = false;
  failRefresh = false;
  failSignOut = false;
  #listeners = new Set<
    (event: ProviderSessionEvent, session: ProviderSession | null) => void
  >();

  async beginGitHubOAuth() {
    this.beginCalls += 1;
    if (this.failBegin) throw new Error("provider begin failed");
    return { redirectUrl, flowId: "flow_12345678" };
  }

  async exchangeCode(): Promise<never> {
    throw new Error("Browser composition does not process callbacks");
  }

  async getSession() {
    return this.session;
  }

  async validateCurrentUser() {
    return this.session ? { userReference: this.session.userReference } : null;
  }

  async validatePreExistingSession(session: ProviderSession) {
    return this.session?.userReference === session.userReference
      ? { userReference: session.userReference }
      : null;
  }

  async refresh() {
    this.refreshCalls += 1;
    if (this.failRefresh) throw new Error("provider refresh failed");
    this.session = currentSession("refreshed-access-token");
    return this.session;
  }

  async signOutLocal() {
    this.signOutCalls += 1;
    if (this.failSignOut) throw new Error("provider sign-out failed");
    this.session = null;
  }

  onSessionChange(
    listener: (event: ProviderSessionEvent, session: ProviderSession | null) => void,
  ) {
    this.#listeners.add(listener);
    return () => this.#listeners.delete(listener);
  }

  emit(event: ProviderSessionEvent, session: ProviderSession | null) {
    this.session = session;
    for (const listener of this.#listeners) listener(event, session);
  }
}

class RecordingFence implements AuthSessionFence {
  prepareCalls = 0;
  associateCalls = 0;
  abandonCalls = 0;
  tombstoneCalls = 0;
  publishCalls = 0;
  failAt: "prepare" | "associate" | "publish" | null = null;
  resolution: AuthFenceResolution = {
    eligible: false,
    reason: "UNVERIFIED",
  };

  async prepareSignIn() {
    this.prepareCalls += 1;
    if (this.failAt === "prepare") throw new Error("fence prepare failed");
    return { signInAttemptReference: attemptReference };
  }

  async associateSignInAttempt() {
    this.associateCalls += 1;
    if (this.failAt === "associate") throw new Error("association failed");
    return {
      signInAttemptReference: attemptReference,
      callbackFlowReference: "server-callback-reference",
      correlationReference: "server-correlation-reference",
    };
  }

  async abandonSignInAttempt() {
    this.abandonCalls += 1;
  }

  async abandonCallback() {}
  async validateCallback() {
    return this.resolution;
  }
  async establishSession() {
    return this.resolution;
  }
  async rollbackSessionEstablishment() {}
  async resolveFence() {
    return this.resolution;
  }
  createLocalSignOutTombstone() {
    this.tombstoneCalls += 1;
  }
  async publishSignOut() {
    this.publishCalls += 1;
    if (this.failAt === "publish") throw new Error("publish failed");
  }
  async cleanupStaleSessionMaterial() {}
  subscribeToFenceChanges() {
    return () => {};
  }
}

class RecordingStore implements CorrelationStore {
  readonly inner = new LocalCorrelationStore();
  createCalls = 0;
  removeCalls = 0;
  failCreate = false;

  async createPending(input: Parameters<CorrelationStore["createPending"]>[0]) {
    this.createCalls += 1;
    if (this.failCreate) throw new Error("correlation create failed");
    return this.inner.createPending(input);
  }
  lookup(...input: Parameters<CorrelationStore["lookup"]>) {
    return this.inner.lookup(...input);
  }
  complete(...input: Parameters<CorrelationStore["complete"]>) {
    return this.inner.complete(...input);
  }
  async remove(handle: string) {
    this.removeCalls += 1;
    await this.inner.remove(handle);
  }
  cleanup(now: number) {
    return this.inner.cleanup(now);
  }
}

class CookieDocument {
  #value = "";
  constructor(private readonly onWrite?: () => void) {}
  get cookie() {
    return this.#value;
  }
  set cookie(value: string) {
    this.onWrite?.();
    this.#value = value.includes("Max-Age=0") ? "" : value.split(";", 1)[0];
  }
}

function currentSession(accessToken = "browser-access-token"): ProviderSession {
  return {
    userReference: "user-1",
    accessToken,
    expiresAt: Date.now() + 300_000,
  };
}

function createServerHarness(
  failAt: "prepare" | "provider" | "correlation" | "associate" | "cookie" | null = null,
) {
  const provider = new RecordingProvider();
  provider.failBegin = failAt === "provider";
  const fence = new RecordingFence();
  fence.failAt = failAt === "prepare" || failAt === "associate" ? failAt : null;
  const store = new RecordingStore();
  store.failCreate = failAt === "correlation";
  const cookies: CorrelationCookie[] = [];
  let cookieWrites = 0;
  let cookieDeletes = 0;
  const host = new AuthSessionFenceHostService({
    provider,
    sessionFence: fence,
    correlationStore: store,
    securityPolicyVersion: policyVersion,
    applicationOrigin: origin,
    setCorrelationCookie: (cookie) => {
      cookieWrites += 1;
      if (failAt === "cookie") throw new Error("cookie write failed");
      cookies.push(cookie);
    },
    deleteCorrelationCookie: () => {
      cookieDeletes += 1;
    },
    now: () => 1_000,
  });
  return {
    provider,
    fence,
    store,
    cookies,
    host,
    cookieWrites: () => cookieWrites,
    cookieDeletes: () => cookieDeletes,
  };
}

function createBrowserHarness(
  sessionFence: AuthBrowserSessionFenceBridge,
  options: {
    order?: string[];
    failProviderSignOut?: boolean;
    cookieDocument?: CookieDocument;
  } = {},
) {
  const provider = new RecordingProvider();
  provider.failSignOut = options.failProviderSignOut ?? false;
  const cookieDocument =
    options.cookieDocument ??
    new CookieDocument(() => options.order?.push("tombstone"));
  const tombstone = new BrowserLocalSignOutTombstone(origin, cookieDocument);
  const navigations: string[] = [];
  const adapter = createBrowserAuthAdapter({
    provider,
    sessionFence,
    tombstone,
    navigateToProvider: (url) => {
      navigations.push(url);
    },
  });
  provider.emit("SIGNED_OUT", null);
  return { adapter, provider, tombstone, navigations };
}

function staticBridge(
  resolved: { state: "AUTHENTICATED"; userReference: string } | {
    state: "UNAUTHENTICATED";
    userReference: null;
  } = { state: "UNAUTHENTICATED", userReference: null },
) {
  let resolution = resolved;
  let prepareCalls = 0;
  let publishCalls = 0;
  let resolveCalls = 0;
  let failPublish = false;
  return {
    bridge: {
      async prepareSignIn() {
        prepareCalls += 1;
        return { redirectUrl };
      },
      async publishSignOut() {
        publishCalls += 1;
        if (failPublish) throw new Error("bridge publish failed");
      },
      async resolveSession() {
        resolveCalls += 1;
        return resolution;
      },
    } satisfies AuthBrowserSessionFenceBridge,
    setResolution(value: typeof resolution) {
      resolution = value;
    },
    setFailPublish(value: boolean) {
      failPublish = value;
    },
    counts: () => ({ prepareCalls, publishCalls, resolveCalls }),
  };
}

describe("Auth browser/session-fence composition", () => {
  it("performs one server-owned sign-in sequence and returns only a transient redirect", async () => {
    const server = createServerHarness();
    const requests: unknown[] = [];
    const responses: string[] = [];
    const fetchCalls: RequestInit[] = [];
    const fetch = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      fetchCalls.push(init ?? {});
      const request = JSON.parse(String(init?.body));
      requests.push(request);
      const response = await executeAuthSessionFenceHostRequest(server.host, request);
      const serialized = JSON.stringify(response);
      responses.push(serialized);
      return new Response(serialized, {
        status: 200,
        headers: { "content-type": "application/json", "cache-control": "no-store" },
      });
    }) as typeof globalThis.fetch;
    const bridge = createAuthBrowserSessionFenceBridge({
      csrfToken: () => "approved-csrf-token",
      fetch,
    });
    const browser = createBrowserHarness(bridge);

    await browser.adapter.beginSignIn("/runs?view=mine");

    expect(requests).toEqual([
      { operation: "PREPARE_SIGN_IN", intendedReturn: "/runs?view=mine" },
    ]);
    expect(server.fence.prepareCalls).toBe(1);
    expect(server.provider.beginCalls).toBe(1);
    expect(server.store.createCalls).toBe(1);
    expect(server.fence.associateCalls).toBe(1);
    expect(server.cookieWrites()).toBe(1);
    expect(browser.navigations).toEqual([redirectUrl]);
    expect(browser.provider.beginCalls).toBe(0);
    expect(Object.values(browser.adapter)).not.toContain(server.fence);
    expect(browser.adapter.getSessionSnapshot()).toMatchObject({
      state: "SIGN_IN_PENDING",
      canRenderProtectedContent: false,
      canMakeApiRequest: false,
    });
    expect(responses).toEqual([JSON.stringify({ redirectUrl })]);
    expect(Object.keys(JSON.parse(responses[0]))).toEqual(["redirectUrl"]);
    expect(responses[0]).not.toContain(attemptReference);
    expect(responses[0]).not.toMatch(
      /callbackFlowReference|correlationReference|AuthFenceEventReferences|contextHandle|bindingHandle|generation|accessToken|refreshToken|providerSession|authorizationCode|pkce|verifier/i,
    );
    expect(fetchCalls[0]).toMatchObject({
      method: "POST",
      mode: "same-origin",
      credentials: "same-origin",
      cache: "no-store",
    });
    expect(new Headers(fetchCalls[0].headers).get("x-auth-csrf")).toBe(
      "approved-csrf-token",
    );
    const pending = await server.store.lookup(
      server.cookies[0].value,
      "flow_12345678",
      1_001,
    );
    expect(pending).toMatchObject({ intendedReturn: "/runs?view=mine" });
  });

  it.each([
    ["prepare", 0, 0, 0, 0, 0],
    ["provider", 1, 0, 0, 0, 1],
    ["correlation", 1, 1, 0, 0, 1],
    ["associate", 1, 1, 1, 0, 1],
    ["cookie", 1, 1, 1, 1, 1],
  ] as const)(
    "rolls back a %s begin-sign-in failure without a parallel attempt",
    async (failure, providerCalls, correlationCalls, associationCalls, cookieWrites, abandons) => {
      const server = createServerHarness(failure);
      const bridge = createAuthBrowserSessionFenceBridge({
        csrfToken: () => "approved-csrf-token",
        fetch: vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
          try {
            const response = await executeAuthSessionFenceHostRequest(
              server.host,
              JSON.parse(String(init?.body)),
            );
            return Response.json(response);
          } catch {
            return Response.json({ error: "SIGN_IN_FAILED" }, { status: 503 });
          }
        }) as typeof globalThis.fetch,
      });
      const browser = createBrowserHarness(bridge);
      await expect(browser.adapter.beginSignIn("/runs")).rejects.toMatchObject({
        code: "TEMPORARY_PROVIDER_FAILURE",
      });
      expect(server.fence.prepareCalls).toBe(1);
      expect(server.provider.beginCalls).toBe(providerCalls);
      expect(server.store.createCalls).toBe(correlationCalls);
      expect(server.fence.associateCalls).toBe(associationCalls);
      expect(server.cookieWrites()).toBe(cookieWrites);
      expect(server.fence.abandonCalls).toBe(abandons);
      expect(server.store.removeCalls).toBe(correlationCalls ? 1 : 0);
      expect(server.cookieDeletes()).toBe(correlationCalls ? 1 : 0);
      expect(server.cookies).toEqual([]);
      expect(browser.provider.beginCalls).toBe(0);
      expect(browser.navigations).toEqual([]);
      expect(browser.adapter.getSessionSnapshot()).toMatchObject({
        state: "RECOVERABLE_ERROR",
        canRenderProtectedContent: false,
        canMakeApiRequest: false,
      });
    },
  );

  it("fails a bridge transport error into Auth-owned recoverable state", async () => {
    const server = createServerHarness();
    let transportCalls = 0;
    const bridge = createAuthBrowserSessionFenceBridge({
      csrfToken: () => "approved-csrf-token",
      fetch: vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
        transportCalls += 1;
        await executeAuthSessionFenceHostRequest(
          server.host,
          JSON.parse(String(init?.body)),
        );
        throw new Error("response lost");
      }) as typeof globalThis.fetch,
    });
    const browser = createBrowserHarness(bridge);

    await expect(browser.adapter.beginSignIn()).rejects.toMatchObject({
      code: "TEMPORARY_PROVIDER_FAILURE",
    });
    expect(transportCalls).toBe(1);
    expect(server.fence.prepareCalls).toBe(1);
    expect(server.provider.beginCalls).toBe(1);
    expect(server.store.createCalls).toBe(1);
    expect(server.fence.associateCalls).toBe(1);
    expect(server.cookieWrites()).toBe(1);
    expect(browser.provider.beginCalls).toBe(0);
    expect(browser.navigations).toEqual([]);
    expect(browser.adapter.getSessionSnapshot()).toMatchObject({
      state: "RECOVERABLE_ERROR",
      canRenderProtectedContent: false,
      canMakeApiRequest: false,
    });
  });

  it("rejects host/request payload extensions and browser response references", async () => {
    const server = createServerHarness();
    await expect(
      executeAuthSessionFenceHostRequest(server.host, {
        operation: "PREPARE_SIGN_IN",
        signInAttemptReference: "browser-controlled",
      }),
    ).rejects.toThrow("Invalid Auth session-fence request");

    const bridge = createAuthBrowserSessionFenceBridge({
      csrfToken: () => "approved-csrf-token",
      fetch: vi.fn(async () =>
        Response.json({ redirectUrl, signInAttemptReference: attemptReference }),
      ) as typeof globalThis.fetch,
    });
    await expect(bridge.prepareSignIn()).rejects.toThrow(
      "Invalid PREPARE_SIGN_IN response",
    );
  });

  it.each(["SIGNED_IN", "TOKEN_REFRESHED"] as const)(
    "keeps provider %s provisional until RESOLVE_SESSION",
    async (event) => {
      const transport = staticBridge();
      const browser = createBrowserHarness(transport.bridge);
      browser.provider.emit(event, currentSession());
      await vi.waitFor(() =>
        expect(browser.adapter.getSessionSnapshot().state).toBe("UNAUTHENTICATED"),
      );
      expect(browser.adapter.getSessionSnapshot().canRenderProtectedContent).toBe(false);
      expect(transport.counts().resolveCalls).toBe(1);

      transport.setResolution({ state: "AUTHENTICATED", userReference: "user-1" });
      browser.provider.emit(event, currentSession());
      await vi.waitFor(() =>
        expect(browser.adapter.getSessionSnapshot().state).toBe("AUTHENTICATED"),
      );
      expect(browser.adapter.getSessionSnapshot().canRenderProtectedContent).toBe(true);
    },
  );

  it("requires RESOLVE_SESSION for access tokens and refresh restoration", async () => {
    const transport = staticBridge({ state: "AUTHENTICATED", userReference: "user-1" });
    const browser = createBrowserHarness(transport.bridge);
    browser.provider.emit("INITIAL_SESSION", currentSession());
    await vi.waitFor(() =>
      expect(browser.adapter.getSessionSnapshot().state).toBe("AUTHENTICATED"),
    );

    const beforeToken = transport.counts().resolveCalls;
    await expect(browser.adapter.getAccessTokenForApiRequest()).resolves.toBe(
      "browser-access-token",
    );
    expect(transport.counts().resolveCalls).toBe(beforeToken + 1);

    const beforeRefresh = transport.counts().resolveCalls;
    await expect(browser.adapter.refreshSession()).resolves.toMatchObject({
      state: "AUTHENTICATED",
      userReference: "user-1",
    });
    expect(browser.provider.refreshCalls).toBe(1);
    expect(transport.counts().resolveCalls).toBe(beforeRefresh + 2);

    transport.setResolution({ state: "UNAUTHENTICATED", userReference: null });
    await expect(browser.adapter.getAccessTokenForApiRequest()).rejects.toMatchObject({
      code: "SESSION_EXPIRED",
    });
    expect(browser.adapter.getSessionSnapshot()).toMatchObject({
      canRenderProtectedContent: false,
      canMakeApiRequest: false,
    });
  });

  it("orders CURRENT_SESSION_ONLY sign-out and publishes exactly once", async () => {
    const order: string[] = [];
    let publishCalls = 0;
    const bridge: AuthBrowserSessionFenceBridge = {
      async prepareSignIn() {
        return { redirectUrl };
      },
      async publishSignOut() {
        publishCalls += 1;
        order.push("publish");
      },
      async resolveSession() {
        return { state: "AUTHENTICATED", userReference: "user-1" };
      },
    };
    const browser = createBrowserHarness(bridge, { order });
    browser.provider.emit("INITIAL_SESSION", currentSession());
    await vi.waitFor(() =>
      expect(browser.adapter.getSessionSnapshot().state).toBe("AUTHENTICATED"),
    );
    order.length = 0;
    const signOut = browser.provider.signOutLocal.bind(browser.provider);
    vi.spyOn(browser.provider, "signOutLocal").mockImplementation(async () => {
      order.push("provider-signOutLocal");
      await signOut();
    });

    await expect(browser.adapter.signOut()).resolves.toEqual({
      ok: true,
      error: null,
      destination: "/",
    });
    expect(order).toEqual(["tombstone", "publish", "provider-signOutLocal"]);
    expect(publishCalls).toBe(1);
    expect(browser.provider.signOutCalls).toBe(1);
    expect(browser.tombstone.isActive()).toBe(true);
    expect(browser.adapter.getSessionSnapshot().state).toBe("UNAUTHENTICATED");
  });

  it.each(["publication", "provider"] as const)(
    "keeps browser fail closed when sign-out %s fails",
    async (failure) => {
      const transport = staticBridge({
        state: "AUTHENTICATED",
        userReference: "user-1",
      });
      transport.setFailPublish(failure === "publication");
      const browser = createBrowserHarness(transport.bridge, {
        failProviderSignOut: failure === "provider",
      });
      browser.provider.emit("INITIAL_SESSION", currentSession());
      await vi.waitFor(() =>
        expect(browser.adapter.getSessionSnapshot().state).toBe("AUTHENTICATED"),
      );

      await expect(browser.adapter.signOut()).resolves.toEqual({
        ok: false,
        error: "SIGN_OUT_FAILED",
        destination: "/",
      });
      expect(transport.counts().publishCalls).toBe(1);
      expect(browser.provider.signOutCalls).toBe(1);
      expect(browser.tombstone.isActive()).toBe(true);
      expect(browser.adapter.getSessionSnapshot()).toMatchObject({
        state: "SIGN_OUT_PENDING",
        canRenderProtectedContent: false,
        canMakeApiRequest: false,
      });
    },
  );

  it.each([
    "SIGNED_IN",
    "TOKEN_REFRESHED",
    "INITIAL_SESSION",
    "USER_UPDATED",
  ] as const)(
    "keeps an active tombstone deny-only for provider %s despite AUTHENTICATED resolution",
    async (event) => {
      const transport = staticBridge({
        state: "AUTHENTICATED",
        userReference: "user-1",
      });
      const browser = createBrowserHarness(transport.bridge);
      browser.provider.emit("INITIAL_SESSION", currentSession());
      await vi.waitFor(() =>
        expect(browser.adapter.getSessionSnapshot().state).toBe("AUTHENTICATED"),
      );

      transport.setResolution({ state: "UNAUTHENTICATED", userReference: null });
      await browser.adapter.signOut();
      expect(browser.tombstone.isActive()).toBe(true);
      expect(browser.adapter.getSessionSnapshot().state).toBe("UNAUTHENTICATED");

      transport.setResolution({ state: "AUTHENTICATED", userReference: "user-1" });
      const beforeEvent = transport.counts().resolveCalls;
      browser.provider.emit(event, currentSession("stale-token"));
      await vi.waitFor(() =>
        expect(transport.counts().resolveCalls).toBe(beforeEvent + 1),
      );
      await vi.waitFor(() =>
        expect(browser.adapter.getSessionSnapshot().state).toBe("UNAUTHENTICATED"),
      );
      expect(browser.tombstone.isActive()).toBe(true);
      expect(browser.adapter.getSessionSnapshot()).toMatchObject({
        canRenderProtectedContent: false,
        canMakeApiRequest: false,
      });
      await expect(browser.adapter.getAccessTokenForApiRequest()).rejects.toMatchObject({
        code: "SESSION_EXPIRED",
      });
      expect(browser.tombstone.isActive()).toBe(true);
    },
  );

  it("restores a signed-out browser only after PREPARE_SIGN_IN clears its tombstone", async () => {
    const server = createServerHarness();
    server.provider.session = currentSession();
    server.fence.resolution = {
      eligible: true,
      references: {
        signInAttemptReference: attemptReference,
        callbackFlowReference: "server-callback-reference",
        correlationReference: "server-correlation-reference",
      },
    };
    const requests: unknown[] = [];
    const cookieDocument = new CookieDocument();
    const authorizedCookieMutation = new BrowserLocalSignOutTombstone(
      origin,
      cookieDocument,
    );
    const bridge = createAuthBrowserSessionFenceBridge({
      csrfToken: () => "approved-csrf-token",
      fetch: vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
        const request = JSON.parse(String(init?.body));
        requests.push(request);
        const response = await executeAuthSessionFenceHostRequest(server.host, request);
        if (request.operation === "PREPARE_SIGN_IN") {
          // Simulates the browser applying Auth's successful reconciliation Set-Cookie.
          authorizedCookieMutation.clearAfterAuthorizedReconciliation();
        }
        return Response.json(response);
      }) as typeof globalThis.fetch,
    });
    const browser = createBrowserHarness(bridge, { cookieDocument });
    browser.provider.emit("INITIAL_SESSION", currentSession());
    await vi.waitFor(() =>
      expect(browser.adapter.getSessionSnapshot().state).toBe("AUTHENTICATED"),
    );
    await browser.adapter.signOut();
    expect(browser.tombstone.isActive()).toBe(true);

    await browser.adapter.beginSignIn("/runs");

    expect(browser.tombstone.isActive()).toBe(false);
    expect(requests.filter((request) =>
      (request as { operation?: string }).operation === "PREPARE_SIGN_IN"
    )).toHaveLength(1);
    expect(server.fence.prepareCalls).toBe(1);
    expect(server.provider.beginCalls).toBe(1);
    expect(server.store.createCalls).toBe(1);
    expect(server.fence.associateCalls).toBe(1);
    expect(server.cookieWrites()).toBe(1);
    expect(browser.provider.beginCalls).toBe(0);
    expect(browser.navigations).toEqual([redirectUrl]);

    const recovered = createBrowserHarness(bridge, { cookieDocument });
    recovered.provider.emit("SIGNED_IN", currentSession("fresh-token"));
    await vi.waitFor(() =>
      expect(recovered.adapter.getSessionSnapshot().state).toBe("AUTHENTICATED"),
    );
    expect(recovered.adapter.getSessionSnapshot()).toMatchObject({
      canRenderProtectedContent: true,
      canMakeApiRequest: true,
    });
  });

  it("preserves the seven-operation AuthAdapter boundary without browser callback transport", async () => {
    const browser = createBrowserHarness(staticBridge().bridge);
    expect(
      [
        "beginSignIn",
        "processCallback",
        "getSessionSnapshot",
        "subscribeToSessionChanges",
        "getAccessTokenForApiRequest",
        "refreshSession",
        "signOut",
      ].every(
        (operation) =>
          typeof browser.adapter[operation as keyof typeof browser.adapter] === "function",
      ),
    ).toBe(true);
    await expect(
      browser.adapter.processCallback({ url: "https://browser.invalid", correlationHandles: [] }),
    ).rejects.toMatchObject({ code: "CONFIGURATION_UNAVAILABLE" });
  });
});
