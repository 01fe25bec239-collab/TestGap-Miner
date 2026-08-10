export const AUTH_SESSION_STATES = [
  "INITIALIZING",
  "UNAUTHENTICATED",
  "SIGN_IN_PENDING",
  "CALLBACK_PROCESSING",
  "AUTHENTICATED",
  "REFRESH_PENDING",
  "SIGN_OUT_PENDING",
  "RECOVERABLE_ERROR",
  "TERMINAL_SESSION_ERROR",
] as const;

export type AuthSessionState = (typeof AUTH_SESSION_STATES)[number];
export type RefreshMode = "PROVEN_CREDENTIAL" | "UNPROVEN_CREDENTIAL";

export type AuthSessionSnapshot = Readonly<{
  state: AuthSessionState;
  userReference: string | null;
  refreshMode: RefreshMode | null;
  canRenderProtectedContent: boolean;
  canMakeApiRequest: boolean;
}>;

export type PublicAuthError =
  | "SIGN_IN_FAILED"
  | "USER_CANCELLED"
  | "PROVIDER_DENIED"
  | "SESSION_EXPIRED"
  | "REFRESH_FAILED"
  | "SIGN_OUT_FAILED"
  | "CONFIGURATION_UNAVAILABLE"
  | "TEMPORARY_PROVIDER_FAILURE";

export type InternalCallbackError =
  | "INVALID_CALLBACK"
  | "STATE_VALIDATION_FAILED"
  | "PKCE_VALIDATION_FAILED"
  | "SESSION_EXCHANGE_FAILED";

export type AuthSecurityEvent = Readonly<{
  classification: InternalCallbackError;
  sessionPreserved: boolean;
  callbackSuccess: false;
  rejectedCallbackDestinationUsed: false;
}>;

export type CallbackResult =
  | Readonly<{
      ok: true;
      snapshot: AuthSessionSnapshot;
      destination: string;
      duplicate: boolean;
    }>
  | Readonly<{
      ok: false;
      error: PublicAuthError;
      snapshot: AuthSessionSnapshot;
      destination: "/" | null;
    }>;

export type SignOutResult = Readonly<{
  ok: boolean;
  error: "SIGN_OUT_FAILED" | null;
  destination: "/";
}>;

export type CallbackRequest = Readonly<{
  url: string;
  correlationHandles: readonly string[];
}>;

export interface AuthAdapter {
  beginSignIn(intendedReturn?: string): Promise<void>;
  processCallback(request: CallbackRequest): Promise<CallbackResult>;
  getSessionSnapshot(): AuthSessionSnapshot;
  subscribeToSessionChanges(
    listener: (snapshot: AuthSessionSnapshot) => void,
  ): () => void;
  getAccessTokenForApiRequest(): Promise<string>;
  refreshSession(): Promise<AuthSessionSnapshot>;
  signOut(): Promise<SignOutResult>;
}

export type ProviderSession = Readonly<{
  userReference: string;
  accessToken: string;
  expiresAt: number;
}>;

export type ProviderCodeExchange = Readonly<{
  session: ProviderSession;
  prepareSessionCommit(): Promise<void>;
  commitSession(): Promise<void>;
  discardSession(): Promise<void>;
}>;

export type ProviderSessionEvent =
  | "INITIAL_SESSION"
  | "SIGNED_IN"
  | "SIGNED_OUT"
  | "TOKEN_REFRESHED"
  | "USER_UPDATED";

export interface AuthProvider {
  beginGitHubOAuth(callbackUrl: string): Promise<{
    redirectUrl: string;
    flowId: string;
  }>;
  exchangeCode(code: string, flowId: string): Promise<ProviderCodeExchange>;
  getSession(): Promise<ProviderSession | null>;
  validateCurrentUser(): Promise<{ userReference: string } | null>;
  validatePreExistingSession(
    session: ProviderSession,
  ): Promise<{ userReference: string } | null>;
  refresh(): Promise<ProviderSession>;
  signOutLocal(): Promise<void>;
  onSessionChange(
    listener: (event: ProviderSessionEvent, session: ProviderSession | null) => void,
  ): () => void;
}

export class AuthRuntimeError extends Error {
  constructor(
    readonly code: PublicAuthError | InternalCallbackError,
    readonly recoverable = false,
  ) {
    super("Authentication operation failed");
    this.name = "AuthRuntimeError";
  }
}
