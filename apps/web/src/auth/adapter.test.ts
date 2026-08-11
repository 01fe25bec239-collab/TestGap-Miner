import { describe, expect, it, vi } from "vitest";
import { createAuthAdapter } from "./adapter";
import {
  LocalCorrelationStore,
  PENDING_CORRELATION_TTL_MS,
  type CorrelationCookie,
} from "./correlation";
import {
  AuthSessionFenceHostService,
  AuthSessionFenceService,
  LocalProcessAuthSynchronizationAuthority,
  createOpaqueAuthHandle,
  type AuthFenceStateStore,
} from "./session-fence";
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
  validationGate: ReturnType<typeof deferred<void>> | null = null;
  validationCalls = 0;
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
    this.validationCalls += 1;
    if (this.validationGate) await this.validationGate.promise;
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

class MemoryFenceState implements AuthFenceStateStore {
  contextHandle: string | null = null;
  sessionBindingHandle: string | null = null;
  tombstone = false;
  contextWrites = 0;
  bindingClears = 0;
  tombstoneClears = 0;

  async readAuthContextHandle() {
    return this.contextHandle;
  }

  async writeAuthContextHandle(handle: string) {
    this.contextHandle = handle;
    this.contextWrites += 1;
  }

  async readSessionBindingHandle() {
    return this.sessionBindingHandle;
  }

  async writeSessionBindingHandle(handle: string) {
    this.sessionBindingHandle = handle;
  }

  async clearSessionBindingHandle() {
    this.sessionBindingHandle = null;
    this.bindingClears += 1;
  }

  async hasLocalSignOutTombstone() {
    return this.tombstone;
  }

  createLocalSignOutTombstone() {
    this.tombstone = true;
  }

  async clearLocalSignOutTombstone() {
    this.tombstone = false;
    this.tombstoneClears += 1;
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
    authority?: LocalProcessAuthSynchronizationAuthority;
    fenceState?: MemoryFenceState;
  } = {},
) {
  const provider = new MockProvider();
  const store = options.store ?? new LocalCorrelationStore();
  const cookies: CorrelationCookie[] = [];
  const deleted: string[] = [];
  const redirects: string[] = [];
  const securityEvents: AuthSecurityEvent[] = [];
  const securitySink = { throws: false };
  const authority =
    options.authority ??
    new LocalProcessAuthSynchronizationAuthority("LOCAL_NON_PRODUCTION_ONLY");
  const fenceState = options.fenceState ?? new MemoryFenceState();
  const sessionFence = new AuthSessionFenceService(authority, fenceState);
  let cleared = 0;
  let now = options.now ?? Date.now();
  const adapter = createAuthAdapter({
    provider,
    correlationStore: store,
    sessionFence,
    securityPolicyVersion: options.securityPolicyVersion ?? securityPolicyVersion,
    environmentClass: "TEST",
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
    authority,
    fenceState,
    sessionFence,
    cleared: () => cleared,
    setNow: (value: number) => {
      now = value;
    },
  };
}

function createHost(harness: ReturnType<typeof createHarness>) {
  return new AuthSessionFenceHostService({
    provider: harness.provider,
    correlationStore: harness.store,
    sessionFence: harness.sessionFence,
    securityPolicyVersion,
    applicationOrigin: "http://localhost:3000",
    setCorrelationCookie: (cookie) => {
      harness.cookies.push(cookie);
    },
    deleteCorrelationCookie: () => {},
  });
}

async function establishAuthenticatedSession(
  harness: ReturnType<typeof createHarness>,
  session = currentSession(),
) {
  await establishFenceBinding(harness);
  harness.provider.emit("SIGNED_IN", session);
  await vi.waitFor(() =>
    expect(harness.adapter.getSessionSnapshot().state).toBe("AUTHENTICATED"),
  );
}

async function establishFenceBinding(harness: ReturnType<typeof createHarness>) {
  const prepared = await harness.sessionFence.prepareSignIn();
  const callbackLookupHandle = createOpaqueAuthHandle();
  await harness.sessionFence.associateSignInAttempt(
    prepared.signInAttemptReference,
    callbackLookupHandle,
  );
  await harness.sessionFence.establishSession(callbackLookupHandle);
}

async function associateFenceAttempt(
  harness: ReturnType<typeof createHarness>,
  callbackLookupHandle: string,
) {
  const prepared = await harness.sessionFence.prepareSignIn();
  await harness.sessionFence.associateSignInAttempt(
    prepared.signInAttemptReference,
    callbackLookupHandle,
  );
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
    await associateFenceAttempt(harness, firstHandle);
    await associateFenceAttempt(harness, secondHandle);
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
    await establishAuthenticatedSession(harness);
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
    expect(harness.securityEvents).toMatchObject([
      {
        classification: internalError,
        sessionPreserved: false,
        callbackSuccess: false,
        rejectedCallbackDestinationUsed: false,
      },
    ]);
    expect(harness.securityEvents[0].signInAttemptReference).toMatch(/^[a-f0-9]{64}$/);
    expect(harness.securityEvents[0].callbackFlowReference).toMatch(/^[a-f0-9]{64}$/);
    expect(harness.securityEvents[0].correlationReference).toMatch(/^[a-f0-9]{64}$/);
    expect([
      harness.securityEvents[0].signInAttemptReference,
      harness.securityEvents[0].callbackFlowReference,
      harness.securityEvents[0].correlationReference,
    ]).not.toContain(harness.cookies[0].value);
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
    expect(harness.securityEvents).toMatchObject([
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
    await establishAuthenticatedSession(harness, original);
    await associateFenceAttempt(harness, handle);
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
      await establishAuthenticatedSession(
        harness,
        currentSession("original-access-token"),
      );
      await associateFenceAttempt(harness, handle);
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
      expect(harness.provider.signOutCalls).toBe(1);
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
  it("treats provider events as provisional until fence verification", async () => {
    const harness = createHarness();
    const listener = vi.fn();
    const unsubscribe = harness.adapter.subscribeToSessionChanges(listener);
    await establishFenceBinding(harness);
    harness.provider.emit("SIGNED_IN", currentSession("sensitive-access-token"));
    expect(harness.adapter.getSessionSnapshot()).toMatchObject({
      state: "INITIALIZING",
      canRenderProtectedContent: false,
      canMakeApiRequest: false,
    });
    await vi.waitFor(() =>
      expect(harness.adapter.getSessionSnapshot().state).toBe("AUTHENTICATED"),
    );
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
    expect(listener).toHaveBeenCalledTimes(4);
  });

  it("retrieves access tokens just in time without an independent cache", async () => {
    const harness = createHarness();
    await establishAuthenticatedSession(harness, currentSession("first-token"));
    const callsBeforeRequests = harness.provider.getSessionCalls;
    expect(await harness.adapter.getAccessTokenForApiRequest()).toBe("first-token");
    harness.provider.session = currentSession("second-token");
    expect(await harness.adapter.getAccessTokenForApiRequest()).toBe("second-token");
    expect(harness.provider.getSessionCalls - callsBeforeRequests).toBe(2);
  });

  it("keeps REFRESH_PENDING fail closed and coalesces refresh in one runtime", async () => {
    const harness = createHarness();
    await establishAuthenticatedSession(harness);
    harness.provider.refreshGate = deferred();
    const first = harness.adapter.refreshSession();
    const second = harness.adapter.refreshSession();
    await vi.waitFor(() =>
      expect(harness.adapter.getSessionSnapshot()).toMatchObject({
        state: "REFRESH_PENDING",
        refreshMode: "PROVEN_CREDENTIAL",
        canMakeApiRequest: false,
      }),
    );
    harness.provider.refreshGate.resolve(currentSession("fresh-token"));
    await expect(first).resolves.toMatchObject({ state: "AUTHENTICATED" });
    await expect(second).resolves.toMatchObject({ state: "AUTHENTICATED" });
    expect(harness.provider.refreshCalls).toBe(1);
  });

  it("uses unproven refresh for expired credentials and returns the fresh token", async () => {
    const harness = createHarness();
    await establishAuthenticatedSession(
      harness,
      currentSession("expired", Date.now() - 1),
    );
    expect(await harness.adapter.getAccessTokenForApiRequest()).toBe("fresh-access-token");
    expect(harness.provider.refreshCalls).toBe(1);
  });

  it("distinguishes recoverable and terminal refresh failures", async () => {
    const recoverable = createHarness();
    await establishAuthenticatedSession(recoverable);
    recoverable.provider.refreshError = new AuthRuntimeError(
      "TEMPORARY_PROVIDER_FAILURE",
      true,
    );
    await expect(recoverable.adapter.refreshSession()).rejects.toMatchObject({
      code: "TEMPORARY_PROVIDER_FAILURE",
    });
    expect(recoverable.adapter.getSessionSnapshot().state).toBe("RECOVERABLE_ERROR");

    const terminal = createHarness();
    await establishAuthenticatedSession(terminal);
    terminal.provider.refreshError = new AuthRuntimeError("REFRESH_FAILED");
    await expect(terminal.adapter.refreshSession()).rejects.toMatchObject({
      code: "REFRESH_FAILED",
    });
    expect(terminal.adapter.getSessionSnapshot().state).toBe("TERMINAL_SESSION_ERROR");
  });

  it("signs out the current session, coalesces repeats, and clears on remote failure", async () => {
    const harness = createHarness();
    await establishAuthenticatedSession(harness);
    const first = harness.adapter.signOut();
    const second = harness.adapter.signOut();
    expect(harness.adapter.getSessionSnapshot().state).toBe("SIGN_OUT_PENDING");
    await expect(first).resolves.toEqual({ ok: true, error: null, destination: "/" });
    await expect(second).resolves.toEqual({ ok: true, error: null, destination: "/" });
    expect(harness.provider.signOutCalls).toBe(1);
    expect(harness.adapter.getSessionSnapshot().state).toBe("UNAUTHENTICATED");

    const failed = createHarness();
    await establishAuthenticatedSession(failed);
    failed.provider.signOutError = true;
    await expect(failed.adapter.signOut()).resolves.toEqual({
      ok: false,
      error: "SIGN_OUT_FAILED",
      destination: "/",
    });
    expect(failed.adapter.getSessionSnapshot().state).toBe("UNAUTHENTICATED");
  });
});

describe("AUTH-007 generation fence regressions", () => {
  it("does not restore a completed callback after stale preserved-session validation", async () => {
    const harness = createHarness({ now: 10_000 });
    await harness.adapter.beginSignIn("/runs");
    const handle = harness.cookies[0].value;
    await harness.adapter.processCallback({
      url: callback(),
      correlationHandles: [handle],
    });
    const finalFenceStarted = deferred<void>();
    const finalFenceGate = deferred<void>();
    const resolveFence = harness.sessionFence.resolveFence.bind(harness.sessionFence);
    vi.spyOn(harness.sessionFence, "resolveFence").mockImplementation(async () => {
      const resolution = await resolveFence();
      finalFenceStarted.resolve(undefined);
      await finalFenceGate.promise;
      return resolution;
    });

    const duplicate = harness.adapter.processCallback({
      url: callback(),
      correlationHandles: [handle],
    });
    await finalFenceStarted.promise;
    const signOutState = new MemoryFenceState();
    signOutState.contextHandle = harness.fenceState.contextHandle;
    const signOutService = new AuthSessionFenceService(harness.authority, signOutState);
    signOutService.createLocalSignOutTombstone();
    await signOutService.publishSignOut();
    finalFenceGate.resolve(undefined);

    await expect(duplicate).resolves.toMatchObject({
      ok: false,
      error: "SIGN_IN_FAILED",
      destination: null,
      snapshot: { canRenderProtectedContent: false, canMakeApiRequest: false },
    });
    expect(harness.adapter.getSessionSnapshot().state).not.toBe("AUTHENTICATED");
    expect(harness.provider.session).toBeNull();
    expect(harness.fenceState.sessionBindingHandle).toBeNull();
    await expect(harness.adapter.getAccessTokenForApiRequest()).rejects.toMatchObject({
      code: "SESSION_EXPIRED",
    });
  });

  it("does not preserve a rejected callback session after stale fence validation", async () => {
    const harness = createHarness();
    await establishAuthenticatedSession(
      harness,
      currentSession("preserved-session-token"),
    );
    const finalFenceStarted = deferred<void>();
    const finalFenceGate = deferred<void>();
    const resolveFence = harness.sessionFence.resolveFence.bind(harness.sessionFence);
    vi.spyOn(harness.sessionFence, "resolveFence").mockImplementation(async () => {
      const resolution = await resolveFence();
      finalFenceStarted.resolve(undefined);
      await finalFenceGate.promise;
      return resolution;
    });

    const rejected = harness.adapter.processCallback({
      url: callback("unknown_flow_1"),
      correlationHandles: [],
    });
    await finalFenceStarted.promise;
    const signOutState = new MemoryFenceState();
    signOutState.contextHandle = harness.fenceState.contextHandle;
    const signOutService = new AuthSessionFenceService(harness.authority, signOutState);
    signOutService.createLocalSignOutTombstone();
    await signOutService.publishSignOut();
    finalFenceGate.resolve(undefined);

    await expect(rejected).resolves.toMatchObject({
      ok: false,
      error: "SIGN_IN_FAILED",
      destination: null,
      snapshot: { canRenderProtectedContent: false, canMakeApiRequest: false },
    });
    expect(harness.securityEvents).toMatchObject([{ sessionPreserved: false }]);
    expect(harness.adapter.getSessionSnapshot().state).not.toBe("AUTHENTICATED");
    expect(harness.provider.session).toBeNull();
    await expect(harness.adapter.getAccessTokenForApiRequest()).rejects.toMatchObject({
      code: "SESSION_EXPIRED",
    });
  });

  it("does not return an access token after stale final fence validation", async () => {
    const harness = createHarness();
    await establishAuthenticatedSession(harness, currentSession("must-not-escape"));
    const finalFenceStarted = deferred<void>();
    const finalFenceGate = deferred<void>();
    const resolveFence = harness.sessionFence.resolveFence.bind(harness.sessionFence);
    let resolutions = 0;
    vi.spyOn(harness.sessionFence, "resolveFence").mockImplementation(async () => {
      const resolution = await resolveFence();
      resolutions += 1;
      if (resolutions === 2) {
        finalFenceStarted.resolve(undefined);
        await finalFenceGate.promise;
      }
      return resolution;
    });

    const token = harness.adapter.getAccessTokenForApiRequest();
    await finalFenceStarted.promise;
    const signOutState = new MemoryFenceState();
    signOutState.contextHandle = harness.fenceState.contextHandle;
    const signOutService = new AuthSessionFenceService(harness.authority, signOutState);
    signOutService.createLocalSignOutTombstone();
    await signOutService.publishSignOut();
    finalFenceGate.resolve(undefined);

    await expect(token).rejects.toMatchObject({ code: "SESSION_EXPIRED" });
    expect(harness.adapter.getSessionSnapshot().state).not.toBe("AUTHENTICATED");
    expect(harness.provider.session).toBeNull();
    expect(harness.fenceState.sessionBindingHandle).toBeNull();
  });

  it("enforces a shared generation fence across distinct callback and sign-out services", async () => {
    const callbackRuntime = createHarness();
    await callbackRuntime.adapter.beginSignIn("/runs");
    const handle = callbackRuntime.cookies[0].value;
    callbackRuntime.provider.exchangeGate = deferred();
    const callbackResult = callbackRuntime.adapter.processCallback({
      url: callback(),
      correlationHandles: [handle],
    });
    await vi.waitFor(() => expect(callbackRuntime.provider.exchangeCalls).toBe(1));

    const signOutState = new MemoryFenceState();
    signOutState.contextHandle = callbackRuntime.fenceState.contextHandle;
    const signOutService = new AuthSessionFenceService(
      callbackRuntime.authority,
      signOutState,
    );
    signOutService.createLocalSignOutTombstone();
    await signOutService.publishSignOut();

    callbackRuntime.provider.exchangeGate.resolve(undefined);
    await expect(callbackResult).resolves.toMatchObject({
      ok: false,
      error: "SIGN_IN_FAILED",
      snapshot: { canRenderProtectedContent: false, canMakeApiRequest: false },
    });
    expect(callbackRuntime.provider.commitSessionCalls).toBe(0);
    expect(callbackRuntime.provider.discardSessionCalls).toBe(1);
    expect(callbackRuntime.adapter.getSessionSnapshot().state).not.toBe("AUTHENTICATED");
    await expect(
      callbackRuntime.adapter.getAccessTokenForApiRequest(),
    ).rejects.toMatchObject({ code: "SESSION_EXPIRED" });
  });

  it("lets sign-out win when a generation-G callback resolves after G+1", async () => {
    const harness = createHarness();
    await harness.adapter.beginSignIn("/runs");
    const oldHandle = harness.cookies[0].value;
    harness.provider.exchangeGate = deferred();
    const callbackResult = harness.adapter.processCallback({
      url: callback(),
      correlationHandles: [oldHandle],
    });
    await vi.waitFor(() => expect(harness.provider.exchangeCalls).toBe(1));

    await expect(harness.adapter.signOut()).resolves.toEqual({
      ok: true,
      error: null,
      destination: "/",
    });
    harness.provider.exchangeGate.resolve(undefined);
    await expect(callbackResult).resolves.toMatchObject({
      ok: false,
      error: "SIGN_IN_FAILED",
      snapshot: { canRenderProtectedContent: false, canMakeApiRequest: false },
    });
    expect(harness.provider.commitSessionCalls).toBe(0);
    expect(harness.provider.discardSessionCalls).toBe(1);
    await expect(harness.adapter.getAccessTokenForApiRequest()).rejects.toMatchObject({
      code: "SESSION_EXPIRED",
    });
  });

  it("keeps local Auth signed out when sign-out publication fails", async () => {
    const harness = createHarness();
    await establishAuthenticatedSession(harness);
    harness.authority.setAvailableForTests(false);

    await expect(harness.adapter.signOut()).resolves.toEqual({
      ok: false,
      error: "SIGN_OUT_FAILED",
      destination: "/",
    });
    expect(harness.fenceState.tombstone).toBe(true);
    expect(harness.provider.signOutCalls).toBeGreaterThan(0);
    expect(harness.adapter.getSessionSnapshot()).toMatchObject({
      state: "UNAUTHENTICATED",
      canRenderProtectedContent: false,
      canMakeApiRequest: false,
    });

    harness.provider.emit("SIGNED_IN", currentSession("stale-token"));
    await vi.waitFor(() =>
      expect(harness.adapter.getSessionSnapshot().state).not.toBe("INITIALIZING"),
    );
    expect(harness.adapter.getSessionSnapshot().state).not.toBe("AUTHENTICATED");
  });

  it("clears a tombstone only after successful explicit reconciliation", async () => {
    const successful = createHarness();
    await establishAuthenticatedSession(successful);
    await successful.adapter.signOut();
    expect(successful.fenceState.tombstone).toBe(true);
    await successful.adapter.beginSignIn();
    expect(successful.fenceState.tombstone).toBe(false);
    expect(successful.provider.beginCalls).toBe(1);

    const failed = createHarness();
    await establishAuthenticatedSession(failed);
    failed.authority.setAvailableForTests(false);
    await failed.adapter.signOut();
    failed.authority.setAvailableForTests(true);
    await expect(failed.adapter.beginSignIn()).rejects.toMatchObject({
      code: "TEMPORARY_PROVIDER_FAILURE",
    });
    expect(failed.fenceState.tombstone).toBe(true);
    expect(failed.provider.beginCalls).toBe(0);
  });

  it("does not start OAuth when a missing tombstone hides unreconciled authority state", async () => {
    const harness = createHarness();
    await establishAuthenticatedSession(harness);
    await harness.adapter.signOut();
    harness.fenceState.tombstone = false;
    vi.spyOn(harness.fenceState, "clearLocalSignOutTombstone").mockRejectedValueOnce(
      new Error("reconciliation unavailable"),
    );

    await expect(harness.adapter.beginSignIn()).rejects.toMatchObject({
      code: "TEMPORARY_PROVIDER_FAILURE",
    });
    expect(harness.provider.beginCalls).toBe(0);
    expect(harness.fenceState.tombstone).toBe(true);

    await expect(harness.adapter.beginSignIn()).resolves.toBeUndefined();
    expect(harness.provider.beginCalls).toBe(1);
    expect(harness.fenceState.tombstone).toBe(false);
  });

  it("does not let an old proof clear a second tombstone after publication failure", async () => {
    const harness = createHarness();
    await harness.adapter.beginSignIn("/generation-g");
    await expect(harness.adapter.signOut()).resolves.toMatchObject({ ok: true });

    await harness.adapter.beginSignIn("/generation-g-plus-one");
    const currentHandle = harness.cookies.at(-1)!.value;
    expect(harness.fenceState.tombstone).toBe(false);
    const providerBegins = harness.provider.beginCalls;

    vi.spyOn(harness.authority, "advanceSignOutGeneration").mockImplementationOnce(
      () => {
        harness.authority.setAvailableForTests(false);
        throw new Error("Auth synchronization authority unavailable");
      },
    );
    await expect(harness.adapter.signOut()).resolves.toEqual({
      ok: false,
      error: "SIGN_OUT_FAILED",
      destination: "/",
    });
    harness.authority.setAvailableForTests(true);

    await expect(harness.adapter.beginSignIn()).rejects.toMatchObject({
      code: "TEMPORARY_PROVIDER_FAILURE",
    });
    expect(harness.provider.beginCalls).toBe(providerBegins);
    expect(harness.fenceState.tombstone).toBe(true);
    await expect(
      harness.adapter.processCallback({
        url: callback(),
        correlationHandles: [currentHandle],
      }),
    ).resolves.toMatchObject({ ok: false, error: "SIGN_IN_FAILED" });
    expect(harness.provider.exchangeCalls).toBe(0);
    expect(harness.adapter.getSessionSnapshot().state).not.toBe("AUTHENTICATED");
    await expect(harness.adapter.getAccessTokenForApiRequest()).rejects.toMatchObject({
      code: "SESSION_EXPIRED",
    });
  });

  it("requires provider validity for the complete Auth-owned RESOLVE_SESSION", async () => {
    const harness = createHarness();
    await establishFenceBinding(harness);
    const host = createHost(harness);
    expect(
      Object.getOwnPropertyNames(AuthSessionFenceHostService.prototype),
    ).toEqual(["constructor", "prepareSignIn", "publishSignOut", "resolveSession"]);

    await expect(host.resolveSession()).resolves.toEqual({
      state: "UNAUTHENTICATED",
      userReference: null,
    });
    expect(harness.fenceState.sessionBindingHandle).toBeNull();

    await establishFenceBinding(harness);
    harness.provider.session = currentSession("must-not-be-returned");
    await expect(host.resolveSession()).resolves.toEqual({
      state: "AUTHENTICATED",
      userReference: "user-1",
    });
    expect(JSON.stringify(await host.resolveSession())).not.toMatch(
      /must-not-be-returned|token|context|binding|generation/i,
    );

    harness.provider.validationSucceeds = false;
    await expect(host.resolveSession()).resolves.toEqual({
      state: "UNAUTHENTICATED",
      userReference: null,
    });
    expect(harness.provider.session).toBeNull();
  });

  it("rechecks the host fence after held live provider validation", async () => {
    const harness = createHarness();
    await establishFenceBinding(harness);
    harness.provider.session = currentSession("must-not-escape");
    harness.provider.validationGate = deferred();
    const host = createHost(harness);
    const resolution = host.resolveSession();
    await vi.waitFor(() => expect(harness.provider.validationCalls).toBeGreaterThan(0));

    const signOutState = new MemoryFenceState();
    signOutState.contextHandle = harness.fenceState.contextHandle;
    const signOutService = new AuthSessionFenceService(
      harness.authority,
      signOutState,
    );
    signOutService.createLocalSignOutTombstone();
    await signOutService.publishSignOut();
    harness.provider.validationGate.resolve(undefined);

    await expect(resolution).resolves.toEqual({
      state: "UNAUTHENTICATED",
      userReference: null,
    });
    expect(harness.provider.session).toBeNull();
    expect(JSON.stringify(await resolution)).not.toMatch(
      /must-not-escape|token|context|binding|generation/i,
    );
  });

  it("does not restore callback authentication after a stale final fence result", async () => {
    const harness = createHarness();
    await harness.adapter.beginSignIn("/runs");
    const handle = harness.cookies[0].value;
    const finalFenceStarted = deferred<void>();
    const finalFenceGate = deferred<void>();
    const resolveFence = harness.sessionFence.resolveFence.bind(harness.sessionFence);
    let heldFinalFence = false;
    vi.spyOn(harness.sessionFence, "resolveFence").mockImplementation(async () => {
      const resolution = await resolveFence();
      if (harness.provider.commitSessionCalls === 1 && !heldFinalFence) {
        heldFinalFence = true;
        finalFenceStarted.resolve(undefined);
        await finalFenceGate.promise;
      }
      return resolution;
    });
    const callbackResult = harness.adapter.processCallback({
      url: callback(),
      correlationHandles: [handle],
    });
    await finalFenceStarted.promise;

    const signOutState = new MemoryFenceState();
    signOutState.contextHandle = harness.fenceState.contextHandle;
    const signOutService = new AuthSessionFenceService(
      harness.authority,
      signOutState,
    );
    signOutService.createLocalSignOutTombstone();
    await signOutService.publishSignOut();
    finalFenceGate.resolve(undefined);

    await expect(callbackResult).resolves.toMatchObject({
      ok: false,
      error: "SIGN_IN_FAILED",
      snapshot: { canRenderProtectedContent: false, canMakeApiRequest: false },
    });
    expect(harness.provider.commitSessionCalls).toBe(1);
    expect(harness.provider.session).toBeNull();
    expect(harness.adapter.getSessionSnapshot().state).not.toBe("AUTHENTICATED");
  });

  it("keeps callback A stale after sign-out and newer intentional sign-in B", async () => {
    const harness = createHarness();
    await harness.adapter.beginSignIn("/old");
    const oldHandle = harness.cookies[0].value;
    await harness.adapter.signOut();
    await harness.adapter.beginSignIn("/new");
    const newHandle = harness.cookies.at(-1)!.value;

    await expect(
      harness.adapter.processCallback({
        url: callback(),
        correlationHandles: [oldHandle],
      }),
    ).resolves.toMatchObject({ ok: false, error: "SIGN_IN_FAILED" });
    expect(harness.provider.exchangeCalls).toBe(0);
    await expect(harness.adapter.getAccessTokenForApiRequest()).rejects.toMatchObject({
      code: "SESSION_EXPIRED",
    });

    await expect(
      harness.adapter.processCallback({
        url: callback(),
        correlationHandles: [newHandle],
      }),
    ).resolves.toMatchObject({ ok: true, destination: "/new" });
    expect(harness.provider.exchangeCalls).toBe(1);
  });

  it.each(["SIGNED_IN", "TOKEN_REFRESHED"] as const)(
    "keeps an active tombstone authoritative over provider %s",
    async (event) => {
      const harness = createHarness();
      await establishAuthenticatedSession(harness);
      await harness.adapter.signOut();
      harness.provider.emit(event, currentSession("stale-provider-token"));
      await vi.waitFor(() =>
        expect(harness.adapter.getSessionSnapshot().state).not.toBe("INITIALIZING"),
      );
      expect(harness.adapter.getSessionSnapshot()).toMatchObject({
        canRenderProtectedContent: false,
        canMakeApiRequest: false,
      });
      expect(harness.adapter.getSessionSnapshot().state).not.toBe("AUTHENTICATED");
      expect(harness.fenceState.tombstone).toBe(true);
    },
  );

  it.each(["INITIAL_SESSION", "USER_UPDATED"] as const)(
    "keeps provider %s provisional until asynchronous fence verification",
    async (event) => {
      const harness = createHarness();
      await establishFenceBinding(harness);
      harness.provider.emit(event, currentSession());
      expect(harness.adapter.getSessionSnapshot()).toMatchObject({
        state: "INITIALIZING",
        canRenderProtectedContent: false,
        canMakeApiRequest: false,
      });
      await vi.waitFor(() =>
        expect(harness.adapter.getSessionSnapshot().state).toBe("AUTHENTICATED"),
      );
    },
  );

  it("fails token preparation closed after authority state loss", async () => {
    const harness = createHarness();
    await establishAuthenticatedSession(harness, currentSession("must-not-escape"));
    const context = harness.fenceState.contextHandle;
    harness.authority.resetStateForTests();
    await expect(harness.adapter.getAccessTokenForApiRequest()).rejects.toMatchObject({
      code: "SESSION_EXPIRED",
    });
    expect(harness.fenceState.contextHandle).toBe(context);
    expect(harness.fenceState.sessionBindingHandle).toBeNull();
    expect(harness.provider.session).toBeNull();
  });

  it("reauthenticates from terminal authority loss against a fresh context", async () => {
    const harness = createHarness();
    await establishAuthenticatedSession(
      harness,
      currentSession("old-access-token"),
    );
    const oldContext = harness.fenceState.contextHandle;
    const oldBinding = harness.fenceState.sessionBindingHandle!;

    harness.authority.resetStateForTests();
    expect(harness.adapter.getSessionSnapshot()).toMatchObject({
      state: "TERMINAL_SESSION_ERROR",
      canRenderProtectedContent: false,
      canMakeApiRequest: false,
    });

    await expect(harness.adapter.beginSignIn("/runs")).resolves.toBeUndefined();
    expect(harness.adapter.getSessionSnapshot()).toMatchObject({
      state: "SIGN_IN_PENDING",
      canRenderProtectedContent: false,
      canMakeApiRequest: false,
    });
    expect(harness.provider.beginCalls).toBe(1);
    expect(harness.fenceState.contextHandle).not.toBe(oldContext);
    expect(harness.fenceState.sessionBindingHandle).toBeNull();
    expect(
      harness.authority.validateSessionBinding(
        harness.fenceState.contextHandle!,
        oldBinding,
      ),
    ).toBeNull();
    await expect(harness.adapter.getAccessTokenForApiRequest()).rejects.toMatchObject({
      code: "SESSION_EXPIRED",
    });
    expect(harness.provider.session).toBeNull();
  });

  it("keeps a lost-context callback stale after explicit reauthentication", async () => {
    const harness = createHarness();
    await establishAuthenticatedSession(harness);
    const oldContext = harness.fenceState.contextHandle;
    const oldCallbackHandle = createOpaqueAuthHandle();
    await harness.store.createPending({
      handle: oldCallbackHandle,
      flowId,
      securityPolicyVersion,
      intendedReturn: "/old",
      now: Date.now(),
    });
    await associateFenceAttempt(harness, oldCallbackHandle);

    harness.authority.resetStateForTests();
    await harness.adapter.beginSignIn("/new");
    const freshContext = harness.fenceState.contextHandle;
    expect(freshContext).not.toBe(oldContext);

    await expect(
      harness.adapter.processCallback({
        url: callback(),
        correlationHandles: [oldCallbackHandle],
      }),
    ).resolves.toMatchObject({
      ok: false,
      error: "SIGN_IN_FAILED",
      snapshot: { canRenderProtectedContent: false, canMakeApiRequest: false },
    });
    expect(harness.provider.exchangeCalls).toBe(0);
    expect(harness.fenceState.contextHandle).toBe(freshContext);
  });

  it("recovers from authority loss with a tombstone and retries reset failure", async () => {
    const harness = createHarness();
    await establishAuthenticatedSession(harness);
    await harness.adapter.signOut();
    const lostContext = harness.fenceState.contextHandle;
    expect(harness.fenceState.tombstone).toBe(true);
    harness.authority.resetStateForTests();
    expect(harness.adapter.getSessionSnapshot().state).toBe(
      "TERMINAL_SESSION_ERROR",
    );

    const writeContext = harness.fenceState.writeAuthContextHandle.bind(
      harness.fenceState,
    );
    vi.spyOn(harness.fenceState, "writeAuthContextHandle").mockImplementationOnce(
      async (handle) => {
        await writeContext(handle);
        throw new Error("cookie mutation failed");
      },
    );
    await expect(harness.adapter.beginSignIn()).rejects.toMatchObject({
      code: "TEMPORARY_PROVIDER_FAILURE",
    });
    const freshContext = harness.fenceState.contextHandle;
    expect(freshContext).not.toBe(lostContext);
    expect(harness.adapter.getSessionSnapshot()).toMatchObject({
      state: "RECOVERABLE_ERROR",
      canRenderProtectedContent: false,
      canMakeApiRequest: false,
    });
    expect(harness.fenceState.sessionBindingHandle).toBeNull();
    expect(harness.fenceState.tombstone).toBe(true);
    expect(harness.provider.beginCalls).toBe(0);

    await expect(harness.adapter.beginSignIn()).resolves.toBeUndefined();
    expect(harness.fenceState.contextHandle).toBe(freshContext);
    expect(harness.fenceState.tombstone).toBe(false);
    expect(harness.provider.beginCalls).toBe(1);
    expect(harness.adapter.getSessionSnapshot()).toMatchObject({
      state: "SIGN_IN_PENDING",
      canRenderProtectedContent: false,
      canMakeApiRequest: false,
    });
  });

  it("preserves refresh sign-out-wins and cleans late refreshed material", async () => {
    const harness = createHarness();
    await establishAuthenticatedSession(harness);
    harness.provider.refreshGate = deferred();
    const refresh = harness.adapter.refreshSession();
    await vi.waitFor(() =>
      expect(harness.adapter.getSessionSnapshot().state).toBe("REFRESH_PENDING"),
    );
    await harness.adapter.signOut();
    harness.provider.refreshGate.resolve(currentSession("late-refresh-token"));
    await expect(refresh).resolves.toMatchObject({
      state: "UNAUTHENTICATED",
      canMakeApiRequest: false,
    });
    expect(harness.provider.session).toBeNull();
    expect(harness.fenceState.tombstone).toBe(true);
  });

  it("does not restore refresh after sign-out during final fence validation", async () => {
    const harness = createHarness();
    await establishAuthenticatedSession(harness);
    harness.provider.refreshGate = deferred();
    const finalFenceStarted = deferred<void>();
    const finalFenceGate = deferred<void>();
    const resolveFence = harness.sessionFence.resolveFence.bind(harness.sessionFence);
    let heldFinalFence = false;
    vi.spyOn(harness.sessionFence, "resolveFence").mockImplementation(async () => {
      const resolution = await resolveFence();
      if (harness.provider.refreshCalls === 1 && !heldFinalFence) {
        heldFinalFence = true;
        finalFenceStarted.resolve(undefined);
        await finalFenceGate.promise;
      }
      return resolution;
    });
    const refresh = harness.adapter.refreshSession();
    await vi.waitFor(() => expect(harness.provider.refreshCalls).toBe(1));
    harness.provider.refreshGate.resolve(currentSession("late-refresh-token"));
    await finalFenceStarted.promise;

    const signOutState = new MemoryFenceState();
    signOutState.contextHandle = harness.fenceState.contextHandle;
    const signOutService = new AuthSessionFenceService(
      harness.authority,
      signOutState,
    );
    signOutService.createLocalSignOutTombstone();
    await signOutService.publishSignOut();
    finalFenceGate.resolve(undefined);

    await expect(refresh).resolves.toMatchObject({
      canRenderProtectedContent: false,
      canMakeApiRequest: false,
    });
    expect(harness.adapter.getSessionSnapshot().state).not.toBe("AUTHENTICATED");
    expect(harness.provider.session).toBeNull();
    await expect(harness.adapter.getAccessTokenForApiRequest()).rejects.toMatchObject({
      code: "SESSION_EXPIRED",
    });
  });

  it("fails an in-flight refresh closed when fence verification becomes unavailable", async () => {
    const harness = createHarness();
    await establishAuthenticatedSession(harness);
    harness.provider.refreshGate = deferred();
    const refresh = harness.adapter.refreshSession();
    await vi.waitFor(() =>
      expect(harness.adapter.getSessionSnapshot().state).toBe("REFRESH_PENDING"),
    );
    harness.authority.setAvailableForTests(false);
    harness.provider.refreshGate.resolve(currentSession("unverified-refresh-token"));
    await expect(refresh).rejects.toMatchObject({ code: "REFRESH_FAILED" });
    expect(harness.adapter.getSessionSnapshot()).toMatchObject({
      state: "TERMINAL_SESSION_ERROR",
      canRenderProtectedContent: false,
      canMakeApiRequest: false,
    });
    expect(harness.provider.session).toBeNull();
  });

  it("emits the accepted INVALID_CALLBACK envelope without prohibited material", async () => {
    const harness = createHarness({ now: 1_723_200_000_000 });
    const result = await harness.adapter.processCallback({
      url: callback("unknown_flow_1", "secret-code-123456789"),
      correlationHandles: [],
    });
    expect(result).toMatchObject({ ok: false, error: "SIGN_IN_FAILED" });
    expect(harness.securityEvents[0]).toMatchObject({
      eventName: "AUTH_INVALID_CALLBACK",
      classification: "INVALID_CALLBACK",
      occurredAt: "2024-08-09T10:40:00.000Z",
      environmentClass: "TEST",
      sourceComponent: "AUTH",
      outcome: "REJECTED",
      blockingEffect: "CALLBACK_REJECTED",
      actorType: "UNAUTHENTICATED",
      actorReference: "UNAUTHENTICATED",
      policyVersion: securityPolicyVersion,
      sessionPreserved: false,
      reasonCode: "INVALID_CALLBACK",
      redactionStatus: "SECRET_FREE",
      callbackSuccess: false,
      rejectedCallbackDestinationUsed: false,
    });
    expect(harness.securityEvents[0].requestReference).toMatch(/^[a-f0-9]{64}$/);
    expect(JSON.stringify(harness.securityEvents[0])).not.toMatch(
      /secret-code|access-token|refresh-token|verifier|cookie|sb_flow|localhost|http:|stack|email/i,
    );
  });
});
