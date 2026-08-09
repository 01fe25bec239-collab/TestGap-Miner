import {
  completedCorrelationCookie,
  correlationCookie,
  createOpaqueCorrelationHandle,
  isValidSecurityPolicyVersion,
  type CorrelationCookie,
  type CorrelationRecord,
  type CorrelationStore,
} from "./correlation";
import { DEFAULT_AUTH_DESTINATION, validateIntendedReturn } from "./redirect";
import { AuthStateMachine } from "./state-machine";
import type {
  AuthAdapter,
  AuthSecurityEvent,
  AuthSessionSnapshot,
  CallbackRequest,
  CallbackResult,
  InternalCallbackError,
  ProviderSession,
  PublicAuthError,
  SignOutResult,
} from "./types";
import { AuthRuntimeError } from "./types";

const FLOW_ID_PARAMETER = "sb_flow_id";
const CALLBACK_CODE = /^[A-Za-z0-9._~-]{16,2048}$/;
const FLOW_ID = /^[A-Za-z0-9_-]{8,64}$/;
const PUBLIC_CALLBACK_FAILURES = new Set<InternalCallbackError>([
  "INVALID_CALLBACK",
  "STATE_VALIDATION_FAILED",
  "PKCE_VALIDATION_FAILED",
  "SESSION_EXCHANGE_FAILED",
]);

class SecurityEventSinkFailure extends Error {
  constructor() {
    super("Authentication security event emission failed");
    this.name = "SecurityEventSinkFailure";
  }
}

export type AuthRuntimeDependencies = Readonly<{
  provider: import("./types").AuthProvider;
  correlationStore: CorrelationStore;
  securityPolicyVersion: string;
  applicationOrigin: string;
  redirectToProvider: (url: string) => void | Promise<void>;
  setCorrelationCookie: (cookie: CorrelationCookie) => void | Promise<void>;
  deleteCorrelationCookie: (handle: string) => void | Promise<void>;
  clearCallbackUrl: () => void | Promise<void>;
  emitSecurityEvent: (event: AuthSecurityEvent) => void | Promise<void>;
  now?: () => number;
}>;

export function createAuthAdapter(dependencies: AuthRuntimeDependencies): AuthAdapter {
  return new AuthRuntime(dependencies);
}

class AuthRuntime implements AuthAdapter {
  #machine = new AuthStateMachine();
  #beginPromise: Promise<void> | null = null;
  #refreshPromise: Promise<AuthSessionSnapshot> | null = null;
  #signOutPromise: Promise<SignOutResult> | null = null;
  #callbackProcessingCount = 0;
  #callbackFlights = new Map<string, Promise<CallbackResult>>();
  #operationEpoch = 0;
  #callbackUrl: string;

  constructor(private readonly dependencies: AuthRuntimeDependencies) {
    if (!isValidSecurityPolicyVersion(dependencies.securityPolicyVersion)) {
      throw new AuthRuntimeError("CONFIGURATION_UNAVAILABLE", true);
    }
    this.#callbackUrl = callbackUrlForOrigin(dependencies.applicationOrigin);
    dependencies.provider.onSessionChange((event, session) => {
      if (this.#callbackProcessingCount || this.#refreshPromise || this.#signOutPromise) return;
      try {
        if (event === "SIGNED_OUT" || !session) {
          this.#machine.transition("UNAUTHENTICATED");
        } else {
          this.#machine.transition("AUTHENTICATED", {
            userReference: session.userReference,
          });
        }
      } catch {
        // Invalid provider event ordering already moved the machine fail closed.
      }
    });
  }

  beginSignIn(intendedReturn?: string): Promise<void> {
    if (this.#beginPromise) return this.#beginPromise;
    const state = this.#machine.snapshot.state;
    if (state !== "UNAUTHENTICATED" && state !== "RECOVERABLE_ERROR") {
      return Promise.reject(new AuthRuntimeError("TEMPORARY_PROVIDER_FAILURE", true));
    }

    this.#beginPromise = this.#beginSignIn(intendedReturn).finally(() => {
      this.#beginPromise = null;
    });
    return this.#beginPromise;
  }

  async #beginSignIn(intendedReturn?: string) {
    this.#machine.transition("SIGN_IN_PENDING");
    let handle: string | null = null;
    let redirectUrl: string;
    try {
      const providerResult = await this.dependencies.provider.beginGitHubOAuth(
        this.#callbackUrl,
      );
      handle = createOpaqueCorrelationHandle();
      await this.dependencies.correlationStore.createPending({
        handle,
        flowId: providerResult.flowId,
        securityPolicyVersion: this.dependencies.securityPolicyVersion,
        intendedReturn: validateIntendedReturn(intendedReturn),
        now: this.#now(),
      });
      await this.dependencies.setCorrelationCookie(
        correlationCookie(handle, this.dependencies.applicationOrigin),
      );
      redirectUrl = providerResult.redirectUrl;
    } catch (error) {
      if (handle) {
        await this.dependencies.correlationStore.remove(handle).catch(() => undefined);
        await Promise.resolve(this.dependencies.deleteCorrelationCookie(handle)).catch(() => undefined);
      }
      this.#machine.transition("RECOVERABLE_ERROR");
      throw safeRuntimeError(error, "TEMPORARY_PROVIDER_FAILURE");
    }
    await this.dependencies.redirectToProvider(redirectUrl);
  }

  async processCallback(request: CallbackRequest): Promise<CallbackResult> {
    this.#callbackProcessingCount += 1;
    const preExistingSession = await this.dependencies.provider.getSession().catch(() => null);
    try {
      this.#machine.transition("CALLBACK_PROCESSING");
      const parsed = parseCallback(request.url, this.#callbackUrl);
      const match = parsed.flowId
        ? await this.#findCorrelation(request.correlationHandles, parsed.flowId)
        : null;

      if (!parsed.ok) {
        if (match?.record.lifecycle === "PENDING_ATTEMPT_CORRELATION") {
          await this.#discardAttempt(match.handle);
        }
        return await this.#callbackFailure(parsed.error, preExistingSession);
      }

      if (!match) {
        return await this.#callbackFailure("INVALID_CALLBACK", preExistingSession);
      }

      if (match.record.securityPolicyVersion !== this.dependencies.securityPolicyVersion) {
        if (match.record.lifecycle === "PENDING_ATTEMPT_CORRELATION") {
          await this.#discardAttempt(match.handle);
        }
        return await this.#callbackFailure("INVALID_CALLBACK", preExistingSession);
      }

      if (match.record.lifecycle === "COMPLETED_CALLBACK_CORRELATION") {
        return await this.#completedCallback(match.record, preExistingSession);
      }

      const active = this.#callbackFlights.get(match.handle);
      if (active) return await active;

      const current = await this.dependencies.correlationStore.lookup(
        match.handle,
        parsed.flowId,
        this.#now(),
      );
      if (!current) {
        return await this.#callbackFailure("INVALID_CALLBACK", preExistingSession);
      }
      if (current.securityPolicyVersion !== this.dependencies.securityPolicyVersion) {
        if (current.lifecycle === "PENDING_ATTEMPT_CORRELATION") {
          await this.#discardAttempt(match.handle);
        }
        return await this.#callbackFailure("INVALID_CALLBACK", preExistingSession);
      }
      if (current.lifecycle === "COMPLETED_CALLBACK_CORRELATION") {
        return await this.#completedCallback(current, preExistingSession);
      }

      const concurrentlyStarted = this.#callbackFlights.get(match.handle);
      if (concurrentlyStarted) return await concurrentlyStarted;

      const flight = this.#exchangeCallback(
        parsed.code,
        parsed.flowId,
        match.handle,
        preExistingSession,
      );
      this.#callbackFlights.set(match.handle, flight);
      try {
        return await flight;
      } finally {
        if (this.#callbackFlights.get(match.handle) === flight) {
          this.#callbackFlights.delete(match.handle);
        }
      }
    } catch (error) {
      if (error instanceof SecurityEventSinkFailure) throw error;
      return await this.#callbackFailure("INVALID_CALLBACK", preExistingSession);
    } finally {
      this.#callbackProcessingCount -= 1;
    }
  }

  async #exchangeCallback(
    code: string,
    flowId: string,
    handle: string,
    preExistingSession: ProviderSession | null,
  ): Promise<CallbackResult> {
    this.#machine.transition("CALLBACK_PROCESSING");
    let exchange: Awaited<ReturnType<AuthRuntimeDependencies["provider"]["exchangeCode"]>>;
    try {
      exchange = await this.dependencies.provider.exchangeCode(code, flowId);
    } catch (error) {
      await this.#discardAttempt(handle);
      const internalError =
        error instanceof AuthRuntimeError &&
        PUBLIC_CALLBACK_FAILURES.has(error.code as InternalCallbackError)
          ? (error.code as InternalCallbackError)
          : "SESSION_EXCHANGE_FAILED";
      return await this.#callbackFailure(internalError, preExistingSession);
    }

    try {
      await exchange.prepareSessionCommit();
    } catch {
      await exchange.discardSession();
      await this.#discardAttempt(handle);
      return await this.#callbackFailure("SESSION_EXCHANGE_FAILED", preExistingSession);
    }

    let completion;
    try {
      completion = await this.dependencies.correlationStore.complete(
        handle,
        flowId,
        { userReference: exchange.session.userReference },
        this.#now(),
      );
    } catch {
      await exchange.discardSession();
      await this.#discardAttempt(handle).catch(() => undefined);
      return await this.#callbackFailure("INVALID_CALLBACK", preExistingSession);
    }
    if (!completion) {
      await exchange.discardSession();
      await this.#discardAttempt(handle);
      return await this.#callbackFailure("INVALID_CALLBACK", preExistingSession);
    }

    try {
      await this.dependencies.setCorrelationCookie(
        completedCorrelationCookie(handle, this.dependencies.applicationOrigin),
      );
      await exchange.commitSession();
      this.#machine.transition("AUTHENTICATED", {
        userReference: exchange.session.userReference,
      });
      await Promise.resolve(this.dependencies.clearCallbackUrl()).catch(() => undefined);
      return {
        ok: true,
        snapshot: this.#machine.snapshot,
        destination: completion.consumedIntendedReturn,
        duplicate: false,
      };
    } catch {
      await exchange.discardSession();
      return await this.#callbackFailure("SESSION_EXCHANGE_FAILED", preExistingSession);
    }
  }

  async #completedCallback(
    record: Extract<CorrelationRecord, { lifecycle: "COMPLETED_CALLBACK_CORRELATION" }>,
    preExistingSession: ProviderSession | null,
  ): Promise<CallbackResult> {
    this.#machine.transition("CALLBACK_PROCESSING");
    const validated = await this.#validatePreservedSession(preExistingSession);
    if (validated?.userReference !== record.outcome.userReference) {
      return await this.#callbackFailure("INVALID_CALLBACK", preExistingSession);
    }
    this.#machine.transition("AUTHENTICATED", {
      userReference: record.outcome.userReference,
    });
    await this.dependencies.clearCallbackUrl();
    return {
      ok: true,
      snapshot: this.#machine.snapshot,
      destination: DEFAULT_AUTH_DESTINATION,
      duplicate: true,
    };
  }

  getSessionSnapshot(): AuthSessionSnapshot {
    return this.#machine.snapshot;
  }

  subscribeToSessionChanges(
    listener: (snapshot: AuthSessionSnapshot) => void,
  ): () => void {
    return this.#machine.subscribe(listener);
  }

  async getAccessTokenForApiRequest(): Promise<string> {
    if (this.#refreshPromise) await this.#refreshPromise;
    if (this.#machine.snapshot.state !== "AUTHENTICATED") {
      throw new AuthRuntimeError("SESSION_EXPIRED");
    }

    let session = await this.dependencies.provider.getSession();
    if (!session) {
      this.#machine.transition("TERMINAL_SESSION_ERROR");
      throw new AuthRuntimeError("SESSION_EXPIRED");
    }

    const remaining = session.expiresAt - this.#now();
    if (remaining <= 0) {
      await this.#refresh("UNPROVEN_CREDENTIAL");
      session = await this.dependencies.provider.getSession();
    } else if (remaining <= 60_000) {
      await this.#refresh("PROVEN_CREDENTIAL");
      session = await this.dependencies.provider.getSession();
    }

    if (!session || this.#machine.snapshot.state !== "AUTHENTICATED") {
      throw new AuthRuntimeError("SESSION_EXPIRED");
    }
    return session.accessToken;
  }

  refreshSession(): Promise<AuthSessionSnapshot> {
    return this.#refresh();
  }

  #refresh(forcedMode?: import("./types").RefreshMode): Promise<AuthSessionSnapshot> {
    if (this.#refreshPromise) return this.#refreshPromise;
    this.#refreshPromise = this.#performRefresh(forcedMode).finally(() => {
      this.#refreshPromise = null;
    });
    return this.#refreshPromise;
  }

  async #performRefresh(
    forcedMode?: import("./types").RefreshMode,
  ): Promise<AuthSessionSnapshot> {
    if (this.#machine.snapshot.state !== "AUTHENTICATED") {
      throw new AuthRuntimeError("SESSION_EXPIRED");
    }

    const session = await this.dependencies.provider.getSession();
    const mode =
      forcedMode ??
      (session && session.expiresAt > this.#now()
        ? "PROVEN_CREDENTIAL"
        : "UNPROVEN_CREDENTIAL");
    const epoch = this.#operationEpoch;
    this.#machine.transition("REFRESH_PENDING", {
      refreshMode: mode,
      userReference: session?.userReference,
    });

    return this.dependencies.provider
      .refresh()
      .then((refreshed) => {
        if (epoch !== this.#operationEpoch) return this.#machine.snapshot;
        return this.#machine.transition("AUTHENTICATED", {
          userReference: refreshed.userReference,
        });
      })
      .catch((error) => {
        const recoverable = error instanceof AuthRuntimeError && error.recoverable;
        this.#machine.transition(recoverable ? "RECOVERABLE_ERROR" : "TERMINAL_SESSION_ERROR");
        throw safeRuntimeError(error, recoverable ? "TEMPORARY_PROVIDER_FAILURE" : "REFRESH_FAILED");
      });
  }

  signOut(): Promise<SignOutResult> {
    if (this.#signOutPromise) return this.#signOutPromise;
    if (this.#machine.snapshot.state === "UNAUTHENTICATED") {
      return Promise.resolve({ ok: true, error: null, destination: DEFAULT_AUTH_DESTINATION });
    }

    this.#operationEpoch += 1;
    this.#machine.transition("SIGN_OUT_PENDING");
    this.#signOutPromise = this.dependencies.provider
      .signOutLocal()
      .then(() => ({ ok: true, error: null, destination: DEFAULT_AUTH_DESTINATION }) as const)
      .catch(
        () =>
          ({
            ok: false,
            error: "SIGN_OUT_FAILED",
            destination: DEFAULT_AUTH_DESTINATION,
          }) as const,
      )
      .then((result) => {
        this.#machine.transition("UNAUTHENTICATED");
        return result;
      })
      .finally(() => {
        this.#signOutPromise = null;
      });
    return this.#signOutPromise;
  }

  async #findCorrelation(handles: readonly string[], flowId: string) {
    let match: { handle: string; record: CorrelationRecord } | null = null;
    for (const handle of new Set(handles)) {
      const record = await this.dependencies.correlationStore.lookup(handle, flowId, this.#now());
      if (!record) continue;
      if (match) return null;
      match = { handle, record };
    }
    return match;
  }

  async #discardAttempt(handle: string) {
    await this.dependencies.correlationStore.remove(handle);
    await this.dependencies.deleteCorrelationCookie(handle);
  }

  async #callbackFailure(
    internalError: InternalCallbackError | "PROVIDER_DENIED" | "USER_CANCELLED",
    preExistingSession: ProviderSession | null,
  ): Promise<CallbackResult> {
    await Promise.resolve(this.dependencies.clearCallbackUrl()).catch(() => undefined);
    const preserved = await this.#validatePreservedSession(preExistingSession);
    if (preserved) {
      this.#machine.transition("AUTHENTICATED", { userReference: preserved.userReference });
      const result = {
        ok: false,
        error: publicCallbackError(internalError),
        snapshot: this.#machine.snapshot,
        destination: DEFAULT_AUTH_DESTINATION,
      } as const;
      await this.#emitSecurityEvent(internalError, true);
      return result;
    }

    const next =
      internalError === "PROVIDER_DENIED" || internalError === "USER_CANCELLED"
        ? "UNAUTHENTICATED"
        : "TERMINAL_SESSION_ERROR";
    this.#machine.transition(next);
    const result = {
      ok: false,
      error: publicCallbackError(internalError),
      snapshot: this.#machine.snapshot,
      destination: null,
    } as const;
    await this.#emitSecurityEvent(internalError, false);
    return result;
  }

  async #validatePreservedSession(preExisting: ProviderSession | null) {
    if (!preExisting) return null;
    const validated = await this.dependencies.provider
      .validatePreExistingSession(preExisting)
      .catch(() => null);
    return validated?.userReference === preExisting.userReference ? validated : null;
  }

  async #emitSecurityEvent(
    classification: InternalCallbackError | "PROVIDER_DENIED" | "USER_CANCELLED",
    sessionPreserved: boolean,
  ) {
    if (!PUBLIC_CALLBACK_FAILURES.has(classification as InternalCallbackError)) return;
    try {
      await this.dependencies.emitSecurityEvent(
        Object.freeze({
          classification: classification as InternalCallbackError,
          sessionPreserved,
          callbackSuccess: false,
          rejectedCallbackDestinationUsed: false,
        }),
      );
    } catch {
      throw new SecurityEventSinkFailure();
    }
  }

  #now() {
    return this.dependencies.now?.() ?? Date.now();
  }
}

function parseCallback(
  requestUrl: string,
  approvedCallbackUrl: string,
):
  | { ok: true; code: string; flowId: string }
  | {
      ok: false;
      flowId: string | null;
      error: InternalCallbackError | "PROVIDER_DENIED" | "USER_CANCELLED";
    } {
  try {
    const request = new URL(requestUrl);
    const approved = new URL(approvedCallbackUrl);
    if (
      request.origin !== approved.origin ||
      request.pathname !== approved.pathname ||
      request.hash ||
      request.searchParams.getAll(FLOW_ID_PARAMETER).length !== 1
    ) {
      return { ok: false, flowId: null, error: "INVALID_CALLBACK" };
    }

    const flowId = request.searchParams.get(FLOW_ID_PARAMETER);
    if (!flowId || !FLOW_ID.test(flowId)) {
      return { ok: false, flowId: null, error: "INVALID_CALLBACK" };
    }

    if (request.searchParams.has("error")) {
      return {
        ok: false,
        flowId,
        error:
          request.searchParams.get("error") === "access_denied"
            ? "PROVIDER_DENIED"
            : "INVALID_CALLBACK",
      };
    }

    const codes = request.searchParams.getAll("code");
    if (codes.length !== 1 || !CALLBACK_CODE.test(codes[0])) {
      return { ok: false, flowId, error: "INVALID_CALLBACK" };
    }
    return { ok: true, code: codes[0], flowId };
  } catch {
    return { ok: false, flowId: null, error: "INVALID_CALLBACK" };
  }
}

function publicCallbackError(
  error: InternalCallbackError | "PROVIDER_DENIED" | "USER_CANCELLED",
): PublicAuthError {
  return PUBLIC_CALLBACK_FAILURES.has(error as InternalCallbackError)
    ? "SIGN_IN_FAILED"
    : (error as "PROVIDER_DENIED" | "USER_CANCELLED");
}

function safeRuntimeError(error: unknown, fallback: PublicAuthError): AuthRuntimeError {
  return error instanceof AuthRuntimeError ? error : new AuthRuntimeError(fallback, true);
}

function callbackUrlForOrigin(origin: string): string {
  try {
    const parsed = new URL(origin);
    if (parsed.origin !== origin || parsed.pathname !== "/" || parsed.search || parsed.hash) {
      throw new Error();
    }
    return new URL("/auth/callback", parsed).toString();
  } catch {
    throw new AuthRuntimeError("CONFIGURATION_UNAVAILABLE", true);
  }
}
