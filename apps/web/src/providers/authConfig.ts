import type { CallbackRequest } from "@/auth";

/**
 * Stable across a deployment because the merged Auth runtime rejects a callback
 * whose correlation record was created under a different policy version. It is
 * presentation-independent configuration, not an Auth semantic.
 */
export const AUTH_SECURITY_POLICY_VERSION = "testgap-local-auth@1";

export const AUTH_SIGN_IN_ROUTE = "/auth/sign-in";
export const AUTH_CALLBACK_ROUTE = "/auth/callback";
export const AUTH_CSRF_COOKIE = "testgap-auth-csrf";

const LOCAL_ORIGIN = "http://localhost:3000";

/** Server-side origin of this Dashboard; never derived from request headers. */
export function applicationOrigin(): string {
  return process.env.DASHBOARD_ORIGIN || LOCAL_ORIGIN;
}

/**
 * Rebuilds the callback request in the shape `AuthAdapter.processCallback`
 * requires. The query string is relayed verbatim: the UI never inspects,
 * validates, normalizes or decides anything from callback parameters.
 */
export function callbackRequest(
  origin: string,
  callbackQuery: string,
  correlationHandles: readonly string[],
): CallbackRequest {
  const url = new URL(AUTH_CALLBACK_ROUTE, origin);
  url.search = callbackQuery.startsWith("?") ? callbackQuery.slice(1) : callbackQuery;
  return { url: url.toString(), correlationHandles };
}
