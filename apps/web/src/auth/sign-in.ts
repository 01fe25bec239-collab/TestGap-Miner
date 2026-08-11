import {
  correlationCookie,
  createOpaqueCorrelationHandle,
  isValidSecurityPolicyVersion,
  type CorrelationCookie,
  type CorrelationStore,
} from "./correlation";
import { validateIntendedReturn } from "./redirect";
import type { AuthSessionFence } from "./session-fence";
import { AuthRuntimeError, type AuthProvider } from "./types";

export type AuthSignInDependencies = Readonly<{
  provider: AuthProvider;
  correlationStore: CorrelationStore;
  sessionFence: AuthSessionFence;
  securityPolicyVersion: string;
  applicationOrigin: string;
  setCorrelationCookie: (cookie: CorrelationCookie) => void | Promise<void>;
  deleteCorrelationCookie: (handle: string) => void | Promise<void>;
  now?: () => number;
}>;

export type PreparedAuthSignIn = Readonly<{ redirectUrl: string }>;

/** The one authoritative fence/provider/correlation/cookie sign-in composition. */
export async function prepareAuthSignIn(
  dependencies: AuthSignInDependencies,
  callbackUrl: string,
  intendedReturn?: string,
): Promise<PreparedAuthSignIn> {
  if (!isValidSecurityPolicyVersion(dependencies.securityPolicyVersion)) {
    throw new AuthRuntimeError("CONFIGURATION_UNAVAILABLE", true);
  }

  let handle: string | null = null;
  let signInAttemptReference: string | null = null;
  try {
    ({ signInAttemptReference } = await dependencies.sessionFence.prepareSignIn());
    const providerResult = await dependencies.provider.beginGitHubOAuth(callbackUrl);
    handle = createOpaqueCorrelationHandle();
    await dependencies.correlationStore.createPending({
      handle,
      flowId: providerResult.flowId,
      securityPolicyVersion: dependencies.securityPolicyVersion,
      intendedReturn: validateIntendedReturn(intendedReturn),
      now: dependencies.now?.() ?? Date.now(),
    });
    await dependencies.sessionFence.associateSignInAttempt(
      signInAttemptReference,
      handle,
    );
    await dependencies.setCorrelationCookie(
      correlationCookie(handle, dependencies.applicationOrigin),
    );
    return Object.freeze({ redirectUrl: providerResult.redirectUrl });
  } catch (error) {
    if (handle) {
      await dependencies.correlationStore.remove(handle).catch(() => undefined);
      await Promise.resolve(dependencies.deleteCorrelationCookie(handle)).catch(
        () => undefined,
      );
    }
    if (signInAttemptReference) {
      await dependencies.sessionFence
        .abandonSignInAttempt(signInAttemptReference)
        .catch(() => undefined);
    }
    throw error;
  }
}

export function authCallbackUrl(applicationOrigin: string): string {
  try {
    const origin = new URL(applicationOrigin);
    if (
      origin.origin !== applicationOrigin ||
      origin.pathname !== "/" ||
      origin.search ||
      origin.hash
    ) {
      throw new Error();
    }
    return new URL("/auth/callback", origin).toString();
  } catch {
    throw new AuthRuntimeError("CONFIGURATION_UNAVAILABLE", true);
  }
}
