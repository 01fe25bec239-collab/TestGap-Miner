import { describe, expect, it } from "vitest";
import {
  COMPLETED_CORRELATION_TTL_MS,
  LocalCorrelationStore,
  PENDING_CORRELATION_TTL_MS,
  completedCorrelationCookie,
  correlationCookie,
  createOpaqueCorrelationHandle,
  readCorrelationHandles,
} from "./correlation";
import { createAuthCsrfToken, validateAuthMutationRequest } from "./csrf";
import { validateIntendedReturn } from "./redirect";

const handle = "a".repeat(64);
const flowId = "flow_12345678";
const securityPolicyVersion = "test-policy@1.0";

describe("correlation and intended return", () => {
  it("creates opaque random handles without embedded state", () => {
    const first = createOpaqueCorrelationHandle();
    const second = createOpaqueCorrelationHandle();
    expect(first).toMatch(/^[a-f0-9]{64}$/);
    expect(second).not.toBe(first);
    expect(first).not.toContain("/");
  });

  it("expires pending records at no more than ten minutes", async () => {
    const store = new LocalCorrelationStore();
    const record = await store.createPending({
      handle,
      flowId,
      securityPolicyVersion,
      intendedReturn: "/runs?view=mine#new",
      now: 1_000,
    });
    expect(record.expiresAt - record.createdAt).toBe(PENDING_CORRELATION_TTL_MS);
    expect(await store.lookup(handle, flowId, record.expiresAt - 1)).not.toBeNull();
    expect(await store.lookup(handle, flowId, record.expiresAt)).toBeNull();
  });

  it("atomically consumes intended return and keeps completion exactly 120 seconds", async () => {
    const store = new LocalCorrelationStore();
    await store.createPending({
      handle,
      flowId,
      securityPolicyVersion,
      intendedReturn: "/runs",
      now: 0,
    });
    expect(await store.lookup(handle, flowId, 49)).toMatchObject({ intendedReturn: "/runs" });
    const first = await store.complete(
      handle,
      flowId,
      { userReference: "user-1" },
      50,
    );
    const second = await store.complete(
      handle,
      flowId,
      { userReference: "user-2" },
      51,
    );
    expect(first?.consumedIntendedReturn).toBe("/runs");
    expect(first?.record).toEqual({
      lifecycle: "COMPLETED_CALLBACK_CORRELATION",
      handle,
      flowId,
      securityPolicyVersion,
      outcome: { userReference: "user-1" },
      completedAt: 50,
      expiresAt: 50 + COMPLETED_CORRELATION_TTL_MS,
    });
    expect(JSON.stringify(first?.record)).not.toMatch(/intendedReturn|destination|returnPath|\/runs/);
    expect(first?.record.expiresAt).toBe(50 + COMPLETED_CORRELATION_TTL_MS);
    expect(second).toBeNull();
    expect(await store.lookup(handle, flowId, first!.record.expiresAt - 1)).toEqual(first?.record);
    expect(await store.lookup(handle, flowId, first!.record.expiresAt)).toBeNull();
  });

  it("isolates attempts and callback flows", async () => {
    const store = new LocalCorrelationStore();
    const otherHandle = "b".repeat(64);
    await store.createPending({
      handle,
      flowId,
      securityPolicyVersion,
      intendedReturn: "/one",
      now: 0,
    });
    await store.createPending({
      handle: otherHandle,
      flowId: "other_flow_123",
      securityPolicyVersion,
      intendedReturn: "/two",
      now: 0,
    });
    expect(await store.lookup(handle, "other_flow_123", 1)).toBeNull();
    expect((await store.lookup(otherHandle, "other_flow_123", 1))?.lifecycle).toBe(
      "PENDING_ATTEMPT_CORRELATION",
    );
  });

  it("cleans expired and failed attempts", async () => {
    const store = new LocalCorrelationStore();
    await store.createPending({
      handle,
      flowId,
      securityPolicyVersion,
      intendedReturn: "/",
      now: 0,
    });
    expect(await store.cleanup(PENDING_CORRELATION_TTL_MS)).toBe(1);
    await store.createPending({
      handle,
      flowId,
      securityPolicyVersion,
      intendedReturn: "/",
      now: 1_000_000,
    });
    await store.remove(handle);
    expect(await store.lookup(handle, flowId, 1_000_001)).toBeNull();
  });

  it("fails closed when the local store is unavailable", async () => {
    const store = new LocalCorrelationStore();
    store.setAvailable(false);
    await expect(store.lookup(handle, flowId, 0)).rejects.toThrow("unavailable");
  });

  it("requires a structurally valid Security policy version", async () => {
    const store = new LocalCorrelationStore();
    await expect(
      store.createPending({
        handle,
        flowId,
        securityPolicyVersion: "",
        intendedReturn: "/",
        now: 0,
      }),
    ).rejects.toThrow("Invalid Security policy version");
  });

  it("applies the frozen correlation cookie posture", () => {
    expect(correlationCookie(handle, "http://localhost:3000").options).toMatchObject({
      httpOnly: true,
      secure: false,
      sameSite: "lax",
      path: "/auth/callback",
      maxAge: 600,
    });
    expect(completedCorrelationCookie(handle, "https://app.example").options).toMatchObject({
      secure: true,
      maxAge: 120,
    });
    expect(
      readCorrelationHandles([
        { name: `testgap-auth-correlation-${handle.slice(0, 16)}`, value: handle },
        { name: "unrelated", value: "value" },
      ]),
    ).toEqual([handle]);
  });

  it.each([
    "https://evil.example",
    "//evil.example",
    "/\\evil.example",
    "/auth/callback",
    "/path@evil.example",
    "/path?next=https://evil.example",
    "/%2F%2Fevil.example",
    "/%252Fevil.example",
    "/path%0Aheader",
    "/javascript:alert(1)",
  ])("rejects unsafe intended return %s", (candidate) => {
    expect(validateIntendedReturn(candidate)).toBe("/");
  });

  it("accepts a same-origin relative intended return and falls back when absent", () => {
    expect(validateIntendedReturn("/runs?view=mine#latest")).toBe("/runs?view=mine#latest");
    expect(validateIntendedReturn()).toBe("/");
  });
});

describe("same-origin Auth mutation validation", () => {
  const origin = "https://app.example";
  const token = createAuthCsrfToken();

  function request(method: string, headers: Record<string, string> = {}) {
    return new Request(`${origin}/auth/mutation`, { method, headers });
  }

  it("accepts exact-origin mutation with anti-CSRF and same-origin metadata", () => {
    expect(
      validateAuthMutationRequest(
        request("POST", {
          origin,
          "sec-fetch-site": "same-origin",
          "x-auth-csrf": token,
        }),
        origin,
        token,
      ),
    ).toEqual({ ok: true, kind: "MUTATION" });
  });

  it("rejects wrong origin, bad metadata, and missing anti-CSRF", () => {
    expect(
      validateAuthMutationRequest(
        request("POST", { origin: "https://evil.example", "x-auth-csrf": token }),
        origin,
        token,
      ),
    ).toMatchObject({ ok: false, reason: "ORIGIN_REJECTED" });
    expect(
      validateAuthMutationRequest(
        request("POST", { origin, "sec-fetch-site": "cross-site", "x-auth-csrf": token }),
        origin,
        token,
      ),
    ).toMatchObject({ ok: false, reason: "FETCH_METADATA_REJECTED" });
    expect(validateAuthMutationRequest(request("POST", { origin }), origin, token)).toMatchObject({
      ok: false,
      reason: "CSRF_REJECTED",
    });
  });

  it.each(["GET", "HEAD", "OPTIONS"])("keeps %s side-effect-free", (method) => {
    expect(validateAuthMutationRequest(request(method), origin, token)).toEqual({
      ok: true,
      kind: "SIDE_EFFECT_FREE",
    });
  });
});
