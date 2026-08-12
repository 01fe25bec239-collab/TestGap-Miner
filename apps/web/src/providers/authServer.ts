import { cookies } from "next/headers";
import {
  AuthFenceCookieStateStore,
  AuthSessionFenceHostService,
  AuthSessionFenceService,
  correlationCookie,
  createAuthAdapter,
  createSupabaseAuthProvider,
  getSharedLocalProcessAuthSynchronizationAuthority,
  readCorrelationHandles,
  type AuthRuntimeDependencies,
} from "@/auth";
import { getSharedLocalProcessCorrelationStore } from "@/auth/correlation";
import {
  createAuthCallbackProvider,
  createAuthServerClient,
} from "@/auth/supabase-server";
import {
  AUTH_CALLBACK_ROUTE,
  AUTH_SECURITY_POLICY_VERSION,
  applicationOrigin,
  callbackRequest,
} from "./authConfig";
import { localAuthSecurityEventSink } from "./securityEventSink";

type CookieWriter = Awaited<ReturnType<typeof cookies>>;

function correlationDependencies(
  origin: string,
  cookieStore: CookieWriter,
): Pick<
  AuthRuntimeDependencies,
  | "correlationStore"
  | "securityPolicyVersion"
  | "applicationOrigin"
  | "setCorrelationCookie"
  | "deleteCorrelationCookie"
  | "clearCallbackUrl"
> {
  return {
    correlationStore: getSharedLocalProcessCorrelationStore({
      applicationOrigin: origin,
      environmentClass: "LOCAL_DEVELOPMENT",
    }),
    securityPolicyVersion: AUTH_SECURITY_POLICY_VERSION,
    applicationOrigin: origin,
    setCorrelationCookie: (cookie) => {
      cookieStore.set(cookie.name, cookie.value, cookie.options);
    },
    deleteCorrelationCookie: (handle) => {
      cookieStore.delete({
        name: correlationCookie(handle, origin).name,
        path: AUTH_CALLBACK_ROUTE,
      });
    },
    // The browser address bar is cleared by the callback view; the server has no
    // browser history to rewrite.
    clearCallbackUrl: () => {},
  };
}

function sessionFence(origin: string, cookieStore: CookieWriter) {
  return new AuthSessionFenceService(
    getSharedLocalProcessAuthSynchronizationAuthority({
      applicationOrigin: origin,
      environmentClass: "LOCAL_DEVELOPMENT",
    }),
    new AuthFenceCookieStateStore(origin, {
      getAll: () => cookieStore.getAll(),
      set: (cookie) => {
        cookieStore.set(cookie.name, cookie.value, cookie.options);
      },
    }),
  );
}

export async function createAuthSessionFenceHost() {
  const origin = applicationOrigin();
  const cookieStore = await cookies();
  const provider = createSupabaseAuthProvider(await createAuthServerClient(origin, () => {}));
  return new AuthSessionFenceHostService({
    ...correlationDependencies(origin, cookieStore),
    provider,
    sessionFence: sessionFence(origin, cookieStore),
  });
}

export type CallbackOutcome = Readonly<{ ok: boolean; destination: string | null }>;

/**
 * Delegates every callback semantic — parameter validation, PKCE, OAuth state,
 * correlation, code exchange, intended-return validation and session
 * establishment — to `AuthAdapter.processCallback`, and returns only the
 * presentation-safe outcome.
 */
export async function processAuthCallback(callbackQuery: string): Promise<CallbackOutcome> {
  const origin = applicationOrigin();
  const cookieStore = await cookies();
  const provider = await createAuthCallbackProvider(origin, () => {});
  const adapter = createAuthAdapter({
    ...correlationDependencies(origin, cookieStore),
    provider,
    sessionFence: sessionFence(origin, cookieStore),
    environmentClass: "LOCAL_DEVELOPMENT",
    redirectToProvider: () => {},
    emitSecurityEvent: localAuthSecurityEventSink.emit,
  });

  const result = await adapter.processCallback(
    callbackRequest(origin, callbackQuery, readCorrelationHandles(cookieStore.getAll())),
  );
  return { ok: result.ok, destination: result.destination };
}
