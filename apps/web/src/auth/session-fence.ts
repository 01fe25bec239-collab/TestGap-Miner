import {
  authCallbackUrl,
  prepareAuthSignIn,
  type AuthSignInDependencies,
  type PreparedAuthSignIn,
} from "./sign-in";

export const AUTH_CONTEXT_COOKIE = "testgap-auth-context";
export const AUTH_SESSION_BINDING_COOKIE = "testgap-auth-session-binding";
export const LOCAL_SIGN_OUT_TOMBSTONE_COOKIE = "testgap-auth-signed-out";
export const AUTH_SESSION_FENCE_OPERATIONS = [
  "PREPARE_SIGN_IN",
  "PUBLISH_SIGN_OUT",
  "RESOLVE_SESSION",
] as const;

const HANDLE = /^[a-f0-9]{64}$/;
const TOMBSTONE_VALUE = "1";

export type AuthFenceFailure =
  | "STALE_PROVIDER_SESSION_MATERIAL"
  | "TOMBSTONED"
  | "UNVERIFIED"
  | "AUTHORITY_UNAVAILABLE";

export type AuthFenceEventReferences = Readonly<{
  signInAttemptReference: string;
  callbackFlowReference: string;
  correlationReference: string;
}>;

export type AuthFenceResolution =
  | Readonly<{ eligible: true; references: AuthFenceEventReferences }>
  | Readonly<{ eligible: false; reason: AuthFenceFailure }>;

export type AuthCookieDefinition = Readonly<{
  name: string;
  value: string;
  options: Readonly<{
    httpOnly: boolean;
    secure: boolean;
    sameSite: "lax";
    path: "/";
    maxAge?: 0;
  }>;
}>;

export function authContextCookie(handle: string, origin: string): AuthCookieDefinition {
  return opaqueCookie(AUTH_CONTEXT_COOKIE, handle, origin);
}

export function authSessionBindingCookie(
  handle: string,
  origin: string,
): AuthCookieDefinition {
  return opaqueCookie(AUTH_SESSION_BINDING_COOKIE, handle, origin);
}

export function localSignOutTombstoneCookie(origin: string): AuthCookieDefinition {
  return Object.freeze({
    name: LOCAL_SIGN_OUT_TOMBSTONE_COOKIE,
    value: TOMBSTONE_VALUE,
    options: cookieOptions(origin, false),
  });
}

export function clearedAuthCookie(
  name: typeof AUTH_SESSION_BINDING_COOKIE | typeof LOCAL_SIGN_OUT_TOMBSTONE_COOKIE,
  origin: string,
  httpOnly: boolean,
): AuthCookieDefinition {
  return Object.freeze({
    name,
    value: "",
    options: Object.freeze({ ...cookieOptions(origin, httpOnly), maxAge: 0 as const }),
  });
}

function opaqueCookie(name: string, handle: string, origin: string): AuthCookieDefinition {
  if (!HANDLE.test(handle)) throw new Error("Invalid opaque Auth handle");
  return Object.freeze({ name, value: handle, options: cookieOptions(origin, true) });
}

function cookieOptions(origin: string, httpOnly: boolean) {
  return Object.freeze({
    httpOnly,
    secure: origin !== "http://localhost:3000",
    sameSite: "lax" as const,
    path: "/" as const,
  });
}

export interface AuthFenceStateStore {
  readAuthContextHandle(): Promise<string | null>;
  writeAuthContextHandle(handle: string): Promise<void>;
  readSessionBindingHandle(): Promise<string | null>;
  writeSessionBindingHandle(handle: string): Promise<void>;
  clearSessionBindingHandle(): Promise<void>;
  hasLocalSignOutTombstone(): Promise<boolean>;
  createLocalSignOutTombstone(): void | Promise<void>;
  clearLocalSignOutTombstone(): Promise<void>;
}

export type AuthFenceCookieAccess = Readonly<{
  getAll():
    | readonly Readonly<{ name: string; value: string }>[]
    | Promise<readonly Readonly<{ name: string; value: string }>[] | null | undefined>
    | null
    | undefined;
  set(cookie: AuthCookieDefinition): void | Promise<void>;
}>;

export class AuthFenceCookieStateStore implements AuthFenceStateStore {
  constructor(
    private readonly origin: string,
    private readonly cookies: AuthFenceCookieAccess,
  ) {}

  async readAuthContextHandle() {
    return this.#readOpaque(AUTH_CONTEXT_COOKIE);
  }

  async writeAuthContextHandle(handle: string) {
    await this.cookies.set(authContextCookie(handle, this.origin));
  }

  async readSessionBindingHandle() {
    return this.#readOpaque(AUTH_SESSION_BINDING_COOKIE);
  }

  async writeSessionBindingHandle(handle: string) {
    await this.cookies.set(authSessionBindingCookie(handle, this.origin));
  }

  async clearSessionBindingHandle() {
    await this.cookies.set(
      clearedAuthCookie(AUTH_SESSION_BINDING_COOKIE, this.origin, true),
    );
  }

  async hasLocalSignOutTombstone() {
    return (await this.#all()).some(({ name }) => name === LOCAL_SIGN_OUT_TOMBSTONE_COOKIE);
  }

  createLocalSignOutTombstone() {
    return this.cookies.set(localSignOutTombstoneCookie(this.origin));
  }

  async clearLocalSignOutTombstone() {
    await this.cookies.set(
      clearedAuthCookie(LOCAL_SIGN_OUT_TOMBSTONE_COOKIE, this.origin, false),
    );
  }

  async #readOpaque(name: string) {
    const value = (await this.#all()).find((cookie) => cookie.name === name)?.value;
    return value && HANDLE.test(value) ? value : null;
  }

  async #all() {
    return (await this.cookies.getAll()) ?? [];
  }
}

type BrowserCookieDocument = { cookie: string };

/** Auth-owned browser helper. The marker is deny-only and contains no Auth data. */
export class BrowserLocalSignOutTombstone {
  constructor(
    private readonly origin = globalThis.location?.origin ?? "",
    private readonly cookieDocument: BrowserCookieDocument = globalThis.document,
  ) {}

  isActive() {
    return this.cookieDocument.cookie
      .split(";")
      .some((part) => part.trim().split("=", 1)[0] === LOCAL_SIGN_OUT_TOMBSTONE_COOKIE);
  }

  create() {
    const secure = this.origin === "http://localhost:3000" ? "" : "; Secure";
    this.cookieDocument.cookie = `${LOCAL_SIGN_OUT_TOMBSTONE_COOKIE}=${TOMBSTONE_VALUE}; Path=/; SameSite=Lax${secure}`;
  }

  clearAfterAuthorizedReconciliation() {
    const secure = this.origin === "http://localhost:3000" ? "" : "; Secure";
    this.cookieDocument.cookie = `${LOCAL_SIGN_OUT_TOMBSTONE_COOKIE}=; Path=/; SameSite=Lax; Max-Age=0${secure}`;
  }
}

type AttemptRecord = {
  readonly contextHandle: string;
  readonly generation: number;
  readonly attemptReference: string;
  callbackLookupHandle: string | null;
  callbackFlowReference: string | null;
  correlationReference: string | null;
  establishmentReference: string | null;
  bindingHandle: string | null;
};

type BindingRecord = Readonly<{
  contextHandle: string;
  generation: number;
  attemptReference: string;
  callbackFlowReference: string;
  establishmentReference: string;
}>;

type ContextRecord = {
  generation: number;
  publishedSignOutGeneration: number | null;
  reconciledSignOutGeneration: number | null;
  authorizedContextResetPending: boolean;
  attempts: Map<string, AttemptRecord>;
};

export type AuthSynchronizationAuthorityChange =
  | Readonly<{ kind: "GENERATION_ADVANCED"; contextHandle: string }>
  | Readonly<{ kind: "UNAVAILABLE" | "STATE_LOST" }>;

type PreparedSignIn = Readonly<{
  contextHandle: string;
  establishedContextHandle: string | null;
  attemptReference: string;
  reconciliationGeneration: number | null;
  authorizedContextReset: boolean;
}>;

/** Provider-neutral authority port. The production implementation is unselected. */
export interface AuthSynchronizationAuthority {
  subscribe(listener: (change: AuthSynchronizationAuthorityChange) => void): () => void;
  prepareSignIn(contextHandle: string | null, tombstoned: boolean): PreparedSignIn;
  completeSignInReconciliation(contextHandle: string, generation: number): void;
  completeAuthorizedContextReset(contextHandle: string): void;
  readCurrentGeneration(contextHandle: string): number;
  advanceSignOutGeneration(contextHandle: string): number;
  associateAttempt(
    contextHandle: string,
    attemptReference: string,
    callbackLookupHandle: string,
  ): AuthFenceEventReferences;
  validateAttempt(
    contextHandle: string,
    callbackLookupHandle: string,
  ): AuthFenceEventReferences | null;
  createSessionBinding(
    contextHandle: string,
    callbackLookupHandle: string,
  ): Readonly<{ bindingHandle: string; references: AuthFenceEventReferences }>;
  validateSessionBinding(
    contextHandle: string,
    bindingHandle: string,
  ): AuthFenceEventReferences | null;
  invalidateBinding(bindingHandle: string): void;
  invalidateBindingForAttempt(contextHandle: string, callbackLookupHandle: string): void;
  abandonAttempt(contextHandle: string, attemptReference: string): void;
  abandonAttemptForCallback(contextHandle: string, callbackLookupHandle: string): void;
}

/**
 * LOCAL_NON_PRODUCTION_ONLY / PROCESS_LOCAL.
 *
 * One OS process and one memory space only. This is not safe for replicas,
 * clusters, serverless isolates, load balancing, or independently restarted
 * handlers. State loss invalidates every prior context and requires reauthentication.
 */
export class LocalProcessAuthSynchronizationAuthority
  implements AuthSynchronizationAuthority
{
  #available = true;
  #contexts = new Map<string, ContextRecord>();
  #bindings = new Map<string, BindingRecord>();
  #listeners = new Set<(change: AuthSynchronizationAuthorityChange) => void>();

  constructor(readonly safetyClass: "LOCAL_NON_PRODUCTION_ONLY") {}

  setAvailableForTests(available: boolean) {
    this.#available = available;
    if (!available) this.#emit({ kind: "UNAVAILABLE" });
  }

  resetStateForTests() {
    this.#contexts.clear();
    this.#bindings.clear();
    this.#emit({ kind: "STATE_LOST" });
  }

  subscribe(listener: (change: AuthSynchronizationAuthorityChange) => void) {
    this.#listeners.add(listener);
    return () => this.#listeners.delete(listener);
  }

  prepareSignIn(contextHandle: string | null, tombstoned: boolean) {
    this.#assertAvailable();
    let context = contextHandle ? this.#contexts.get(contextHandle) : null;
    let establishedContextHandle: string | null = null;
    const hasOutstandingReconciliation = Boolean(
      context &&
        context.publishedSignOutGeneration !== null &&
        context.publishedSignOutGeneration === context.generation &&
        context.reconciledSignOutGeneration !== context.publishedSignOutGeneration,
    );

    let authorizedContextReset = Boolean(context?.authorizedContextResetPending);
    const lostSuppliedContext = !context && contextHandle !== null;
    if (
      tombstoned &&
      !hasOutstandingReconciliation &&
      !authorizedContextReset &&
      !lostSuppliedContext
    ) {
      throw new Error("Auth sign-in reconciliation failed");
    } else if (!context) {
      authorizedContextReset = contextHandle !== null;
      establishedContextHandle = this.#createContext(authorizedContextReset);
      contextHandle = establishedContextHandle;
      context = this.#contexts.get(contextHandle)!;
    }

    if (!context || !contextHandle) throw new Error("Auth context is unavailable");
    const attemptReference = createOpaqueAuthHandle();
    context.attempts.set(attemptReference, {
      contextHandle,
      generation: context.generation,
      attemptReference,
      callbackLookupHandle: null,
      callbackFlowReference: null,
      correlationReference: null,
      establishmentReference: null,
      bindingHandle: null,
    });
    return {
      contextHandle,
      establishedContextHandle,
      attemptReference,
      reconciliationGeneration: hasOutstandingReconciliation
        ? context.generation
        : null,
      authorizedContextReset:
        authorizedContextReset && !hasOutstandingReconciliation,
    } as const;
  }

  completeSignInReconciliation(contextHandle: string, generation: number) {
    this.#assertAvailable();
    const context = this.#contexts.get(contextHandle);
    if (
      !context ||
      context.generation !== generation ||
      context.publishedSignOutGeneration !== generation ||
      context.reconciledSignOutGeneration === generation
    ) {
      throw new Error("Auth sign-in reconciliation failed");
    }
    context.reconciledSignOutGeneration = generation;
    context.authorizedContextResetPending = false;
  }

  completeAuthorizedContextReset(contextHandle: string) {
    this.#assertAvailable();
    const context = this.#contexts.get(contextHandle);
    if (
      !context?.authorizedContextResetPending ||
      context.publishedSignOutGeneration !== null
    ) {
      throw new Error("Authorized Auth-context reset failed");
    }
    context.authorizedContextResetPending = false;
  }

  readCurrentGeneration(contextHandle: string) {
    this.#assertAvailable();
    const context = this.#contexts.get(contextHandle);
    if (!context) throw new Error("Auth context is unavailable");
    return context.generation;
  }

  advanceSignOutGeneration(contextHandle: string) {
    this.#assertAvailable();
    const context = this.#contexts.get(contextHandle);
    if (!context || context.generation >= Number.MAX_SAFE_INTEGER) {
      throw new Error("Auth generation cannot be advanced");
    }
    context.generation += 1;
    context.publishedSignOutGeneration = context.generation;
    this.#emit({ kind: "GENERATION_ADVANCED", contextHandle });
    return context.generation;
  }

  associateAttempt(
    contextHandle: string,
    attemptReference: string,
    callbackLookupHandle: string,
  ): AuthFenceEventReferences {
    this.#assertAvailable();
    const attempt = this.#attempt(contextHandle, attemptReference);
    if (attempt.generation !== this.readCurrentGeneration(contextHandle)) {
      throw new Error("Auth sign-in attempt is superseded");
    }
    if (attempt.callbackLookupHandle) throw new Error("Auth sign-in attempt already associated");
    attempt.callbackLookupHandle = callbackLookupHandle;
    attempt.callbackFlowReference = createOpaqueAuthHandle();
    attempt.correlationReference = createOpaqueAuthHandle();
    return this.#references(attempt);
  }

  validateAttempt(contextHandle: string, callbackLookupHandle: string) {
    this.#assertAvailable();
    const attempt = this.#validatedAttempt(contextHandle, callbackLookupHandle);
    return attempt ? this.#references(attempt) : null;
  }

  createSessionBinding(contextHandle: string, callbackLookupHandle: string) {
    this.#assertAvailable();
    const attempt = this.#validatedAttempt(contextHandle, callbackLookupHandle);
    if (!attempt) throw new Error("Auth sign-in attempt is superseded");
    const callbackFlowReference = attempt.callbackFlowReference!;
    const establishmentReference = createOpaqueAuthHandle();
    const bindingHandle = createOpaqueAuthHandle();
    const binding = Object.freeze({
      contextHandle,
      generation: attempt.generation,
      attemptReference: attempt.attemptReference,
      callbackFlowReference,
      establishmentReference,
    });
    this.#bindings.set(bindingHandle, binding);
    attempt.establishmentReference = establishmentReference;
    attempt.bindingHandle = bindingHandle;
    return { bindingHandle, references: this.#references(attempt) } as const;
  }

  validateSessionBinding(contextHandle: string, bindingHandle: string) {
    this.#assertAvailable();
    const context = this.#contexts.get(contextHandle);
    const binding = this.#bindings.get(bindingHandle);
    if (
      !context ||
      !binding ||
      binding.contextHandle !== contextHandle ||
      binding.generation !== context.generation
    ) {
      return null;
    }
    const attempt = context.attempts.get(binding.attemptReference);
    return attempt?.bindingHandle === bindingHandle ? this.#references(attempt) : null;
  }

  invalidateBinding(bindingHandle: string) {
    this.#assertAvailable();
    this.#bindings.delete(bindingHandle);
    for (const context of this.#contexts.values()) {
      for (const attempt of context.attempts.values()) {
        if (attempt.bindingHandle === bindingHandle) attempt.bindingHandle = null;
      }
    }
  }

  invalidateBindingForAttempt(contextHandle: string, callbackLookupHandle: string) {
    this.#assertAvailable();
    const context = this.#contexts.get(contextHandle);
    const attempt = [...(context?.attempts.values() ?? [])].find(
      (candidate) => candidate.callbackLookupHandle === callbackLookupHandle,
    );
    if (attempt?.bindingHandle) this.invalidateBinding(attempt.bindingHandle);
  }

  abandonAttempt(contextHandle: string, attemptReference: string) {
    this.#assertAvailable();
    this.#contexts.get(contextHandle)?.attempts.delete(attemptReference);
  }

  abandonAttemptForCallback(contextHandle: string, callbackLookupHandle: string) {
    this.#assertAvailable();
    const context = this.#contexts.get(contextHandle);
    if (!context) return;
    for (const [reference, attempt] of context.attempts) {
      if (attempt.callbackLookupHandle === callbackLookupHandle && !attempt.bindingHandle) {
        context.attempts.delete(reference);
      }
    }
  }

  #createContext(authorizedContextResetPending: boolean) {
    let handle = createOpaqueAuthHandle();
    while (this.#contexts.has(handle)) handle = createOpaqueAuthHandle();
    this.#contexts.set(handle, {
      generation: 0,
      publishedSignOutGeneration: null,
      reconciledSignOutGeneration: null,
      authorizedContextResetPending,
      attempts: new Map(),
    });
    return handle;
  }

  #attempt(contextHandle: string, attemptReference: string) {
    const attempt = this.#contexts.get(contextHandle)?.attempts.get(attemptReference);
    if (!attempt) throw new Error("Auth sign-in attempt is unavailable");
    return attempt;
  }

  #validatedAttempt(contextHandle: string, callbackLookupHandle: string) {
    const context = this.#contexts.get(contextHandle);
    if (!context) return null;
    const attempt = [...context.attempts.values()].find(
      (candidate) => candidate.callbackLookupHandle === callbackLookupHandle,
    );
    return attempt && attempt.generation === context.generation ? attempt : null;
  }

  #references(attempt: AttemptRecord): AuthFenceEventReferences {
    if (!attempt.callbackFlowReference || !attempt.correlationReference) {
      throw new Error("Auth callback association is unavailable");
    }
    return Object.freeze({
      signInAttemptReference: attempt.attemptReference,
      callbackFlowReference: attempt.callbackFlowReference,
      correlationReference: attempt.correlationReference,
    });
  }

  #assertAvailable() {
    if (!this.#available) throw new Error("Auth synchronization authority unavailable");
  }

  #emit(change: AuthSynchronizationAuthorityChange) {
    for (const listener of this.#listeners) listener(change);
  }
}

export interface AuthSessionFence {
  prepareSignIn(): Promise<Readonly<{ signInAttemptReference: string }>>;
  associateSignInAttempt(
    signInAttemptReference: string,
    callbackLookupHandle: string,
  ): Promise<AuthFenceEventReferences>;
  abandonSignInAttempt(signInAttemptReference: string): Promise<void>;
  abandonCallback(callbackLookupHandle: string): Promise<void>;
  validateCallback(callbackLookupHandle: string): Promise<AuthFenceResolution>;
  establishSession(callbackLookupHandle: string): Promise<AuthFenceResolution>;
  rollbackSessionEstablishment(callbackLookupHandle: string): Promise<void>;
  resolveFence(): Promise<AuthFenceResolution>;
  createLocalSignOutTombstone(): void | Promise<void>;
  publishSignOut(): Promise<void>;
  cleanupStaleSessionMaterial(): Promise<void>;
  subscribeToFenceChanges(listener: () => void): () => void;
}

export class AuthSessionFenceService implements AuthSessionFence {
  #lastContextHandle: string | null = null;

  constructor(
    private readonly authority: AuthSynchronizationAuthority,
    private readonly state: AuthFenceStateStore,
  ) {}

  async prepareSignIn() {
    const contextHandle = await this.#context();
    const tombstoned = await this.state.hasLocalSignOutTombstone();
    const prepared = this.authority.prepareSignIn(contextHandle, tombstoned);
    this.#lastContextHandle = prepared.contextHandle;
    try {
      if (prepared.authorizedContextReset) {
        await this.state.clearSessionBindingHandle();
        if (prepared.establishedContextHandle) {
          await this.state.writeAuthContextHandle(prepared.establishedContextHandle);
        }
        if (tombstoned) await this.state.clearLocalSignOutTombstone();
        this.authority.completeAuthorizedContextReset(prepared.contextHandle);
      } else {
        if (prepared.establishedContextHandle) {
          await this.state.writeAuthContextHandle(prepared.establishedContextHandle);
        }
        if (prepared.reconciliationGeneration !== null) {
          try {
            await this.state.clearLocalSignOutTombstone();
            this.authority.completeSignInReconciliation(
              prepared.contextHandle,
              prepared.reconciliationGeneration,
            );
          } catch (error) {
            await Promise.resolve(this.state.createLocalSignOutTombstone()).catch(
              () => undefined,
            );
            throw error;
          }
        }
      }
    } catch (error) {
      if (prepared.authorizedContextReset && tombstoned) {
        await Promise.resolve(this.state.createLocalSignOutTombstone()).catch(
          () => undefined,
        );
      }
      try {
        this.authority.abandonAttempt(
          prepared.contextHandle,
          prepared.attemptReference,
        );
      } catch {
        // The failed preparation has no callback association or session eligibility.
      }
      throw error;
    }
    return Object.freeze({ signInAttemptReference: prepared.attemptReference });
  }

  async associateSignInAttempt(
    signInAttemptReference: string,
    callbackLookupHandle: string,
  ) {
    const contextHandle = await this.#requiredContext();
    return this.authority.associateAttempt(
      contextHandle,
      signInAttemptReference,
      callbackLookupHandle,
    );
  }

  async abandonSignInAttempt(signInAttemptReference: string) {
    const contextHandle = await this.#context();
    if (contextHandle) this.authority.abandonAttempt(contextHandle, signInAttemptReference);
  }

  async abandonCallback(callbackLookupHandle: string) {
    const contextHandle = await this.#context();
    if (contextHandle) this.authority.abandonAttemptForCallback(contextHandle, callbackLookupHandle);
  }

  async validateCallback(callbackLookupHandle: string): Promise<AuthFenceResolution> {
    if (await this.state.hasLocalSignOutTombstone()) {
      return { eligible: false, reason: "TOMBSTONED" };
    }
    const contextHandle = await this.#context();
    if (!contextHandle) return { eligible: false, reason: "UNVERIFIED" };
    try {
      const validated = this.authority.validateAttempt(contextHandle, callbackLookupHandle);
      return validated
        ? { eligible: true, references: validated }
        : { eligible: false, reason: "STALE_PROVIDER_SESSION_MATERIAL" };
    } catch {
      return { eligible: false, reason: "AUTHORITY_UNAVAILABLE" };
    }
  }

  async establishSession(callbackLookupHandle: string): Promise<AuthFenceResolution> {
    const validation = await this.validateCallback(callbackLookupHandle);
    if (!validation.eligible) return validation;
    const contextHandle = await this.#requiredContext();
    try {
      const established = this.authority.createSessionBinding(
        contextHandle,
        callbackLookupHandle,
      );
      try {
        await this.state.writeSessionBindingHandle(established.bindingHandle);
      } catch (error) {
        this.authority.invalidateBinding(established.bindingHandle);
        throw error;
      }
      return { eligible: true, references: established.references };
    } catch {
      return { eligible: false, reason: "STALE_PROVIDER_SESSION_MATERIAL" };
    }
  }

  async rollbackSessionEstablishment(callbackLookupHandle: string) {
    const contextHandle = await this.#context();
    if (contextHandle) {
      try {
        this.authority.invalidateBindingForAttempt(contextHandle, callbackLookupHandle);
      } catch {
        // Semantic denial already occurred; cookie cleanup still proceeds.
      }
    }
    await this.state.clearSessionBindingHandle();
  }

  async resolveFence(): Promise<AuthFenceResolution> {
    if (await this.state.hasLocalSignOutTombstone()) {
      return this.#denyResolvedSession("TOMBSTONED");
    }
    const [contextHandle, bindingHandle] = await Promise.all([
      this.#context(),
      this.state.readSessionBindingHandle(),
    ]);
    if (!contextHandle || !bindingHandle) return this.#denyResolvedSession("UNVERIFIED");
    try {
      const references = this.authority.validateSessionBinding(contextHandle, bindingHandle);
      return references
        ? { eligible: true, references }
        : this.#denyResolvedSession("STALE_PROVIDER_SESSION_MATERIAL");
    } catch {
      return this.#denyResolvedSession("AUTHORITY_UNAVAILABLE");
    }
  }

  createLocalSignOutTombstone() {
    return this.state.createLocalSignOutTombstone();
  }

  async publishSignOut() {
    const contextHandle = await this.#requiredContext();
    this.authority.advanceSignOutGeneration(contextHandle);
    await this.cleanupStaleSessionMaterial();
  }

  async cleanupStaleSessionMaterial() {
    const bindingHandle = await this.state.readSessionBindingHandle();
    if (bindingHandle) {
      try {
        this.authority.invalidateBinding(bindingHandle);
      } catch {
        // Authority loss cannot prevent local stale-cookie cleanup.
      }
    }
    await this.state.clearSessionBindingHandle();
  }

  subscribeToFenceChanges(listener: () => void) {
    return this.authority.subscribe((change) => {
      if (
        change.kind !== "GENERATION_ADVANCED" ||
        !this.#lastContextHandle ||
        change.contextHandle === this.#lastContextHandle
      ) {
        listener();
      }
    });
  }

  async #context() {
    const contextHandle = await this.state.readAuthContextHandle();
    this.#lastContextHandle = contextHandle;
    return contextHandle;
  }

  async #requiredContext() {
    const contextHandle = await this.#context();
    if (!contextHandle) throw new Error("Auth context is unavailable");
    return contextHandle;
  }

  async #denyResolvedSession(reason: AuthFenceFailure): Promise<AuthFenceResolution> {
    await this.cleanupStaleSessionMaterial().catch(() => undefined);
    return { eligible: false, reason };
  }
}

export type AuthResolvedSession =
  | Readonly<{ state: "AUTHENTICATED"; userReference: string }>
  | Readonly<{ state: "UNAUTHENTICATED"; userReference: null }>;

export type AuthSessionFenceHostRequest =
  | Readonly<{ operation: "PREPARE_SIGN_IN"; intendedReturn?: string }>
  | Readonly<{ operation: "PUBLISH_SIGN_OUT" }>
  | Readonly<{ operation: "RESOLVE_SESSION" }>;

export type AuthSessionFenceHostResponse =
  | PreparedAuthSignIn
  | Readonly<{ ok: true }>
  | AuthResolvedSession;

/** Auth-owned semantics behind the future UI-owned POST /auth/session-fence host. */
export interface AuthSessionFenceHost {
  prepareSignIn(intendedReturn?: string): Promise<PreparedAuthSignIn>;
  publishSignOut(): Promise<void>;
  resolveSession(): Promise<AuthResolvedSession>;
}

export class AuthSessionFenceHostService implements AuthSessionFenceHost {
  #callbackUrl: string;

  constructor(private readonly dependencies: AuthSignInDependencies) {
    this.#callbackUrl = authCallbackUrl(dependencies.applicationOrigin);
  }

  prepareSignIn(intendedReturn?: string) {
    return prepareAuthSignIn(this.dependencies, this.#callbackUrl, intendedReturn);
  }

  async publishSignOut() {
    await this.dependencies.sessionFence.createLocalSignOutTombstone();
    await this.dependencies.sessionFence.publishSignOut();
  }

  async resolveSession(): Promise<AuthResolvedSession> {
    const session = await this.dependencies.provider.getSession().catch(() => null);
    if (session) {
      const currentUser = await this.dependencies.provider
        .validateCurrentUser()
        .catch(() => null);
      const fence = currentUser
        ? await this.dependencies.sessionFence.resolveFence().catch(() => null)
        : null;
      if (fence?.eligible && currentUser?.userReference === session.userReference) {
        return Object.freeze({
          state: "AUTHENTICATED",
          userReference: currentUser.userReference,
        });
      }
    }
    await Promise.all([
      this.dependencies.sessionFence
        .cleanupStaleSessionMaterial()
        .catch(() => undefined),
      this.dependencies.provider.signOutLocal().catch(() => undefined),
    ]);
    return Object.freeze({ state: "UNAUTHENTICATED", userReference: null });
  }
}

/** Parses and dispatches only the three frozen host operations. */
export async function executeAuthSessionFenceHostRequest(
  host: AuthSessionFenceHost,
  input: unknown,
): Promise<AuthSessionFenceHostResponse> {
  const request = parseAuthSessionFenceHostRequest(input);
  switch (request.operation) {
    case "PREPARE_SIGN_IN":
      return host.prepareSignIn(request.intendedReturn);
    case "PUBLISH_SIGN_OUT":
      await host.publishSignOut();
      return Object.freeze({ ok: true });
    case "RESOLVE_SESSION":
      return host.resolveSession();
  }
}

function parseAuthSessionFenceHostRequest(input: unknown): AuthSessionFenceHostRequest {
  if (!input || typeof input !== "object" || Array.isArray(input)) {
    throw new Error("Invalid Auth session-fence request");
  }
  const record = input as Record<string, unknown>;
  if (record.operation === "PREPARE_SIGN_IN") {
    if (
      !exactKeys(record, record.intendedReturn === undefined
        ? ["operation"]
        : ["operation", "intendedReturn"]) ||
      (record.intendedReturn !== undefined && typeof record.intendedReturn !== "string")
    ) {
      throw new Error("Invalid Auth session-fence request");
    }
    return record as AuthSessionFenceHostRequest;
  }
  if (
    (record.operation === "PUBLISH_SIGN_OUT" ||
      record.operation === "RESOLVE_SESSION") &&
    exactKeys(record, ["operation"])
  ) {
    return record as AuthSessionFenceHostRequest;
  }
  throw new Error("Invalid Auth session-fence request");
}

function exactKeys(record: Record<string, unknown>, expected: readonly string[]) {
  const keys = Object.keys(record);
  return keys.length === expected.length && expected.every((key) => keys.includes(key));
}

const SHARED_LOCAL_AUTHORITY = Symbol.for("testgap.auth.local-process-authority");

export function getSharedLocalProcessAuthSynchronizationAuthority(input: {
  applicationOrigin: string;
  environmentClass: "LOCAL_DEVELOPMENT";
}) {
  if (
    input.applicationOrigin !== "http://localhost:3000" ||
    input.environmentClass !== "LOCAL_DEVELOPMENT" ||
    process.env.NODE_ENV === "production"
  ) {
    throw new Error("Process-local Auth authority is restricted to local development");
  }
  const shared = globalThis as typeof globalThis & {
    [SHARED_LOCAL_AUTHORITY]?: LocalProcessAuthSynchronizationAuthority;
  };
  return (shared[SHARED_LOCAL_AUTHORITY] ??= new LocalProcessAuthSynchronizationAuthority(
    "LOCAL_NON_PRODUCTION_ONLY",
  ));
}

export function createOpaqueAuthHandle() {
  const bytes = new Uint8Array(32);
  globalThis.crypto.getRandomValues(bytes);
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}
