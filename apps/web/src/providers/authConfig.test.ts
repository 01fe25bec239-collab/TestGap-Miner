import { describe, expect, it, vi } from "vitest";
import {
  LocalCorrelationStore,
  createAuthAdapter,
  createOpaqueCorrelationHandle,
  type AuthProvider,
  type AuthSessionFence,
} from "@/auth";
import { AUTH_SECURITY_POLICY_VERSION, callbackRequest } from "@/providers/authConfig";
import { LocalAuthSecurityEventSink } from "@/providers/securityEventSink";

const ORIGIN = "http://localhost:3000";
const FLOW_ID = "flowabcdefgh";
const CODE = "sxHkQ2Vt7fLmA9pZ0rUw";
const USER_REFERENCE = "3f1c2d94-0a7b-4e55-9c11-6b2f8de41a03";

function callbackProvider(overrides: Partial<AuthProvider> = {}): AuthProvider {
  return {
    beginGitHubOAuth: async () => ({ redirectUrl: "https://provider.test/authorize", flowId: FLOW_ID }),
    exchangeCode: async () => ({
      session: {
        userReference: USER_REFERENCE,
        accessToken: "provider-issued-value",
        expiresAt: Date.now() + 600_000,
      },
      prepareSessionCommit: async () => {},
      commitSession: async () => {},
      discardSession: async () => {},
    }),
    getSession: async () => null,
    validateCurrentUser: async () => null,
    validatePreExistingSession: async () => null,
    refresh: async () => {
      throw new Error("unused");
    },
    signOutLocal: async () => {},
    onSessionChange: () => () => {},
    ...overrides,
  };
}

function callbackFence(): AuthSessionFence {
  const references = {
    signInAttemptReference: "a".repeat(64),
    callbackFlowReference: "b".repeat(64),
    correlationReference: "c".repeat(64),
  };
  return {
    prepareSignIn: async () => ({ signInAttemptReference: references.signInAttemptReference }),
    associateSignInAttempt: async () => references,
    abandonSignInAttempt: async () => {},
    abandonCallback: async () => {},
    validateCallback: async () => ({ eligible: true, references }),
    establishSession: async () => ({ eligible: true, references }),
    rollbackSessionEstablishment: async () => {},
    resolveFence: async () => ({ eligible: true, references }),
    createLocalSignOutTombstone: () => {},
    publishSignOut: async () => {},
    cleanupStaleSessionMaterial: async () => {},
    subscribeToFenceChanges: () => () => {},
  };
}

function callbackRuntime(
  store: LocalCorrelationStore,
  overrides: Partial<AuthProvider> = {},
  sink = new LocalAuthSecurityEventSink(),
) {
  const clearCallbackUrl = vi.fn();
  const emitSecurityEvent = vi.fn(sink.emit);
  const adapter = createAuthAdapter({
    provider: callbackProvider(overrides),
    correlationStore: store,
    sessionFence: callbackFence(),
    securityPolicyVersion: AUTH_SECURITY_POLICY_VERSION,
    applicationOrigin: ORIGIN,
    environmentClass: "LOCAL_DEVELOPMENT",
    redirectToProvider: () => {},
    setCorrelationCookie: () => {},
    deleteCorrelationCookie: () => {},
    clearCallbackUrl,
    emitSecurityEvent,
  });
  return { adapter, clearCallbackUrl, emitSecurityEvent, sink };
}

async function pendingHandle(store: LocalCorrelationStore, intendedReturn = "/") {
  const handle = createOpaqueCorrelationHandle();
  await store.createPending({
    handle,
    flowId: FLOW_ID,
    securityPolicyVersion: AUTH_SECURITY_POLICY_VERSION,
    intendedReturn,
    now: Date.now(),
  });
  return handle;
}

describe("callback request relay", () => {
  it("rebuilds the callback request without altering provider parameters", () => {
    const request = callbackRequest(ORIGIN, "?code=a.b~c&sb_flow_id=x&code=second", ["handle"]);
    const url = new URL(request.url);

    expect(url.origin).toBe(ORIGIN);
    expect(url.pathname).toBe("/auth/callback");
    expect(url.searchParams.getAll("code")).toEqual(["a.b~c", "second"]);
    expect(request.correlationHandles).toEqual(["handle"]);
  });

  it("accepts a query string that has already lost its leading separator", () => {
    expect(callbackRequest(ORIGIN, "sb_flow_id=x", []).url).toBe(
      "http://localhost:3000/auth/callback?sb_flow_id=x",
    );
  });
});

describe("callback processing through the Auth adapter", () => {
  it("establishes the session and returns the destination Auth authorized", async () => {
    const store = new LocalCorrelationStore();
    const handle = await pendingHandle(store, "/");
    const { adapter, clearCallbackUrl } = callbackRuntime(store);

    const result = await adapter.processCallback(
      callbackRequest(ORIGIN, `?code=${CODE}&sb_flow_id=${FLOW_ID}`, [handle]),
    );

    expect(result.ok).toBe(true);
    expect(result.destination).toBe("/");
    expect(result.snapshot.state).toBe("AUTHENTICATED");
    expect(result.snapshot.canRenderProtectedContent).toBe(true);
    expect(clearCallbackUrl).toHaveBeenCalled();
  });

  it("reports only the public failure classification for a rejected callback", async () => {
    const store = new LocalCorrelationStore();
    const { adapter, emitSecurityEvent, sink } = callbackRuntime(store);

    const result = await adapter.processCallback(
      callbackRequest(ORIGIN, `?code=${CODE}&sb_flow_id=${FLOW_ID}`, []),
    );

    expect(result.ok).toBe(false);
    expect(result).not.toHaveProperty("duplicate");
    if (!result.ok) {
      expect(result.error).toBe("SIGN_IN_FAILED");
      expect(result.destination).toBeNull();
    }
    expect(result.snapshot.canRenderProtectedContent).toBe(false);
    expect(emitSecurityEvent).toHaveBeenCalledWith(
      expect.objectContaining({ callbackSuccess: false, sessionPreserved: false }),
    );
    expect(sink.snapshot()).toEqual([
      expect.objectContaining({
        classification: "INVALID_CALLBACK",
        reasonCode: "INVALID_CALLBACK",
        redactionStatus: "SECRET_FREE",
      }),
    ]);
    expect(JSON.stringify(sink.snapshot())).not.toMatch(
      /accessToken|refreshToken|authorization|providerSession|oauthCode|pkce|verifier|clientSecret/i,
    );
  });

  it("keeps a failed Security-event handoff observable", async () => {
    const sink = new LocalAuthSecurityEventSink();
    vi.spyOn(sink, "emit").mockImplementation(() => {
      throw new Error("sink unavailable");
    });
    const { adapter } = callbackRuntime(new LocalCorrelationStore(), {}, sink);

    await expect(
      adapter.processCallback(
        callbackRequest(ORIGIN, `?code=${CODE}&sb_flow_id=${FLOW_ID}`, []),
      ),
    ).rejects.toMatchObject({ name: "SecurityEventSinkFailure" });
  });

  it("keeps duplicated provider parameters rejectable by the Auth runtime", async () => {
    const store = new LocalCorrelationStore();
    const handle = await pendingHandle(store);
    const { adapter } = callbackRuntime(store);

    const result = await adapter.processCallback(
      callbackRequest(ORIGIN, `?code=${CODE}&code=${CODE}&sb_flow_id=${FLOW_ID}`, [handle]),
    );

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toBe("SIGN_IN_FAILED");
  });
});
