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
import {
  createOpaqueAuthHandle,
  type AuthFenceEventReferences,
  type AuthSessionFence,
} from "./session-fence";
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

type CallbackSecurityContext = {
  readonly requestReference: string;
  references: AuthFenceEventReferences | null;
};

export type AuthRuntimeDependencies = Readonly<{
  provider: import("./types").AuthProvider;
  correlationStore: CorrelationStore;
  sessionFence: AuthSessionFence;
  securityPolicyVersion: string;
  environmentClass: AuthSecurityEvent["environmentClass"];
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
  #verificationEpoch = 0;
  #callbackUrl: string;

  constructor(private readonly dependencies: AuthRuntimeDependencies) {
    if (!isValidSecurityPolicyVersion(dependencies.securityPolicyVersion)) {
      throw new AuthRuntimeError("CONFIGURATION_UNAVAILABLE", true);
    }
    this.#callbackUrl = callbackUrlForOrigin(dependencies.applicationOrigin);
    dependencies.sessionFence.subscribeToFenceChanges(() => {
      this.#verificationEpoch += 1;
      if (this.#signOutPromise || this.#machine.snapshot.state === "SIGN_OUT_PENDING") return;
      this.#transitionFailClosed();
    });
    dependencies.provider.onSessionChange((event, session) => {
      if (event === "SIGNED_OUT" || !session) {
        this.#verificationEpoch += 1;
        this.#transitionUnauthenticated();
        void this.dependencies.sessionFence.cleanupStaleSessionMaterial().catch(() => undefined);
        return;
      }
      if (this.#callbackProcessingCount || this.#refreshPromise || this.#signOutPromise) return;
      void this.#resolveProviderSignal(session);
    });
  }

  beginSignIn(intendedReturn?: string): Promise<void> {
    if (this.#beginPromise) return this.#beginPromise;
    const state = this.#machine.snapshot.state;
    if (
      state !== "UNAUTHENTICATED" &&
      state !== "RECOVERABLE_ERROR" &&
      state !== "TERMINAL_SESSION_ERROR"
    ) {
      return Promise.reject(new AuthRuntimeError("TEMPORARY_PROVIDER_FAILURE", true));
    }

    this.#verificationEpoch += 1;
    this.#beginPromise = this.#beginSignIn(intendedReturn).finally(() => {
      this.#beginPromise = null;
    });
    return this.#beginPromise;
  }

  async #beginSignIn(intendedReturn?: string) {
    this.#machine.transition("SIGN_IN_PENDING");
    let handle: string | null = null;
    let signInAttemptReference: string | null = null;
    let redirectUrl: string;
    try {
      ({ signInAttemptReference } = await this.dependencies.sessionFence.prepareSignIn());
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
      await this.dependencies.sessionFence.associateSignInAttempt(
        signInAttemptReference,
        handle,
      );
      await this.dependencies.setCorrelationCookie(
        correlationCookie(handle, this.dependencies.applicationOrigin),
      );
      redirectUrl = providerResult.redirectUrl;
    } catch (error) {
      if (handle) {
        await this.dependencies.correlationStore.remove(handle).catch(() => undefined);
        await Promise.resolve(this.dependencies.deleteCorrelationCookie(handle)).catch(() => undefined);
      }
      if (signInAttemptReference) {
        await this.dependencies.sessionFence
          .abandonSignInAttempt(signInAttemptReference)
          .catch(() => undefined);
      }
      if (this.#machine.snapshot.state !== "TERMINAL_SESSION_ERROR") {
        this.#machine.transition("RECOVERABLE_ERROR");
      }
      throw safeRuntimeError(error, "TEMPORARY_PROVIDER_FAILURE");
    }
    await this.dependencies.redirectToProvider(redirectUrl);
  }

  async processCallback(request: CallbackRequest): Promise<CallbackResult> {
    this.#callbackProcessingCount += 1;
    const securityContext: CallbackSecurityContext = {
      requestReference: createOpaqueAuthHandle(),
      references: null,
    };
    const preExistingSession = await this.dependencies.provider.getSession().catch(() => null);
    try {
      this.#machine.transition("CALLBACK_PROCESSING");
      const parsed = parseCallback(request.url, this.#callbackUrl);
      const match = parsed.flowId
        ? await this.#findCorrelation(request.correlationHandles, parsed.flowId)
        : null;

      if (!parsed.ok) {
        if (match?.record.lifecycle === "PENDING_ATTEMPT_CORRELATION") {
          await this.#captureCallbackFence(match.handle, securityContext);
          await this.#discardAttempt(match.handle);
        }
        return await this.#callbackFailure(parsed.error, preExistingSession, securityContext);
      }

      if (!match) {
        return await this.#callbackFailure(
          "INVALID_CALLBACK",
          preExistingSession,
          securityContext,
        );
      }

      if (match.record.securityPolicyVersion !== this.dependencies.securityPolicyVersion) {
        await this.#captureCallbackFence(match.handle, securityContext);
        if (match.record.lifecycle === "PENDING_ATTEMPT_CORRELATION") {
          await this.#discardAttempt(match.handle);
        }
        return await this.#callbackFailure(
          "INVALID_CALLBACK",
          preExistingSession,
          securityContext,
        );
      }

      if (!(await this.#captureCallbackFence(match.handle, securityContext))) {
        if (match.record.lifecycle === "PENDING_ATTEMPT_CORRELATION") {
          await this.#discardAttempt(match.handle);
        }
        return await this.#callbackFailure(
          "INVALID_CALLBACK",
          preExistingSession,
          securityContext,
        );
      }

      if (match.record.lifecycle === "COMPLETED_CALLBACK_CORRELATION") {
        return await this.#completedCallback(
          match.record,
          preExistingSession,
          securityContext,
        );
      }

      const active = this.#callbackFlights.get(match.handle);
      if (active) return await active;

      const current = await this.dependencies.correlationStore.lookup(
        match.handle,
        parsed.flowId,
        this.#now(),
      );
      if (!current) {
        return await this.#callbackFailure(
          "INVALID_CALLBACK",
          preExistingSession,
          securityContext,
        );
      }
      if (current.securityPolicyVersion !== this.dependencies.securityPolicyVersion) {
        if (current.lifecycle === "PENDING_ATTEMPT_CORRELATION") {
          await this.#discardAttempt(match.handle);
        }
        return await this.#callbackFailure(
          "INVALID_CALLBACK",
          preExistingSession,
          securityContext,
        );
      }
      if (current.lifecycle === "COMPLETED_CALLBACK_CORRELATION") {
        return await this.#completedCallback(current, preExistingSession, securityContext);
      }
      if (!(await this.#captureCallbackFence(match.handle, securityContext))) {
        await this.#discardAttempt(match.handle);
        return await this.#callbackFailure(
          "INVALID_CALLBACK",
          preExistingSession,
          securityContext,
        );
      }

      const concurrentlyStarted = this.#callbackFlights.get(match.handle);
      if (concurrentlyStarted) return await concurrentlyStarted;

      const flight = this.#exchangeCallback(
        parsed.code,
        parsed.flowId,
        match.handle,
        preExistingSession,
        securityContext,
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
      return await this.#callbackFailure(
        "INVALID_CALLBACK",
        preExistingSession,
        securityContext,
      );
    } finally {
      this.#callbackProcessingCount -= 1;
    }
  }

  async #exchangeCallback(
    code: string,
    flowId: string,
    handle: string,
    preExistingSession: ProviderSession | null,
    securityContext: CallbackSecurityContext,
  ): Promise<CallbackResult> {
    const operationEpoch = this.#operationEpoch;
    const verificationEpoch = this.#verificationEpoch;
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
      return await this.#callbackFailure(internalError, preExistingSession, securityContext);
    }

    try {
      await exchange.prepareSessionCommit();
    } catch {
      await exchange.discardSession();
      await this.#discardAttempt(handle);
      return await this.#callbackFailure(
        "SESSION_EXCHANGE_FAILED",
        preExistingSession,
        securityContext,
      );
    }

    if (
      operationEpoch !== this.#operationEpoch ||
      !(await this.#captureCallbackFence(handle, securityContext))
    ) {
      await exchange.discardSession();
      await this.#discardAttempt(handle);
      return await this.#callbackFailure(
        "INVALID_CALLBACK",
        preExistingSession,
        securityContext,
      );
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
      return await this.#callbackFailure(
        "INVALID_CALLBACK",
        preExistingSession,
        securityContext,
      );
    }
    if (!completion) {
      await exchange.discardSession();
      await this.#discardAttempt(handle);
      return await this.#callbackFailure(
        "INVALID_CALLBACK",
        preExistingSession,
        securityContext,
      );
    }

    const establishment = await this.dependencies.sessionFence.establishSession(handle);
    if (!establishment.eligible || operationEpoch !== this.#operationEpoch) {
      await exchange.discardSession();
      await this.#rollbackRejectedEstablishment(handle);
      return await this.#callbackFailure(
        "INVALID_CALLBACK",
        preExistingSession,
        securityContext,
      );
    }
    securityContext.references = establishment.references;

    let committed = false;
    try {
      await this.dependencies.setCorrelationCookie(
        completedCorrelationCookie(handle, this.dependencies.applicationOrigin),
      );
      const beforeCommit = await this.dependencies.sessionFence.resolveFence();
      if (!beforeCommit.eligible || operationEpoch !== this.#operationEpoch) throw new Error();
      await exchange.commitSession();
      committed = true;
      const afterCommit = await this.dependencies.sessionFence.resolveFence();
      if (
        !afterCommit.eligible ||
        !this.#canRestoreAuthenticated(operationEpoch, verificationEpoch)
      ) {
        this.#transitionFailClosed();
        await this.#rollbackRejectedEstablishment(handle);
        await this.#cleanupStaleCurrentProviderMaterial();
        return await this.#callbackFailure(
          "INVALID_CALLBACK",
          preExistingSession,
          securityContext,
        );
      }
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
      if (!committed) await exchange.discardSession().catch(() => undefined);
      await this.#rollbackRejectedEstablishment(handle);
      return await this.#callbackFailure(
        "SESSION_EXCHANGE_FAILED",
        preExistingSession,
        securityContext,
      );
    }
  }

  async #completedCallback(
    record: Extract<CorrelationRecord, { lifecycle: "COMPLETED_CALLBACK_CORRELATION" }>,
    preExistingSession: ProviderSession | null,
    securityContext: CallbackSecurityContext,
  ): Promise<CallbackResult> {
    const operationEpoch = this.#operationEpoch;
    const verificationEpoch = this.#verificationEpoch;
    this.#machine.transition("CALLBACK_PROCESSING");
    const validated = await this.#validatePreservedSession(preExistingSession);
    if (
      validated?.userReference !== record.outcome.userReference ||
      !this.#canRestoreAuthenticated(operationEpoch, verificationEpoch)
    ) {
      this.#transitionFailClosed();
      await this.#cleanupStaleCurrentProviderMaterial();
      return await this.#callbackFailure(
        "INVALID_CALLBACK",
        null,
        securityContext,
      );
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
    const operationEpoch = this.#operationEpoch;
    const verificationEpoch = this.#verificationEpoch;
    if (this.#refreshPromise) await this.#refreshPromise;
    if (this.#machine.snapshot.state !== "AUTHENTICATED") {
      await this.#cleanupStaleCurrentProviderMaterial();
      throw new AuthRuntimeError("SESSION_EXPIRED");
    }

    let session = await this.dependencies.provider.getSession();
    if (!session || !(await this.#isCurrentProviderSession(session))) {
      await this.#denyCurrentSession();
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

    if (!session) {
      await this.#denyCurrentSession();
      throw new AuthRuntimeError("SESSION_EXPIRED");
    }
    const current = await this.#isCurrentProviderSession(session);
    if (
      !current ||
      this.#machine.snapshot.state !== "AUTHENTICATED" ||
      !this.#canRestoreAuthenticated(operationEpoch, verificationEpoch)
    ) {
      await this.#denyCurrentSession();
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
      await this.#cleanupStaleCurrentProviderMaterial();
      throw new AuthRuntimeError("SESSION_EXPIRED");
    }

    const session = await this.dependencies.provider.getSession();
    if (!session || !(await this.#isCurrentProviderSession(session))) {
      await this.#denyCurrentSession();
      throw new AuthRuntimeError("SESSION_EXPIRED");
    }
    const mode =
      forcedMode ??
      (session.expiresAt > this.#now()
        ? "PROVEN_CREDENTIAL"
        : "UNPROVEN_CREDENTIAL");
    const epoch = this.#operationEpoch;
    const verificationEpoch = this.#verificationEpoch;
    this.#machine.transition("REFRESH_PENDING", {
      refreshMode: mode,
      userReference: session.userReference,
    });

    try {
      const refreshed = await this.dependencies.provider.refresh();
      if (epoch !== this.#operationEpoch) {
        await Promise.all([
          this.dependencies.sessionFence.cleanupStaleSessionMaterial().catch(() => undefined),
          this.dependencies.provider.signOutLocal().catch(() => undefined),
        ]);
        return this.#machine.snapshot;
      }
      if (verificationEpoch !== this.#verificationEpoch) {
        await this.#cleanupStaleCurrentProviderMaterial();
        throw new AuthRuntimeError("REFRESH_FAILED");
      }
      if (!(await this.#isCurrentProviderSession(refreshed))) {
        await this.#denyCurrentSession();
        throw new AuthRuntimeError("REFRESH_FAILED");
      }
      if (
        !this.#canRestoreAuthenticated(epoch, verificationEpoch)
      ) {
        await this.#cleanupStaleCurrentProviderMaterial();
        return this.#machine.snapshot;
      }
      return this.#machine.transition("AUTHENTICATED", {
        userReference: refreshed.userReference,
      });
    } catch (error) {
      if (epoch !== this.#operationEpoch) return this.#machine.snapshot;
      const recoverable = error instanceof AuthRuntimeError && error.recoverable;
      this.#machine.transition(recoverable ? "RECOVERABLE_ERROR" : "TERMINAL_SESSION_ERROR");
      throw safeRuntimeError(error, recoverable ? "TEMPORARY_PROVIDER_FAILURE" : "REFRESH_FAILED");
    }
  }

  signOut(): Promise<SignOutResult> {
    if (this.#signOutPromise) return this.#signOutPromise;
    let tombstone: Promise<void>;
    try {
      tombstone = Promise.resolve(
        this.dependencies.sessionFence.createLocalSignOutTombstone(),
      );
    } catch (error) {
      tombstone = Promise.reject(error);
    }
    this.#operationEpoch += 1;
    this.#verificationEpoch += 1;
    this.#machine.transition("SIGN_OUT_PENDING");
    this.#signOutPromise = this.#performSignOut(tombstone).finally(() => {
        this.#signOutPromise = null;
      });
    return this.#signOutPromise;
  }

  async #performSignOut(tombstone: Promise<void>): Promise<SignOutResult> {
    let failed = false;
    await tombstone.catch(() => {
      failed = true;
    });
    await this.dependencies.sessionFence.publishSignOut().catch(() => {
      failed = true;
    });
    await this.dependencies.provider.signOutLocal().catch(() => {
      failed = true;
    });
    await this.dependencies.sessionFence.cleanupStaleSessionMaterial().catch(() => {
      failed = true;
    });
    this.#transitionUnauthenticated();
    return failed
      ? { ok: false, error: "SIGN_OUT_FAILED", destination: DEFAULT_AUTH_DESTINATION }
      : { ok: true, error: null, destination: DEFAULT_AUTH_DESTINATION };
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
    await this.dependencies.sessionFence.abandonCallback(handle).catch(() => undefined);
    await this.dependencies.deleteCorrelationCookie(handle);
  }

  async #callbackFailure(
    internalError: InternalCallbackError | "PROVIDER_DENIED" | "USER_CANCELLED",
    preExistingSession: ProviderSession | null,
    securityContext: CallbackSecurityContext,
  ): Promise<CallbackResult> {
    const operationEpoch = this.#operationEpoch;
    const verificationEpoch = this.#verificationEpoch;
    await Promise.resolve(this.dependencies.clearCallbackUrl()).catch(() => undefined);
    const preserved = await this.#validatePreservedSession(preExistingSession);
    if (preserved && this.#canRestoreAuthenticated(operationEpoch, verificationEpoch)) {
      this.#machine.transition("AUTHENTICATED", { userReference: preserved.userReference });
      const result = {
        ok: false,
        error: publicCallbackError(internalError),
        snapshot: this.#machine.snapshot,
        destination: DEFAULT_AUTH_DESTINATION,
      } as const;
      await this.#emitSecurityEvent(
        internalError,
        true,
        securityContext,
        preserved.userReference,
      );
      return result;
    }
    if (preserved) {
      this.#transitionFailClosed();
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
    await this.#emitSecurityEvent(internalError, false, securityContext, null);
    if (preExistingSession) {
      await Promise.all([
        this.dependencies.sessionFence.cleanupStaleSessionMaterial().catch(() => undefined),
        this.dependencies.provider.signOutLocal().catch(() => undefined),
      ]);
    }
    return result;
  }

  async #validatePreservedSession(preExisting: ProviderSession | null) {
    if (!preExisting) return null;
    const validated = await this.dependencies.provider
      .validatePreExistingSession(preExisting)
      .catch(() => null);
    if (validated?.userReference !== preExisting.userReference) return null;
    const fence = await this.dependencies.sessionFence.resolveFence().catch(() => null);
    return fence?.eligible ? validated : null;
  }

  async #emitSecurityEvent(
    classification: InternalCallbackError | "PROVIDER_DENIED" | "USER_CANCELLED",
    sessionPreserved: boolean,
    securityContext: CallbackSecurityContext,
    userReference: string | null,
  ) {
    if (!PUBLIC_CALLBACK_FAILURES.has(classification as InternalCallbackError)) return;
    try {
      await this.dependencies.emitSecurityEvent(
        Object.freeze({
          eventName: `AUTH_${classification}` as `AUTH_${InternalCallbackError}`,
          classification: classification as InternalCallbackError,
          occurredAt: new Date(this.#now()).toISOString(),
          environmentClass: this.dependencies.environmentClass,
          sourceComponent: "AUTH",
          outcome: "REJECTED",
          blockingEffect: "CALLBACK_REJECTED",
          actorType: userReference ? "HUMAN_USER" : "UNAUTHENTICATED",
          actorReference: userReference ?? "UNAUTHENTICATED",
          signInAttemptReference:
            securityContext.references?.signInAttemptReference ?? null,
          callbackFlowReference:
            securityContext.references?.callbackFlowReference ?? null,
          requestReference: securityContext.requestReference,
          correlationReference:
            securityContext.references?.correlationReference ?? null,
          policyVersion: this.dependencies.securityPolicyVersion,
          sessionPreserved,
          reasonCode: classification as InternalCallbackError,
          redactionStatus: "SECRET_FREE",
          callbackSuccess: false,
          rejectedCallbackDestinationUsed: false,
        }),
      );
    } catch {
      throw new SecurityEventSinkFailure();
    }
  }

  async #captureCallbackFence(
    handle: string,
    securityContext: CallbackSecurityContext,
  ) {
    const resolution = await this.dependencies.sessionFence.validateCallback(handle);
    if (resolution.eligible) securityContext.references = resolution.references;
    return resolution.eligible;
  }

  async #rollbackRejectedEstablishment(handle: string) {
    await this.dependencies.sessionFence
      .rollbackSessionEstablishment(handle)
      .catch(() => undefined);
    await this.dependencies.correlationStore.remove(handle).catch(() => undefined);
    await Promise.resolve(this.dependencies.deleteCorrelationCookie(handle)).catch(
      () => undefined,
    );
  }

  async #isCurrentProviderSession(session: ProviderSession) {
    const currentUser = await this.dependencies.provider
      .validateCurrentUser()
      .catch(() => null);
    const fence = currentUser
      ? await this.dependencies.sessionFence.resolveFence().catch(() => null)
      : null;
    return Boolean(
      fence?.eligible && currentUser?.userReference === session.userReference,
    );
  }

  #canRestoreAuthenticated(operationEpoch: number, verificationEpoch: number) {
    return (
      operationEpoch === this.#operationEpoch &&
      verificationEpoch === this.#verificationEpoch &&
      !this.#signOutPromise &&
      this.#machine.snapshot.state !== "SIGN_OUT_PENDING"
    );
  }

  async #denyCurrentSession() {
    this.#transitionFailClosed();
    await this.#cleanupStaleCurrentProviderMaterial();
  }

  async #cleanupStaleCurrentProviderMaterial() {
    await Promise.all([
      this.dependencies.sessionFence.cleanupStaleSessionMaterial().catch(() => undefined),
      this.dependencies.provider.signOutLocal().catch(() => undefined),
    ]);
  }

  async #resolveProviderSignal(provisionalSession: ProviderSession) {
    const verificationEpoch = ++this.#verificationEpoch;
    const operationEpoch = this.#operationEpoch;
    try {
      this.#machine.transition("INITIALIZING");
    } catch {
      return;
    }
    const session = await this.dependencies.provider.getSession().catch(() => null);
    const eligible = session && (await this.#isCurrentProviderSession(session));
    if (
      verificationEpoch !== this.#verificationEpoch ||
      operationEpoch !== this.#operationEpoch ||
      this.#beginPromise ||
      this.#callbackProcessingCount ||
      this.#refreshPromise ||
      this.#signOutPromise
    ) {
      return;
    }
    if (eligible && session.userReference === provisionalSession.userReference) {
      this.#machine.transition("AUTHENTICATED", {
        userReference: session.userReference,
      });
      return;
    }
    await this.#denyCurrentSession();
  }

  #transitionFailClosed() {
    try {
      this.#machine.transition("TERMINAL_SESSION_ERROR");
    } catch {
      // Invalid ordering already forces TERMINAL_SESSION_ERROR.
    }
  }

  #transitionUnauthenticated() {
    try {
      this.#machine.transition("UNAUTHENTICATED");
    } catch {
      // Invalid ordering already fails closed.
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
