import { BrowserLocalSignOutTombstone, type AuthResolvedSession } from "./session-fence";
import { AuthStateMachine } from "./state-machine";
import type {
  AuthAdapter,
  AuthProvider,
  AuthSessionSnapshot,
  CallbackRequest,
  CallbackResult,
  ProviderSession,
  RefreshMode,
  SignOutResult,
} from "./types";
import { AuthRuntimeError } from "./types";

export const AUTH_SESSION_FENCE_PATH = "/auth/session-fence";

export interface AuthBrowserSessionFenceBridge {
  prepareSignIn(intendedReturn?: string): Promise<Readonly<{ redirectUrl: string }>>;
  publishSignOut(): Promise<void>;
  resolveSession(): Promise<AuthResolvedSession>;
}

export type AuthBrowserSessionFenceTransportDependencies = Readonly<{
  csrfToken: () => string | Promise<string>;
  fetch?: typeof globalThis.fetch;
}>;

/** Same-origin, no-store transport for the frozen three-operation Auth host. */
export function createAuthBrowserSessionFenceBridge(
  dependencies: AuthBrowserSessionFenceTransportDependencies,
): AuthBrowserSessionFenceBridge {
  const request = async (body: object): Promise<unknown> => {
    const csrfToken = await dependencies.csrfToken();
    if (!csrfToken) throw new Error("Auth CSRF token is unavailable");
    const response = await (dependencies.fetch ?? globalThis.fetch)(
      AUTH_SESSION_FENCE_PATH,
      {
        method: "POST",
        mode: "same-origin",
        credentials: "same-origin",
        cache: "no-store",
        headers: {
          accept: "application/json",
          "content-type": "application/json",
          "x-auth-csrf": csrfToken,
        },
        body: JSON.stringify(body),
      },
    );
    if (!response.ok) throw new Error("Auth session-fence request failed");
    return response.json();
  };

  return Object.freeze({
    async prepareSignIn(intendedReturn?: string) {
      const payload = await request(
        intendedReturn === undefined
          ? { operation: "PREPARE_SIGN_IN" }
          : { operation: "PREPARE_SIGN_IN", intendedReturn },
      );
      if (!isExactRecord(payload, ["redirectUrl"])) {
        throw new Error("Invalid PREPARE_SIGN_IN response");
      }
      return Object.freeze({ redirectUrl: safeRedirectUrl(payload.redirectUrl) });
    },
    async publishSignOut() {
      const payload = await request({ operation: "PUBLISH_SIGN_OUT" });
      if (!isExactRecord(payload, ["ok"]) || payload.ok !== true) {
        throw new Error("Invalid PUBLISH_SIGN_OUT response");
      }
    },
    async resolveSession() {
      const payload = await request({ operation: "RESOLVE_SESSION" });
      if (!isExactRecord(payload, ["state", "userReference"])) {
        throw new Error("Invalid RESOLVE_SESSION response");
      }
      if (payload.state === "UNAUTHENTICATED" && payload.userReference === null) {
        return Object.freeze({ state: "UNAUTHENTICATED", userReference: null });
      }
      if (
        payload.state === "AUTHENTICATED" &&
        typeof payload.userReference === "string" &&
        payload.userReference.length > 0
      ) {
        return Object.freeze({
          state: "AUTHENTICATED",
          userReference: payload.userReference,
        });
      }
      throw new Error("Invalid RESOLVE_SESSION response");
    },
  });
}

export type BrowserAuthAdapterDependencies = Readonly<{
  provider: AuthProvider;
  sessionFence: AuthBrowserSessionFenceBridge;
  tombstone?: BrowserLocalSignOutTombstone;
  navigateToProvider?: (url: string) => void | Promise<void>;
  now?: () => number;
}>;

/** Auth-owned browser construction; callers provide no low-level fence state. */
export function createBrowserAuthAdapter(
  dependencies: BrowserAuthAdapterDependencies,
): AuthAdapter {
  return new BrowserAuthAdapter(dependencies);
}

class BrowserAuthAdapter implements AuthAdapter {
  #machine = new AuthStateMachine();
  #beginPromise: Promise<void> | null = null;
  #refreshPromise: Promise<AuthSessionSnapshot> | null = null;
  #signOutPromise: Promise<SignOutResult> | null = null;
  #operationEpoch = 0;
  #verificationEpoch = 0;
  #tombstone: BrowserLocalSignOutTombstone;

  constructor(private readonly dependencies: BrowserAuthAdapterDependencies) {
    this.#tombstone = dependencies.tombstone ?? new BrowserLocalSignOutTombstone();
    dependencies.provider.onSessionChange((event, session) => {
      if (event === "SIGNED_OUT" || !session) {
        this.#verificationEpoch += 1;
        if (!this.#signOutPromise) this.#transitionUnauthenticated();
        return;
      }
      if (this.#beginPromise || this.#refreshPromise || this.#signOutPromise) return;
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
    this.#machine.transition("SIGN_IN_PENDING");
    this.#beginPromise = this.#begin(intendedReturn).finally(() => {
      this.#beginPromise = null;
    });
    return this.#beginPromise;
  }

  async #begin(intendedReturn?: string) {
    try {
      const { redirectUrl } = await this.dependencies.sessionFence.prepareSignIn(
        intendedReturn,
      );
      await (this.dependencies.navigateToProvider ?? defaultNavigate)(
        safeRedirectUrl(redirectUrl),
      );
    } catch (error) {
      this.#machine.transition("RECOVERABLE_ERROR");
      throw browserError(error, "TEMPORARY_PROVIDER_FAILURE");
    }
  }

  processCallback(request: CallbackRequest): Promise<CallbackResult> {
    void request;
    return Promise.reject(new AuthRuntimeError("CONFIGURATION_UNAVAILABLE", true));
  }

  getSessionSnapshot() {
    return this.#machine.snapshot;
  }

  subscribeToSessionChanges(
    listener: (snapshot: AuthSessionSnapshot) => void,
  ): () => void {
    return this.#machine.subscribe(listener);
  }

  async getAccessTokenForApiRequest(): Promise<string> {
    if (this.#machine.snapshot.state !== "AUTHENTICATED" || this.#tombstone.isActive()) {
      await this.#denyCurrentSession();
      throw new AuthRuntimeError("SESSION_EXPIRED");
    }
    const operationEpoch = this.#operationEpoch;
    const verificationEpoch = this.#verificationEpoch;
    let session = await this.#resolveEligibleSession(operationEpoch, verificationEpoch);
    if (!session) {
      await this.#denyCurrentSession();
      throw new AuthRuntimeError("SESSION_EXPIRED");
    }
    if (session.expiresAt - this.#now() <= 60_000) {
      await this.#refresh(
        session.expiresAt > this.#now() ? "PROVEN_CREDENTIAL" : "UNPROVEN_CREDENTIAL",
      );
      session = await this.dependencies.provider.getSession();
    }
    if (
      !session ||
      this.#machine.snapshot.state !== "AUTHENTICATED" ||
      session.userReference !== this.#machine.snapshot.userReference ||
      this.#tombstone.isActive() ||
      operationEpoch !== this.#operationEpoch ||
      verificationEpoch !== this.#verificationEpoch
    ) {
      await this.#denyCurrentSession();
      throw new AuthRuntimeError("SESSION_EXPIRED");
    }
    return session.accessToken;
  }

  refreshSession() {
    return this.#refresh();
  }

  #refresh(forcedMode?: RefreshMode): Promise<AuthSessionSnapshot> {
    if (this.#refreshPromise) return this.#refreshPromise;
    this.#refreshPromise = this.#performRefresh(forcedMode).finally(() => {
      this.#refreshPromise = null;
    });
    return this.#refreshPromise;
  }

  async #performRefresh(forcedMode?: RefreshMode): Promise<AuthSessionSnapshot> {
    const operationEpoch = this.#operationEpoch;
    const verificationEpoch = this.#verificationEpoch;
    if (this.#machine.snapshot.state !== "AUTHENTICATED" || this.#tombstone.isActive()) {
      await this.#denyCurrentSession();
      throw new AuthRuntimeError("SESSION_EXPIRED");
    }
    const current = await this.#resolveEligibleSession(operationEpoch, verificationEpoch);
    if (!current) {
      await this.#denyCurrentSession();
      throw new AuthRuntimeError("SESSION_EXPIRED");
    }
    const mode =
      forcedMode ??
      (current.expiresAt > this.#now() ? "PROVEN_CREDENTIAL" : "UNPROVEN_CREDENTIAL");
    this.#machine.transition("REFRESH_PENDING", {
      refreshMode: mode,
      userReference: current.userReference,
    });
    try {
      const refreshed = await this.dependencies.provider.refresh();
      if (operationEpoch !== this.#operationEpoch) {
        await this.dependencies.provider.signOutLocal().catch(() => undefined);
        return this.#machine.snapshot;
      }
      const eligible = await this.#resolveEligibleSession(
        operationEpoch,
        verificationEpoch,
      );
      if (!eligible || eligible.userReference !== refreshed.userReference) {
        await this.#denyCurrentSession();
        throw new AuthRuntimeError("REFRESH_FAILED");
      }
      return this.#machine.transition("AUTHENTICATED", {
        userReference: eligible.userReference,
      });
    } catch (error) {
      if (operationEpoch !== this.#operationEpoch) return this.#machine.snapshot;
      this.#transitionFailClosed();
      throw browserError(error, "REFRESH_FAILED");
    }
  }

  signOut(): Promise<SignOutResult> {
    if (this.#signOutPromise) return this.#signOutPromise;
    let tombstone: Promise<void>;
    try {
      tombstone = Promise.resolve(this.#tombstone.create());
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
    if (failed) {
      return { ok: false, error: "SIGN_OUT_FAILED", destination: "/" };
    }
    this.#transitionUnauthenticated();
    return { ok: true, error: null, destination: "/" };
  }

  async #resolveProviderSignal(provisionalSession: ProviderSession) {
    const verificationEpoch = ++this.#verificationEpoch;
    const operationEpoch = this.#operationEpoch;
    try {
      this.#machine.transition("INITIALIZING");
    } catch {
      return;
    }
    const session = await this.#resolveEligibleSession(
      operationEpoch,
      verificationEpoch,
    );
    if (
      operationEpoch !== this.#operationEpoch ||
      verificationEpoch !== this.#verificationEpoch ||
      this.#beginPromise ||
      this.#refreshPromise ||
      this.#signOutPromise
    ) {
      return;
    }
    if (session?.userReference === provisionalSession.userReference) {
      this.#machine.transition("AUTHENTICATED", {
        userReference: session.userReference,
      });
      return;
    }
    await this.dependencies.provider.signOutLocal().catch(() => undefined);
    this.#transitionUnauthenticated();
  }

  async #resolveEligibleSession(
    operationEpoch: number,
    verificationEpoch: number,
  ): Promise<ProviderSession | null> {
    const resolved = await this.dependencies.sessionFence.resolveSession().catch(() => null);
    if (
      !resolved ||
      resolved.state !== "AUTHENTICATED" ||
      operationEpoch !== this.#operationEpoch ||
      verificationEpoch !== this.#verificationEpoch
    ) {
      return null;
    }
    const session = await this.dependencies.provider.getSession().catch(() => null);
    if (
      !session ||
      session.userReference !== resolved.userReference ||
      operationEpoch !== this.#operationEpoch ||
      verificationEpoch !== this.#verificationEpoch
    ) {
      return null;
    }
    return this.#tombstone.isActive() ? null : session;
  }

  async #denyCurrentSession() {
    await this.dependencies.provider.signOutLocal().catch(() => undefined);
    this.#transitionFailClosed();
  }

  #transitionFailClosed() {
    try {
      this.#machine.transition("TERMINAL_SESSION_ERROR");
    } catch {
      // Invalid ordering already fails closed.
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

function isExactRecord(
  input: unknown,
  expectedKeys: readonly string[],
): input is Record<string, unknown> {
  if (!input || typeof input !== "object" || Array.isArray(input)) return false;
  const keys = Object.keys(input);
  return keys.length === expectedKeys.length && expectedKeys.every((key) => keys.includes(key));
}

function safeRedirectUrl(input: unknown) {
  if (typeof input !== "string") throw new Error("Invalid provider redirect URL");
  const url = new URL(input);
  if (url.protocol !== "https:" && url.protocol !== "http:") {
    throw new Error("Invalid provider redirect URL");
  }
  return url.toString();
}

function defaultNavigate(url: string) {
  globalThis.location.assign(url);
}

function browserError(error: unknown, fallback: "TEMPORARY_PROVIDER_FAILURE" | "REFRESH_FAILED") {
  return error instanceof AuthRuntimeError ? error : new AuthRuntimeError(fallback, true);
}
