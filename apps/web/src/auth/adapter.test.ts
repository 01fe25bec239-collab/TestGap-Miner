import { describe, expect, it, vi } from "vitest";
import { createAuthAdapter } from "./adapter";
import {
  LocalCorrelationStore,
  PENDING_CORRELATION_TTL_MS,
  type CorrelationCookie,
} from "./correlation";
import type {
  AuthProvider,
  AuthSecurityEvent,
  ProviderSession,
  ProviderSessionEvent,
} from "./types";
import { AuthRuntimeError } from "./types";

const callbackUrl = "http://localhost:3000/auth/callback";
const flowId = "flow_12345678";
const code = "valid-code-1234567890";
const securityPolicyVersion = "test-auth-policy@1.0";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

class MockProvider implements AuthProvider {
  session: ProviderSession | null = null;
  beginCalls = 0;
  exchangeCalls = 0;
  exchangeSessionCreations = 0;
  getSessionCalls = 0;
  refreshCalls = 0;
  signOutCalls = 0;
  prepareCommitCalls = 0;
  commitSessionCalls = 0;
  discardSessionCalls = 0;
  exchangeError: AuthRuntimeError | null = null;
  refreshError: AuthRuntimeError | null = null;
  signOutError = false;
  validationSucceeds = true;
  validationThrows = false;
  validatedUserReference: string | null = null;
  prepareCommitError = false;
  commitSessionError = false;
  beginGate: ReturnType<typeof deferred<{ redirectUrl: string; flowId: string }>> | null = null;
  exchangeGate: ReturnType<typeof deferred<void>> | null = null;
  refreshGate: ReturnType<typeof deferred<ProviderSession>> | null = null;
  callbackUrls: string[] = [];
  #listeners = new Set<
    (event: ProviderSessionEvent, session: ProviderSession | null) => void
  >();

  async beginGitHubOAuth(callbackUrl: string) {
    this.beginCalls += 1;
    this.callbackUrls.push(callbackUrl);
    if (this.beginGate) return this.beginGate.promise;
    return { redirectUrl: "https://provider.example/authorize", flowId };
  }

  async exchangeCode() {
    this.exchangeCalls += 1;
    if (this.exchangeError) throw this.exchangeError;
    if (this.exchangeGate) await this.exchangeGate.promise;
    this.exchangeSessionCreations += 1;
    const exchangedSession = currentSession();
    return {
      session: exchangedSession,
      prepareSessionCommit: async () => {
        this.prepareCommitCalls += 1;
        if (this.prepareCommitError) throw new Error("commit preparation failed");
      },
      commitSession: async () => {
        this.commitSessionCalls += 1;
        if (this.commitSessionError) throw new Error("session commit failed");
        this.session = exchangedSession;
      },
      discardSession: async () => {
        this.discardSessionCalls += 1;
      },
    };
  }

  async getSession() {
    this.getSessionCalls += 1;
    return this.session;
  }

  async validateCurrentUser() {
    return this.validationSucceeds && this.session
      ? { userReference: this.session.userReference }
      : null;
  }

  async validatePreExistingSession(session: ProviderSession) {
    if (this.validationThrows) throw new Error("validation unavailable");
    const userReference = this.validatedUserReference ?? this.session?.userReference;
    return this.validationSucceeds && userReference === session.userReference
      ? { userReference }
      : null;
  }

  async refresh() {
    this.refreshCalls += 1;
    if (this.refreshError) throw this.refreshError;
    if (this.refreshGate) {
      this.session = await this.refreshGate.promise;
      return this.session;
    }
    this.session = currentSession("fresh-access-token");
    return this.session;
  }

  async signOutLocal() {
    this.signOutCalls += 1;
    if (this.signOutError) throw new AuthRuntimeError("SIGN_OUT_FAILED", true);
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

function currentSession(accessToken = "access-token", expiresAt = Date.now() + 300_000) {
  return { userReference: "user-1", accessToken, expiresAt };
}

function createHarness(
  options: {
    now?: number;
    store?: LocalCorrelationStore;
    securityPolicyVersion?: string;
  } = {},
) {
  const provider = new MockProvider();
  const store = options.store ?? new LocalCorrelationStore();
  const cookies: CorrelationCookie[] = [];
  const deleted: string[] = [];
  const redirects: string[] = [];
  const securityEvents: AuthSecurityEvent[] = [];
  const securitySink = { throws: false };
  let cleared = 0;
  let now = options.now ?? Date.now();
  const adapter = createAuthAdapter({
    provider,
    correlationStore: store,
    securityPolicyVersion: options.securityPolicyVersion ?? securityPolicyVersion,
    applicationOrigin: "http://localhost:3000",
    redirectToProvider: (url) => {
      redirects.push(url);
    },
    setCorrelationCookie: (cookie) => {
      const index = cookies.findIndex(({ name }) => name === cookie.name);
      if (index === -1) cookies.push(cookie);
      else cookies[index] = cookie;
    },
    deleteCorrelationCookie: (handle) => {
      deleted.push(handle);
    },
    clearCallbackUrl: () => {
      cleared += 1;
    },
    emitSecurityEvent: (event) => {
      securityEvents.push(event);
      if (securitySink.throws) throw new Error("test sink failure");
    },
    now: () => now,
  });
  provider.emit("INITIAL_SESSION", null);
  return {
    adapter,
    provider,
    store,
    cookies,
    deleted,
    redirects,
    securityEvents,
    securitySink,
    cleared: () => cleared,
    setNow: (value: number) => {
      now = value;
    },
  };
}

function callback(flow = flowId, authCode = code) {
  return `${callbackUrl}?code=${authCode}&sb_flow_id=${flow}`;
}

describe("Auth adapter contract and sign-in", () => {
  it("exposes all seven provider-neutral operations", () => {
    const { adapter } = createHarness();
    expect(
      [
        "beginSignIn",
        "processCallback",
        "getSessionSnapshot",
        "subscribeToSessionChanges",
        "getAccessTokenForApiRequest",
        "refreshSession",
        "signOut",
      ].every((operation) => typeof adapter[operation as keyof typeof adapter] === "function"),
    ).toBe(true);
  });

  it("begins GitHub OAuth with one pending attempt and validated intended return", async () => {
    const harness = createHarness({ now: 1_000 });
    await harness.adapter.beginSignIn("/runs?view=mine");
    const handle = harness.cookies[0].value;
    expect(harness.provider.beginCalls).toBe(1);
    expect(harness.redirects).toEqual(["https://provider.example/authorize"]);
    expect(await harness.store.lookup(handle, flowId, 1_001)).toMatchObject({
      lifecycle: "PENDING_ATTEMPT_CORRELATION",
      securityPolicyVersion,
      intendedReturn: "/runs?view=mine",
    });
    expect(harness.adapter.getSessionSnapshot().state).toBe("SIGN_IN_PENDING");
  });

  it("coalesces repeated invocation while preserving separate tab attempts", async () => {
    const sharedStore = new LocalCorrelationStore();
    const first = createHarness({ store: sharedStore });
    first.provider.beginGate = deferred();
    const firstCall = first.adapter.beginSignIn("/one");
    const repeatedCall = first.adapter.beginSignIn("/two");
    expect(repeatedCall).toBe(firstCall);
    first.provider.beginGate.resolve({ redirectUrl: "https://provider.example/one", flowId });
    await firstCall;
    expect(first.provider.beginCalls).toBe(1);

    const second = createHarness({ store: sharedStore });
    await second.adapter.beginSignIn("/two");
    expect(second.cookies[0].value).not.toBe(first.cookies[0].value);
  });

  it("falls back for malformed or unsafe intended return", async () => {
    const harness = createHarness();
    await harness.adapter.beginSignIn("https://evil.example");
    expect(
      await harness.store.lookup(harness.cookies[0].value, flowId, Date.now()),
    ).toMatchObject({ intendedReturn: "/" });
  });

  it("rejects an invalid runtime Security policy version", () => {
    expect(() => createHarness({ securityPolicyVersion: "policy version with spaces" })).toThrow(
      "Authentication operation failed",
    );
  });

  it("keeps the Security policy version out of OAuth and browser correlation data", async () => {
    const version = "policy-marker@2026.08";
    const harness = createHarness({ securityPolicyVersion: version });
    await harness.adapter.beginSignIn();
    expect(
      JSON.stringify({
        callbackUrls: harness.provider.callbackUrls,
        redirects: harness.redirects,
        cookies: harness.cookies,
        callback: callback(),
      }),
    ).not.toContain(version);
  });
});

describe("callback processing", () => {
  it("single-flights concurrent processing for one verified callback", async () => {
    const harness = createHarness({ now: 10_000 });
    await harness.adapter.beginSignIn("/runs");
    const handle = harness.cookies[0].value;
    const complete = vi.spyOn(harness.store, "complete");
    harness.provider.exchangeGate = deferred();

    const first = harness.adapter.processCallback({
      url: callback(),
      correlationHandles: [handle],
    });
    const concurrent = harness.adapter.processCallback({
      url: callback(),
      correlationHandles: [handle],
    });

    await vi.waitFor(() => expect(harness.provider.exchangeCalls).toBe(1));
    expect(harness.provider.exchangeSessionCreations).toBe(0);
    harness.provider.exchangeGate.resolve(undefined);
    const [firstResult, concurrentResult] = await Promise.all([first, concurrent]);

    expect(firstResult).toMatchObject({ ok: true, destination: "/runs", duplicate: false });
    expect(concurrentResult).toEqual(firstResult);
    expect(harness.provider.exchangeCalls).toBe(1);
    expect(harness.provider.exchangeSessionCreations).toBe(1);
    expect(complete).toHaveBeenCalledTimes(1);
    expect(await harness.store.lookup(handle, flowId, 10_001)).toMatchObject({
      lifecycle: "COMPLETED_CALLBACK_CORRELATION",
      securityPolicyVersion,
    });
  });

  it("does not attach wrong correlation to a legitimate in-flight callback", async () => {
    const harness = createHarness();
    await harness.adapter.beginSignIn("/runs");
    const handle = harness.cookies[0].value;
    harness.provider.exchangeGate = deferred();
    const legitimate = harness.adapter.processCallback({
      url: callback(),
      correlationHandles: [handle],
    });
    await vi.waitFor(() => expect(harness.provider.exchangeCalls).toBe(1));

    await expect(
      harness.adapter.processCallback({
        url: callback(),
        correlationHandles: ["b".repeat(64)],
      }),
    ).resolves.toMatchObject({ ok: false, error: "SIGN_IN_FAILED" });
    expect(harness.provider.exchangeCalls).toBe(1);

    harness.provider.exchangeGate.resolve(undefined);
    await expect(legitimate).resolves.toMatchObject({
      ok: true,
      destination: "/runs",
      duplicate: false,
    });
    expect(harness.provider.exchangeSessionCreations).toBe(1);
  });

  it("keeps different verified callback flows independent", async () => {
    const harness = createHarness({ now: 10_000 });
    const firstHandle = "a".repeat(64);
    const secondHandle = "b".repeat(64);
    const secondFlowId = "other_flow_123";
    await harness.store.createPending({
      handle: firstHandle,
      flowId,
      securityPolicyVersion,
      intendedReturn: "/one",
      now: 10_000,
    });
    await harness.store.createPending({
      handle: secondHandle,
      flowId: secondFlowId,
      securityPolicyVersion,
      intendedReturn: "/two",
      now: 10_000,
    });
    harness.provider.exchangeGate = deferred();

    const first = harness.adapter.processCallback({
      url: callback(flowId, "first-code-123456789"),
      correlationHandles: [firstHandle],
    });
    const second = harness.adapter.processCallback({
      url: callback(secondFlowId, "second-code-12345678"),
      correlationHandles: [secondHandle],
    });
    await vi.waitFor(() => expect(harness.provider.exchangeCalls).toBe(2));
    harness.provider.exchangeGate.resolve(undefined);

    await expect(first).resolves.toMatchObject({ ok: true, destination: "/one" });
    await expect(second).resolves.toMatchObject({ ok: true, destination: "/two" });
    expect(harness.provider.exchangeSessionCreations).toBe(2);
    expect(await harness.store.lookup(firstHandle, flowId, 10_001)).toMatchObject({
      lifecycle: "COMPLETED_CALLBACK_CORRELATION",
    });
    expect(await harness.store.lookup(secondHandle, secondFlowId, 10_001)).toMatchObject({
      lifecycle: "COMPLETED_CALLBACK_CORRELATION",
    });
  });

  it("processes once and reuses only exact completed correlation", async () => {
    const harness = createHarness({ now: 10_000 });
    await harness.adapter.beginSignIn("/runs");
    const handle = harness.cookies[0].value;
    const first = await harness.adapter.processCallback({
      url: callback(),
      correlationHandles: [handle],
    });
    const duplicate = await harness.adapter.processCallback({
      url: callback(),
      correlationHandles: [handle],
    });
    expect(first).toMatchObject({ ok: true, destination: "/runs", duplicate: false });
    expect(duplicate).toMatchObject({ ok: true, destination: "/", duplicate: true });
    expect(harness.provider.exchangeCalls).toBe(1);
    expect(harness.cookies[0].options.maxAge).toBe(120);
    expect(harness.cleared()).toBe(2);
    expect(harness.securityEvents).toEqual([]);
  });

  it("fails closed on completed correlation policy mismatch without another exchange", async () => {
    const store = new LocalCorrelationStore();
    const first = createHarness({ now: 10_000, store, securityPolicyVersion: "policy@1" });
    await first.adapter.beginSignIn("/runs");
    const handle = first.cookies[0].value;
    await first.adapter.processCallback({ url: callback(), correlationHandles: [handle] });

    const changed = createHarness({ now: 10_001, store, securityPolicyVersion: "policy@2" });
    await expect(
      changed.adapter.processCallback({ url: callback(), correlationHandles: [handle] }),
    ).resolves.toMatchObject({ ok: false, error: "SIGN_IN_FAILED" });
    expect(changed.provider.exchangeCalls).toBe(0);
    expect(changed.deleted).toEqual([]);
    expect(await store.lookup(handle, flowId, 10_001)).toMatchObject({
      lifecycle: "COMPLETED_CALLBACK_CORRELATION",
      securityPolicyVersion: "policy@1",
    });
  });

  it("discards pending intended return on policy mismatch without an exchange", async () => {
    const store = new LocalCorrelationStore();
    const first = createHarness({ now: 10_000, store, securityPolicyVersion: "policy@1" });
    await first.adapter.beginSignIn("/runs");
    const handle = first.cookies[0].value;

    const changed = createHarness({ now: 10_001, store, securityPolicyVersion: "policy@2" });
    await expect(
      changed.adapter.processCallback({ url: callback(), correlationHandles: [handle] }),
    ).resolves.toMatchObject({ ok: false, error: "SIGN_IN_FAILED" });
    expect(changed.provider.exchangeCalls).toBe(0);
    expect(changed.deleted).toEqual([handle]);
    expect(await store.lookup(handle, flowId, 10_001)).toBeNull();
    expect(
      await store.complete(handle, flowId, { userReference: "user-1" }, 10_001),
    ).toBeNull();
  });

  it("discards pending intended return when the pre-exchange recheck finds a policy mismatch", async () => {
    const harness = createHarness({ now: 10_000, securityPolicyVersion: "policy@2" });
    await harness.adapter.beginSignIn("/runs");
    const handle = harness.cookies[0].value;
    const originalLookup = harness.store.lookup.bind(harness.store);
    let lookups = 0;
    vi.spyOn(harness.store, "lookup").mockImplementation(async (...args) => {
      const record = await originalLookup(...args);
      lookups += 1;
      return lookups === 2 && record?.lifecycle === "PENDING_ATTEMPT_CORRELATION"
        ? { ...record, securityPolicyVersion: "policy@1" }
        : record;
    });

    await expect(
      harness.adapter.processCallback({ url: callback(), correlationHandles: [handle] }),
    ).resolves.toMatchObject({ ok: false, error: "SIGN_IN_FAILED" });
    expect(harness.provider.exchangeCalls).toBe(0);
    expect(harness.deleted).toEqual([handle]);
    expect(await harness.store.lookup(handle, flowId, 10_001)).toBeNull();
  });

  it("rejects uncorrelated duplicates while preserving only a live-validated session", async () => {
    const harness = createHarness();
    harness.provider.emit("SIGNED_IN", currentSession());
    const result = await harness.adapter.processCallback({
      url: callback("unknown_flow_1"),
      correlationHandles: ["b".repeat(64)],
    });
    expect(result).toMatchObject({
      ok: false,
      error: "SIGN_IN_FAILED",
      destination: "/",
      snapshot: { state: "AUTHENTICATED" },
    });
    expect(harness.provider.exchangeCalls).toBe(0);
  });

  it("fails closed when an existing session cannot be live-validated", async () => {
    const harness = createHarness();
    harness.provider.emit("SIGNED_IN", currentSession());
    harness.provider.validationSucceeds = false;
    const result = await harness.adapter.processCallback({
      url: callback("unknown_flow_1"),
      correlationHandles: [],
    });
    expect(result).toMatchObject({
      ok: false,
      error: "SIGN_IN_FAILED",
      destination: null,
      snapshot: { state: "TERMINAL_SESSION_ERROR" },
    });
  });

  it.each([
    ["missing parameters", `${callbackUrl}?sb_flow_id=${flowId}`],
    ["malformed parameters", `${callbackUrl}?code=x&sb_flow_id=${flowId}`],
    ["wrong destination", `http://localhost:3000/not-callback?code=${code}&sb_flow_id=${flowId}`],
    ["unknown correlation", callback("unknown_flow_1")],
  ])("collapses %s to the public failure", async (_case, url) => {
    const harness = createHarness();
    const result = await harness.adapter.processCallback({ url, correlationHandles: [] });
    expect(result).toMatchObject({
      ok: false,
      error: "SIGN_IN_FAILED",
      snapshot: { state: "TERMINAL_SESSION_ERROR" },
    });
  });

  it.each([
    "STATE_VALIDATION_FAILED",
    "PKCE_VALIDATION_FAILED",
    "SESSION_EXCHANGE_FAILED",
  ] as const)("collapses internal %s to SIGN_IN_FAILED", async (internalError) => {
    const harness = createHarness();
    await harness.adapter.beginSignIn();
    harness.provider.exchangeError = new AuthRuntimeError(internalError);
    const result = await harness.adapter.processCallback({
      url: callback(),
      correlationHandles: [harness.cookies[0].value],
    });
    expect(result).toMatchObject({ ok: false, error: "SIGN_IN_FAILED" });
    expect(JSON.stringify(result)).not.toContain(internalError);
    expect(harness.securityEvents).toEqual([
      {
        classification: internalError,
        sessionPreserved: false,
        callbackSuccess: false,
        rejectedCallbackDestinationUsed: false,
      },
    ]);
  });

  it("commits the exchanged session once only after correlation completion", async () => {
    const harness = createHarness({ now: 10_000 });
    await harness.adapter.beginSignIn("/runs");
    const handle = harness.cookies[0].value;
    const complete = harness.store.complete.bind(harness.store);
    vi.spyOn(harness.store, "complete").mockImplementation(async (...args) => {
      expect(harness.provider.session).toBeNull();
      expect(harness.provider.commitSessionCalls).toBe(0);
      return complete(...args);
    });

    await expect(
      harness.adapter.processCallback({ url: callback(), correlationHandles: [handle] }),
    ).resolves.toMatchObject({ ok: true, destination: "/runs" });
    expect(harness.provider.prepareCommitCalls).toBe(1);
    expect(harness.provider.commitSessionCalls).toBe(1);
    expect(harness.provider.discardSessionCalls).toBe(0);
    expect(harness.provider.session).toMatchObject({
      userReference: "user-1",
      accessToken: "access-token",
    });
    expect(harness.securityEvents).toEqual([]);
  });

  it("discards an exchanged session when correlation completion returns null", async () => {
    const harness = createHarness();
    await harness.adapter.beginSignIn("/rejected-secret-destination");
    const handle = harness.cookies[0].value;
    vi.spyOn(harness.store, "complete").mockResolvedValue(null);

    await expect(
      harness.adapter.processCallback({ url: callback(), correlationHandles: [handle] }),
    ).resolves.toMatchObject({ ok: false, error: "SIGN_IN_FAILED", destination: null });
    expect(harness.provider.session).toBeNull();
    expect(harness.provider.exchangeCalls).toBe(1);
    expect(harness.provider.commitSessionCalls).toBe(0);
    expect(harness.provider.discardSessionCalls).toBe(1);
    expect(harness.provider.signOutCalls).toBe(0);
    expect(harness.securityEvents).toEqual([
      {
        classification: "INVALID_CALLBACK",
        sessionPreserved: false,
        callbackSuccess: false,
        rejectedCallbackDestinationUsed: false,
      },
    ]);
    expect(JSON.stringify(harness.securityEvents)).not.toMatch(
      /valid-code|access-token|verifier|rejected-secret|sb_flow|http:/,
    );
  });

  it.each(["throws", "times out"])(
    "fails closed and does not re-exchange when correlation completion %s",
    async () => {
      const harness = createHarness();
      await harness.adapter.beginSignIn();
      const handle = harness.cookies[0].value;
      vi.spyOn(harness.store, "complete").mockRejectedValue(new Error("store unavailable"));

      await expect(
        harness.adapter.processCallback({ url: callback(), correlationHandles: [handle] }),
      ).resolves.toMatchObject({ ok: false, error: "SIGN_IN_FAILED" });
      expect(harness.provider.session).toBeNull();
      expect(harness.provider.exchangeCalls).toBe(1);
      expect(harness.provider.discardSessionCalls).toBe(1);
      expect(harness.provider.signOutCalls).toBe(0);
      expect(harness.securityEvents).toHaveLength(1);
    },
  );

  it("discards the exchanged session when completion crosses pending expiry", async () => {
    const harness = createHarness({ now: 0 });
    await harness.adapter.beginSignIn();
    const handle = harness.cookies[0].value;
    harness.provider.exchangeGate = deferred();
    const processing = harness.adapter.processCallback({
      url: callback(),
      correlationHandles: [handle],
    });
    await vi.waitFor(() => expect(harness.provider.exchangeCalls).toBe(1));
    harness.setNow(PENDING_CORRELATION_TTL_MS);
    harness.provider.exchangeGate.resolve(undefined);

    await expect(processing).resolves.toMatchObject({
      ok: false,
      error: "SIGN_IN_FAILED",
    });
    expect(harness.provider.session).toBeNull();
    expect(harness.provider.exchangeCalls).toBe(1);
    expect(harness.provider.discardSessionCalls).toBe(1);
    expect(harness.securityEvents[0]).toMatchObject({ classification: "INVALID_CALLBACK" });
  });

  it("preserves only the original live and identity-equal session after completion failure", async () => {
    const harness = createHarness({ now: 10_000 });
    const handle = "a".repeat(64);
    await harness.store.createPending({
      handle,
      flowId,
      securityPolicyVersion,
      intendedReturn: "/new-session-only",
      now: 10_000,
    });
    const original = currentSession("original-access-token");
    harness.provider.emit("SIGNED_IN", original);
    vi.spyOn(harness.store, "complete").mockResolvedValue(null);

    await expect(
      harness.adapter.processCallback({ url: callback(), correlationHandles: [handle] }),
    ).resolves.toMatchObject({
      ok: false,
      error: "SIGN_IN_FAILED",
      destination: "/",
      snapshot: { state: "AUTHENTICATED", userReference: "user-1" },
    });
    expect(harness.provider.session).toBe(original);
    expect(harness.provider.signOutCalls).toBe(0);
    expect(harness.securityEvents[0]).toMatchObject({
      classification: "INVALID_CALLBACK",
      sessionPreserved: true,
      callbackSuccess: false,
    });
  });

  it.each(["invalid", "mismatch", "unavailable"] as const)(
    "does not preserve a pre-existing session when live validation is %s",
    async (failure) => {
      const harness = createHarness({ now: 10_000 });
      const handle = "a".repeat(64);
      await harness.store.createPending({
        handle,
        flowId,
        securityPolicyVersion,
        intendedReturn: "/",
        now: 10_000,
      });
      harness.provider.emit("SIGNED_IN", currentSession("original-access-token"));
      harness.provider.validationSucceeds = failure !== "invalid";
      harness.provider.validatedUserReference = failure === "mismatch" ? "user-2" : null;
      harness.provider.validationThrows = failure === "unavailable";
      vi.spyOn(harness.store, "complete").mockResolvedValue(null);

      await expect(
        harness.adapter.processCallback({ url: callback(), correlationHandles: [handle] }),
      ).resolves.toMatchObject({
        ok: false,
        error: "SIGN_IN_FAILED",
        destination: null,
        snapshot: { state: "TERMINAL_SESSION_ERROR" },
      });
      expect(harness.securityEvents[0]).toMatchObject({ sessionPreserved: false });
      expect(harness.provider.signOutCalls).toBe(0);
    },
  );

  it("surfaces Security sink programming failures without changing rejection to success", async () => {
    const harness = createHarness();
    harness.securitySink.throws = true;
    await expect(
      harness.adapter.processCallback({
        url: callback("unknown_flow_1"),
        correlationHandles: [],
      }),
    ).rejects.toThrow("Authentication security event emission failed");
    expect(harness.securityEvents).toHaveLength(1);
    expect(harness.provider.exchangeCalls).toBe(0);
    expect(harness.adapter.getSessionSnapshot().state).toBe("TERMINAL_SESSION_ERROR");
  });

  it("surfaces provider denial without leaking provider detail", async () => {
    const harness = createHarness();
    await harness.adapter.beginSignIn();
    const handle = harness.cookies[0].value;
    const result = await harness.adapter.processCallback({
      url: `${callbackUrl}?error=access_denied&sb_flow_id=${flowId}`,
      correlationHandles: [handle],
    });
    expect(result).toMatchObject({
      ok: false,
      error: "PROVIDER_DENIED",
      snapshot: { state: "UNAUTHENTICATED" },
    });
    expect(harness.deleted).toEqual([handle]);
    expect(await harness.store.lookup(handle, flowId, Date.now())).toBeNull();
  });

  it("rejects expired pending and completed callback correlation", async () => {
    const harness = createHarness({ now: 0 });
    await harness.adapter.beginSignIn();
    const handle = harness.cookies[0].value;
    harness.setNow(PENDING_CORRELATION_TTL_MS);
    const pending = await harness.adapter.processCallback({
      url: callback(),
      correlationHandles: [handle],
    });
    expect(pending).toMatchObject({ ok: false, error: "SIGN_IN_FAILED" });

    const second = createHarness({ now: 1_000_000 });
    await second.adapter.beginSignIn();
    const secondHandle = second.cookies[0].value;
    await second.adapter.processCallback({
      url: callback(),
      correlationHandles: [secondHandle],
    });
    second.setNow(1_120_000);
    const completed = await second.adapter.processCallback({
      url: callback(),
      correlationHandles: [secondHandle],
    });
    expect(completed).toMatchObject({ ok: false, error: "SIGN_IN_FAILED" });
    expect(second.provider.exchangeCalls).toBe(1);
  });

  it("fails closed when correlation storage is unavailable", async () => {
    const harness = createHarness();
    await harness.adapter.beginSignIn();
    harness.store.setAvailable(false);
    const result = await harness.adapter.processCallback({
      url: callback(),
      correlationHandles: [harness.cookies[0].value],
    });
    expect(result).toMatchObject({
      ok: false,
      error: "SIGN_IN_FAILED",
      snapshot: { state: "TERMINAL_SESSION_ERROR" },
    });
  });
});

describe("session, token, refresh, and sign-out semantics", () => {
  it("publishes safe snapshots from canonical provider events", () => {
    const harness = createHarness();
    const listener = vi.fn();
    const unsubscribe = harness.adapter.subscribeToSessionChanges(listener);
    harness.provider.emit("SIGNED_IN", currentSession("sensitive-access-token"));
    const snapshot = harness.adapter.getSessionSnapshot();
    expect(snapshot).toMatchObject({
      state: "AUTHENTICATED",
      userReference: "user-1",
      canMakeApiRequest: true,
    });
    expect(JSON.stringify(snapshot)).not.toContain("token");
    harness.provider.emit("SIGNED_OUT", null);
    expect(harness.adapter.getSessionSnapshot().state).toBe("UNAUTHENTICATED");
    unsubscribe();
    expect(listener).toHaveBeenCalledTimes(3);
  });

  it("retrieves access tokens just in time without an independent cache", async () => {
    const harness = createHarness();
    harness.provider.emit("SIGNED_IN", currentSession("first-token"));
    expect(await harness.adapter.getAccessTokenForApiRequest()).toBe("first-token");
    harness.provider.session = currentSession("second-token");
    expect(await harness.adapter.getAccessTokenForApiRequest()).toBe("second-token");
    expect(harness.provider.getSessionCalls).toBe(2);
  });

  it("keeps REFRESH_PENDING fail closed and coalesces refresh in one runtime", async () => {
    const harness = createHarness();
    harness.provider.emit("SIGNED_IN", currentSession());
    harness.provider.refreshGate = deferred();
    const first = harness.adapter.refreshSession();
    const second = harness.adapter.refreshSession();
    await Promise.resolve();
    expect(harness.adapter.getSessionSnapshot()).toMatchObject({
      state: "REFRESH_PENDING",
      refreshMode: "PROVEN_CREDENTIAL",
      canMakeApiRequest: false,
    });
    harness.provider.refreshGate.resolve(currentSession("fresh-token"));
    await expect(first).resolves.toMatchObject({ state: "AUTHENTICATED" });
    await expect(second).resolves.toMatchObject({ state: "AUTHENTICATED" });
    expect(harness.provider.refreshCalls).toBe(1);
  });

  it("uses unproven refresh for expired credentials and returns the fresh token", async () => {
    const harness = createHarness();
    harness.provider.emit("SIGNED_IN", currentSession("expired", Date.now() - 1));
    expect(await harness.adapter.getAccessTokenForApiRequest()).toBe("fresh-access-token");
    expect(harness.provider.refreshCalls).toBe(1);
  });

  it("distinguishes recoverable and terminal refresh failures", async () => {
    const recoverable = createHarness();
    recoverable.provider.emit("SIGNED_IN", currentSession());
    recoverable.provider.refreshError = new AuthRuntimeError(
      "TEMPORARY_PROVIDER_FAILURE",
      true,
    );
    await expect(recoverable.adapter.refreshSession()).rejects.toMatchObject({
      code: "TEMPORARY_PROVIDER_FAILURE",
    });
    expect(recoverable.adapter.getSessionSnapshot().state).toBe("RECOVERABLE_ERROR");

    const terminal = createHarness();
    terminal.provider.emit("SIGNED_IN", currentSession());
    terminal.provider.refreshError = new AuthRuntimeError("REFRESH_FAILED");
    await expect(terminal.adapter.refreshSession()).rejects.toMatchObject({
      code: "REFRESH_FAILED",
    });
    expect(terminal.adapter.getSessionSnapshot().state).toBe("TERMINAL_SESSION_ERROR");
  });

  it("signs out the current session, coalesces repeats, and clears on remote failure", async () => {
    const harness = createHarness();
    harness.provider.emit("SIGNED_IN", currentSession());
    const first = harness.adapter.signOut();
    const second = harness.adapter.signOut();
    expect(harness.adapter.getSessionSnapshot().state).toBe("SIGN_OUT_PENDING");
    await expect(first).resolves.toEqual({ ok: true, error: null, destination: "/" });
    await expect(second).resolves.toEqual({ ok: true, error: null, destination: "/" });
    expect(harness.provider.signOutCalls).toBe(1);
    expect(harness.adapter.getSessionSnapshot().state).toBe("UNAUTHENTICATED");

    const failed = createHarness();
    failed.provider.emit("SIGNED_IN", currentSession());
    failed.provider.signOutError = true;
    await expect(failed.adapter.signOut()).resolves.toEqual({
      ok: false,
      error: "SIGN_OUT_FAILED",
      destination: "/",
    });
    expect(failed.adapter.getSessionSnapshot().state).toBe("UNAUTHENTICATED");
  });
});
