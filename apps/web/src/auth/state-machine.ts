import type {
  AuthSessionSnapshot,
  AuthSessionState,
  RefreshMode,
} from "./types";

const TRANSITIONS: Readonly<Record<AuthSessionState, readonly AuthSessionState[]>> = {
  INITIALIZING: [
    "AUTHENTICATED",
    "UNAUTHENTICATED",
    "CALLBACK_PROCESSING",
    "SIGN_OUT_PENDING",
    "TERMINAL_SESSION_ERROR",
  ],
  UNAUTHENTICATED: ["SIGN_IN_PENDING", "CALLBACK_PROCESSING", "INITIALIZING", "AUTHENTICATED"],
  SIGN_IN_PENDING: [
    "CALLBACK_PROCESSING",
    "UNAUTHENTICATED",
    "RECOVERABLE_ERROR",
    "TERMINAL_SESSION_ERROR",
    "SIGN_OUT_PENDING",
  ],
  CALLBACK_PROCESSING: [
    "AUTHENTICATED",
    "UNAUTHENTICATED",
    "RECOVERABLE_ERROR",
    "TERMINAL_SESSION_ERROR",
    "SIGN_OUT_PENDING",
  ],
  AUTHENTICATED: [
    "CALLBACK_PROCESSING",
    "REFRESH_PENDING",
    "SIGN_OUT_PENDING",
    "UNAUTHENTICATED",
    "TERMINAL_SESSION_ERROR",
  ],
  REFRESH_PENDING: [
    "AUTHENTICATED",
    "UNAUTHENTICATED",
    "RECOVERABLE_ERROR",
    "TERMINAL_SESSION_ERROR",
    "SIGN_OUT_PENDING",
  ],
  SIGN_OUT_PENDING: ["UNAUTHENTICATED"],
  RECOVERABLE_ERROR: [
    "SIGN_IN_PENDING",
    "CALLBACK_PROCESSING",
    "UNAUTHENTICATED",
    "INITIALIZING",
    "AUTHENTICATED",
    "SIGN_OUT_PENDING",
  ],
  TERMINAL_SESSION_ERROR: ["UNAUTHENTICATED", "AUTHENTICATED", "SIGN_OUT_PENDING"],
};

export class InvalidAuthTransition extends Error {
  constructor(from: AuthSessionState, to: AuthSessionState) {
    super(`Invalid Auth state transition: ${from} -> ${to}`);
    this.name = "InvalidAuthTransition";
  }
}

export class AuthStateMachine {
  #state: AuthSessionState = "INITIALIZING";
  #userReference: string | null = null;
  #refreshMode: RefreshMode | null = null;
  #listeners = new Set<(snapshot: AuthSessionSnapshot) => void>();

  get snapshot(): AuthSessionSnapshot {
    const protectedContent =
      this.#state === "AUTHENTICATED" ||
      (this.#state === "REFRESH_PENDING" && this.#refreshMode === "PROVEN_CREDENTIAL");

    return Object.freeze({
      state: this.#state,
      userReference: protectedContent ? this.#userReference : null,
      refreshMode: this.#state === "REFRESH_PENDING" ? this.#refreshMode : null,
      canRenderProtectedContent: protectedContent,
      canMakeApiRequest: this.#state === "AUTHENTICATED",
    });
  }

  transition(
    next: AuthSessionState,
    options: { userReference?: string | null; refreshMode?: RefreshMode } = {},
  ): AuthSessionSnapshot {
    if (next === this.#state) {
      if (
        next === "REFRESH_PENDING" &&
        this.#refreshMode === "PROVEN_CREDENTIAL" &&
        options.refreshMode === "UNPROVEN_CREDENTIAL"
      ) {
        this.#refreshMode = "UNPROVEN_CREDENTIAL";
        this.#userReference = null;
        this.#emit();
      }
      return this.snapshot;
    }

    if (!TRANSITIONS[this.#state].includes(next)) {
      const previous = this.#state;
      this.#state = "TERMINAL_SESSION_ERROR";
      this.#userReference = null;
      this.#refreshMode = null;
      this.#emit();
      throw new InvalidAuthTransition(previous, next);
    }

    this.#state = next;
    this.#refreshMode = next === "REFRESH_PENDING" ? options.refreshMode ?? null : null;
    this.#userReference =
      next === "AUTHENTICATED" ||
      (next === "REFRESH_PENDING" && this.#refreshMode === "PROVEN_CREDENTIAL")
        ? options.userReference ?? this.#userReference
        : null;

    if (next === "REFRESH_PENDING" && !this.#refreshMode) {
      this.#state = "TERMINAL_SESSION_ERROR";
      this.#userReference = null;
      this.#emit();
      throw new InvalidAuthTransition("AUTHENTICATED", "REFRESH_PENDING");
    }

    this.#emit();
    return this.snapshot;
  }

  subscribe(listener: (snapshot: AuthSessionSnapshot) => void): () => void {
    this.#listeners.add(listener);
    listener(this.snapshot);
    return () => this.#listeners.delete(listener);
  }

  #emit() {
    const snapshot = this.snapshot;
    for (const listener of this.#listeners) listener(snapshot);
  }
}
