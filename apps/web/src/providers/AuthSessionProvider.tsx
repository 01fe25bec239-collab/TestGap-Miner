"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  createAuthBrowserSessionFenceBridge,
  createAuthBrowserClient,
  createBrowserAuthAdapter,
  createSupabaseAuthProvider,
  type AuthAdapter,
  type AuthBrowserSessionFenceBridge,
  type AuthSessionSnapshot,
} from "@/auth";
import { AUTH_SIGN_IN_ROUTE } from "./authConfig";

/**
 * Presentation state before the browser Auth runtime exists. It mirrors the
 * Auth runtime's own initial snapshot and is replaced by the runtime snapshot
 * on the first subscription callback; the UI never advances it itself.
 */
const INITIAL_SNAPSHOT: AuthSessionSnapshot = Object.freeze({
  state: "INITIALIZING",
  userReference: null,
  refreshMode: null,
  canRenderProtectedContent: false,
  canMakeApiRequest: false,
});

async function requestAuthCsrfToken() {
  const issued = await fetch(AUTH_SIGN_IN_ROUTE, {
    credentials: "same-origin",
    cache: "no-store",
    headers: { accept: "application/json" },
  });
  if (!issued.ok) throw new Error("Sign-in could not be started");
  const payload: unknown = await issued.json();
  if (
    !payload ||
    typeof payload !== "object" ||
    typeof (payload as { csrfToken?: unknown }).csrfToken !== "string"
  ) {
    throw new Error("Sign-in could not be started");
  }
  return (payload as { csrfToken: string }).csrfToken;
}

let browserAdapter: AuthAdapter | null = null;
let browserSessionFence: AuthBrowserSessionFenceBridge | null = null;

function browserAuthSessionFence(): AuthBrowserSessionFenceBridge {
  return (browserSessionFence ??= createAuthBrowserSessionFenceBridge({
    csrfToken: requestAuthCsrfToken,
  }));
}

export function resolveBrowserAuthSession() {
  return browserAuthSessionFence().resolveSession();
}

function browserAuthAdapter(): AuthAdapter {
  if (browserAdapter) return browserAdapter;
  const origin = window.location.origin;
  const provider = createSupabaseAuthProvider(createAuthBrowserClient(origin));

  browserAdapter = createBrowserAuthAdapter({
    provider,
    sessionFence: browserAuthSessionFence(),
    navigateToProvider: (url) => {
      window.location.assign(url);
    },
  });
  return browserAdapter;
}

export type AuthSessionContextValue = Readonly<{
  snapshot: AuthSessionSnapshot;
  configured: boolean;
  signIn: () => void;
  signOut: () => void;
}>;

const AuthSessionContext = createContext<AuthSessionContextValue | null>(null);

export function useAuthSession(): AuthSessionContextValue {
  const value = useContext(AuthSessionContext);
  if (!value) throw new Error("useAuthSession requires AuthSessionProvider");
  return value;
}

/**
 * The browser Auth runtime cannot exist during server rendering, and a
 * misconfigured environment must degrade to a stated presentation rather than
 * a broken Dashboard.
 */
function resolveRuntime(providedAdapter?: AuthAdapter) {
  if (providedAdapter) return { adapter: providedAdapter, configured: true };
  if (typeof window === "undefined") return { adapter: null, configured: true };
  try {
    return { adapter: browserAuthAdapter(), configured: true };
  } catch {
    return { adapter: null, configured: false };
  }
}

export default function AuthSessionProvider({
  children,
  adapter: providedAdapter,
}: Readonly<{ children: ReactNode; adapter?: AuthAdapter }>) {
  const [{ adapter, configured }] = useState(() => resolveRuntime(providedAdapter));
  const [snapshot, setSnapshot] = useState<AuthSessionSnapshot>(
    () => adapter?.getSessionSnapshot() ?? INITIAL_SNAPSHOT,
  );

  useEffect(() => {
    if (!adapter) return;
    const unsubscribe = adapter.subscribeToSessionChanges(setSnapshot);
    return () => {
      unsubscribe();
    };
  }, [adapter]);

  const signIn = useCallback(() => {
    // A rejected attempt is reported through the Auth snapshot; the reason is
    // never surfaced to presentation.
    adapter?.beginSignIn().catch(() => undefined);
  }, [adapter]);

  const signOut = useCallback(() => {
    adapter?.signOut().catch(() => undefined);
  }, [adapter]);

  const value = useMemo(
    () => ({ snapshot, configured, signIn, signOut }),
    [snapshot, configured, signIn, signOut],
  );

  return <AuthSessionContext.Provider value={value}>{children}</AuthSessionContext.Provider>;
}
