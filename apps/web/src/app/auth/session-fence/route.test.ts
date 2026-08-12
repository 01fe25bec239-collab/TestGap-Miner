import { beforeEach, describe, expect, it, vi } from "vitest";
import { AUTH_SESSION_FENCE_PATH } from "@/auth";

const mocks = vi.hoisted(() => ({
  getCookie: vi.fn(),
  createHost: vi.fn(),
  prepareSignIn: vi.fn(),
  publishSignOut: vi.fn(),
  resolveSession: vi.fn(),
}));

vi.mock("next/headers", () => ({
  cookies: async () => ({ get: mocks.getCookie }),
}));

vi.mock("@/providers/authServer", () => ({
  createAuthSessionFenceHost: mocks.createHost,
}));

import { POST } from "./route";

const ORIGIN = "http://localhost:3000";
const CSRF_TOKEN = "csrf-token";
const REJECTED_REQUESTS: readonly {
  headers: Record<string, string>;
  description: string;
}[] = [
  { headers: { origin: "https://evil.test" }, description: "wrong origin" },
  {
    headers: { "sec-fetch-site": "cross-site" },
    description: "cross-site Fetch Metadata",
  },
  { headers: { "x-auth-csrf": "wrong-token" }, description: "wrong CSRF token" },
];

function request(
  body: unknown,
  headers: Record<string, string> = {},
) {
  return new Request(`${ORIGIN}${AUTH_SESSION_FENCE_PATH}`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      origin: ORIGIN,
      "sec-fetch-site": "same-origin",
      "x-auth-csrf": CSRF_TOKEN,
      ...headers,
    },
    body: typeof body === "string" ? body : JSON.stringify(body),
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  mocks.getCookie.mockReturnValue({ value: CSRF_TOKEN });
  mocks.prepareSignIn.mockResolvedValue({ redirectUrl: "https://github.test/authorize" });
  mocks.publishSignOut.mockResolvedValue(undefined);
  mocks.resolveSession.mockResolvedValue({
    state: "AUTHENTICATED",
    userReference: "user-reference",
  });
  mocks.createHost.mockResolvedValue({
    prepareSignIn: mocks.prepareSignIn,
    publishSignOut: mocks.publishSignOut,
    resolveSession: mocks.resolveSession,
  });
});

describe(`POST ${AUTH_SESSION_FENCE_PATH}`, () => {
  it.each([
    ["PREPARE_SIGN_IN", "prepareSignIn", { redirectUrl: "https://github.test/authorize" }],
    ["PUBLISH_SIGN_OUT", "publishSignOut", { ok: true }],
    [
      "RESOLVE_SESSION",
      "resolveSession",
      { state: "AUTHENTICATED", userReference: "user-reference" },
    ],
  ] as const)("dispatches only %s", async (operation, method, expected) => {
    const response = await POST(request({ operation }));

    expect(response.status).toBe(200);
    expect(response.headers.get("cache-control")).toBe("private, no-store");
    expect(await response.json()).toEqual(expected);
    expect(mocks[method]).toHaveBeenCalledTimes(1);
  });

  it("rejects malformed and unsupported operations without dispatch", async () => {
    for (const body of ["not-json", { operation: "DELETE_EVERYTHING" }, { operation: "RESOLVE_SESSION", extra: true }]) {
      const response = await POST(request(body));
      expect(response.status).toBe(400);
      expect(await response.json()).toEqual({ error: "AUTH_REQUEST_FAILED" });
    }

    expect(mocks.prepareSignIn).not.toHaveBeenCalled();
    expect(mocks.publishSignOut).not.toHaveBeenCalled();
    expect(mocks.resolveSession).not.toHaveBeenCalled();
  });

  it.each(REJECTED_REQUESTS)(
    "rejects $description",
    async ({ headers }) => {
      const response = await POST(request({ operation: "RESOLVE_SESSION" }, headers));

      expect(response.status).toBe(403);
      expect(response.headers.get("cache-control")).toBe("private, no-store");
      expect(mocks.createHost).not.toHaveBeenCalled();
    },
  );

  it("returns only the Auth-owned safe response fields", async () => {
    const prepare = await POST(request({ operation: "PREPARE_SIGN_IN" }));
    const resolve = await POST(request({ operation: "RESOLVE_SESSION" }));
    const serialized = JSON.stringify([await prepare.json(), await resolve.json()]);

    expect(serialized).not.toMatch(
      /contextHandle|bindingHandle|generation|AuthFenceEventReferences|signInAttemptReference|accessToken|refreshToken|providerSession|authorizationCode|pkce|verifier/i,
    );
  });
});
