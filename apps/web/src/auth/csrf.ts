const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);
const MUTATION_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export type AuthMutationValidation =
  | Readonly<{ ok: true; kind: "MUTATION" | "SIDE_EFFECT_FREE" }>
  | Readonly<{
      ok: false;
      reason: "METHOD_NOT_ALLOWED" | "ORIGIN_REJECTED" | "FETCH_METADATA_REJECTED" | "CSRF_REJECTED";
    }>;

export function createAuthCsrfToken(): string {
  const bytes = new Uint8Array(32);
  globalThis.crypto.getRandomValues(bytes);
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

export function validateAuthMutationRequest(
  request: Pick<Request, "method" | "headers">,
  approvedOrigin: string,
  expectedCsrfToken: string,
): AuthMutationValidation {
  const method = request.method.toUpperCase();
  if (SAFE_METHODS.has(method)) return { ok: true, kind: "SIDE_EFFECT_FREE" };
  if (!MUTATION_METHODS.has(method)) return { ok: false, reason: "METHOD_NOT_ALLOWED" };
  if (request.headers.get("origin") !== approvedOrigin) {
    return { ok: false, reason: "ORIGIN_REJECTED" };
  }

  const fetchSite = request.headers.get("sec-fetch-site");
  if (fetchSite && fetchSite !== "same-origin") {
    return { ok: false, reason: "FETCH_METADATA_REJECTED" };
  }

  const suppliedToken = request.headers.get("x-auth-csrf");
  if (!suppliedToken || !constantTimeEqual(suppliedToken, expectedCsrfToken)) {
    return { ok: false, reason: "CSRF_REJECTED" };
  }
  return { ok: true, kind: "MUTATION" };
}

function constantTimeEqual(left: string, right: string): boolean {
  const length = Math.max(left.length, right.length);
  let mismatch = left.length ^ right.length;
  for (let index = 0; index < length; index += 1) {
    mismatch |= (left.charCodeAt(index) || 0) ^ (right.charCodeAt(index) || 0);
  }
  return mismatch === 0;
}
