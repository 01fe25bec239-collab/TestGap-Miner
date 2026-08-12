import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { act } from "react";
import { describe, expect, it, vi } from "vitest";
import {
  AuthRuntimeError,
  BrowserLocalSignOutTombstone,
  createBrowserAuthAdapter,
  type AuthAdapter,
  type AuthBrowserSessionFenceBridge,
  type AuthProvider,
  type AuthResolvedSession,
  type ProviderSession,
} from "@/auth";
import AppShell from "@/components/AppShell";
import ProtectedRegion from "@/components/ProtectedRegion";
import AuthSessionProvider from "@/providers/AuthSessionProvider";
import { renderWithTheme } from "@/test/renderWithTheme";

type SessionListener = Parameters<AuthProvider["onSessionChange"]>[0];
type ProviderSessionEvent = Parameters<SessionListener>[0];

const USER_REFERENCE = "3f1c2d94-0a7b-4e55-9c11-6b2f8de41a03";
const PROTECTED_CONTENT = "Protected dashboard content";

/** Internal Auth vocabulary that must never reach a browser. */
const INTERNAL_VOCABULARY = [
  "INVALID_CALLBACK",
  "STATE_VALIDATION_FAILED",
  "PKCE_VALIDATION_FAILED",
  "SESSION_EXCHANGE_FAILED",
  "SIGN_IN_FAILED",
  "RECOVERABLE_ERROR",
  "TERMINAL_SESSION_ERROR",
  "REFRESH_FAILED",
  "UNPROVEN_CREDENTIAL",
  "access_token",
  "refresh_token",
];

function providerSession(expiresAt: number): ProviderSession {
  return { userReference: USER_REFERENCE, accessToken: "provider-issued-value", expiresAt };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

function createTestAuthRuntime(
  overrides: Partial<AuthProvider> = {},
  fenceOverrides: Partial<AuthBrowserSessionFenceBridge> = {},
) {
  const listeners = new Set<SessionListener>();
  let current: ProviderSession | null = null;

  const provider: AuthProvider = {
    beginGitHubOAuth: vi.fn(async () => ({
      redirectUrl: "https://provider.test/authorize?client_id=test",
      flowId: "flow-abcdefgh",
    })),
    exchangeCode: vi.fn(async () => {
      throw new AuthRuntimeError("SESSION_EXCHANGE_FAILED");
    }),
    getSession: vi.fn(async () => current),
    validateCurrentUser: vi.fn(async () =>
      current ? { userReference: current.userReference } : null,
    ),
    validatePreExistingSession: vi.fn(async () => null),
    refresh: vi.fn(async () => {
      current = providerSession(Date.now() + 600_000);
      return current;
    }),
    signOutLocal: vi.fn(async () => {
      current = null;
    }),
    onSessionChange: (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    ...overrides,
  };

  const redirectToProvider = vi.fn();
  const sessionFence: AuthBrowserSessionFenceBridge = {
    prepareSignIn: vi.fn(async () => ({
      redirectUrl: "https://provider.test/authorize?client_id=test",
    })),
    publishSignOut: vi.fn(async () => {}),
    resolveSession: vi.fn(async (): Promise<AuthResolvedSession> =>
      current
        ? { state: "AUTHENTICATED", userReference: current.userReference }
        : { state: "UNAUTHENTICATED", userReference: null },
    ),
    ...fenceOverrides,
  };
  const adapter = createBrowserAuthAdapter({
    provider,
    sessionFence,
    tombstone: new BrowserLocalSignOutTombstone("http://localhost:3000", { cookie: "" }),
    navigateToProvider: redirectToProvider,
  });

  return {
    adapter,
    provider,
    sessionFence,
    redirectToProvider,
    setProviderSession(session: ProviderSession | null) {
      current = session;
    },
    emit(event: ProviderSessionEvent, session: ProviderSession | null) {
      current = session;
      act(() => {
        for (const listener of listeners) listener(event, session);
      });
    },
  };
}

async function authenticate(
  runtime: ReturnType<typeof createTestAuthRuntime>,
  expiresAt = Date.now() + 600_000,
) {
  runtime.emit("SIGNED_IN", providerSession(expiresAt));
  await waitFor(() => expect(runtime.adapter.getSessionSnapshot().state).toBe("AUTHENTICATED"));
}

function renderDashboard(adapter: AuthAdapter) {
  return renderWithTheme(
    <AuthSessionProvider adapter={adapter}>
      <AppShell>
        <ProtectedRegion>
          <p>{PROTECTED_CONTENT}</p>
        </ProtectedRegion>
      </AppShell>
    </AuthSessionProvider>,
  );
}

function expectNoProtectedContent() {
  expect(screen.queryByText(PROTECTED_CONTENT)).not.toBeInTheDocument();
  expect(screen.queryByLabelText(`Signed in as ${USER_REFERENCE}`)).not.toBeInTheDocument();
}

function expectNoInternalVocabulary() {
  const rendered = document.body.textContent ?? "";
  for (const term of INTERNAL_VOCABULARY) expect(rendered).not.toContain(term);
}

describe("Auth session integration", () => {
  it("hides protected content and reports progress while INITIALIZING", () => {
    const runtime = createTestAuthRuntime();
    renderDashboard(runtime.adapter);

    expect(runtime.adapter.getSessionSnapshot().state).toBe("INITIALIZING");
    expectNoProtectedContent();
    expect(screen.getAllByRole("status").length).toBeGreaterThan(0);
    expect(screen.getByText("Checking your sign-in status")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sign in with GitHub" })).not.toBeInTheDocument();
  });

  it("initializes from the Auth snapshot without an unauthenticated flash", async () => {
    const runtime = createTestAuthRuntime();
    runtime.emit("SIGNED_IN", providerSession(Date.now() + 600_000));

    renderDashboard(runtime.adapter);

    expectNoProtectedContent();
    await screen.findByText(PROTECTED_CONTENT);
    expect(screen.queryByRole("button", { name: "Sign in with GitHub" })).not.toBeInTheDocument();
  });

  it("offers a keyboard-operable GitHub sign-in when UNAUTHENTICATED", async () => {
    const user = userEvent.setup();
    const runtime = createTestAuthRuntime();
    renderDashboard(runtime.adapter);
    runtime.emit("SIGNED_OUT", null);

    expectNoProtectedContent();
    expect(screen.getByText("Sign in with GitHub to view this content.")).toBeInTheDocument();

    const signIn = screen.getByRole("button", { name: "Sign in with GitHub" });
    expect(signIn).toBeEnabled();

    signIn.focus();
    expect(signIn).toHaveFocus();
    await act(async () => {
      await user.keyboard("{Enter}");
    });

    expect(runtime.sessionFence.prepareSignIn).toHaveBeenCalledTimes(1);
    expect(runtime.provider.beginGitHubOAuth).not.toHaveBeenCalled();
    expect(runtime.adapter.getSessionSnapshot().state).toBe("SIGN_IN_PENDING");
  });

  it("presents SIGN_IN_PENDING, blocks duplicate attempts, and hands off to Auth", async () => {
    const user = userEvent.setup();
    const preparation = deferred<{ redirectUrl: string }>();
    const prepareSignIn = vi.fn(() => preparation.promise);
    const runtime = createTestAuthRuntime({}, { prepareSignIn });
    renderDashboard(runtime.adapter);
    runtime.emit("SIGNED_OUT", null);

    await user.click(screen.getByRole("button", { name: "Sign in with GitHub" }));

    const pendingButton = screen.getByRole("button", { name: "Sign in with GitHub" });
    expect(pendingButton).toBeDisabled();
    expect(screen.getByText("Taking you to GitHub to sign in")).toBeInTheDocument();
    expect(screen.getByText("Taking you to GitHub to sign in.")).toBeInTheDocument();
    expectNoProtectedContent();

    fireEvent.click(pendingButton);
    expect(prepareSignIn).toHaveBeenCalledTimes(1);
    expect(runtime.provider.beginGitHubOAuth).not.toHaveBeenCalled();

    await act(async () => {
      preparation.resolve({ redirectUrl: "https://provider.test/authorize" });
      await preparation.promise;
    });
    expect(runtime.redirectToProvider).toHaveBeenCalledWith("https://provider.test/authorize");
  });

  it("renders the authenticated shell with only safe presentation identity", async () => {
    const runtime = createTestAuthRuntime();
    renderDashboard(runtime.adapter);
    await authenticate(runtime);

    expect(screen.getByText(PROTECTED_CONTENT)).toBeInTheDocument();
    expect(screen.getByLabelText(`Signed in as ${USER_REFERENCE}`)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign out" })).toBeEnabled();
    expect(document.body.textContent).not.toContain("provider-issued-value");
  });

  it("keeps protected presentation only while a proven credential is refreshing", async () => {
    const refresh = deferred<ProviderSession>();
    const runtime = createTestAuthRuntime({ refresh: vi.fn(() => refresh.promise) });
    renderDashboard(runtime.adapter);
    await authenticate(runtime);

    let refreshing!: Promise<unknown>;
    await act(async () => {
      refreshing = runtime.adapter.refreshSession();
    });

    expect(runtime.adapter.getSessionSnapshot().refreshMode).toBe("PROVEN_CREDENTIAL");
    expect(screen.getByText(PROTECTED_CONTENT)).toBeInTheDocument();
    expect(screen.getByText("Reverifying your session")).toBeInTheDocument();
    expectNoInternalVocabulary();

    await act(async () => {
      refresh.resolve(providerSession(Date.now() + 600_000));
      await refreshing;
    });
    expect(screen.getByText(PROTECTED_CONTENT)).toBeInTheDocument();
  });

  it("removes protected presentation while a credential is unproven", async () => {
    const refresh = deferred<ProviderSession>();
    const runtime = createTestAuthRuntime({ refresh: vi.fn(() => refresh.promise) });
    renderDashboard(runtime.adapter);
    await authenticate(runtime, Date.now() - 1_000);

    let refreshing!: Promise<unknown>;
    await act(async () => {
      refreshing = runtime.adapter.refreshSession();
    });

    expect(runtime.adapter.getSessionSnapshot().refreshMode).toBe("UNPROVEN_CREDENTIAL");
    expect(runtime.adapter.getSessionSnapshot().canRenderProtectedContent).toBe(false);
    expectNoProtectedContent();
    expect(
      screen.getByText("Reverifying your session before showing this content."),
    ).toBeInTheDocument();
    expectNoInternalVocabulary();

    await act(async () => {
      refresh.resolve(providerSession(Date.now() + 600_000));
      await refreshing;
    });
  });

  it("fails closed on sign-out and is not resurrected by a late Auth result", async () => {
    const user = userEvent.setup();
    const refresh = deferred<ProviderSession>();
    const signOut = deferred<void>();
    const runtime = createTestAuthRuntime({
      refresh: vi.fn(() => refresh.promise),
      signOutLocal: vi.fn(() => signOut.promise),
    });
    renderDashboard(runtime.adapter);
    await authenticate(runtime);

    let refreshing!: Promise<unknown>;
    await act(async () => {
      refreshing = runtime.adapter.refreshSession();
    });
    expect(screen.getByText(PROTECTED_CONTENT)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Sign out" }));
    expect(runtime.provider.signOutLocal).toHaveBeenCalledTimes(1);
    expect(runtime.adapter.getSessionSnapshot().state).toBe("SIGN_OUT_PENDING");
    expectNoProtectedContent();
    expect(screen.getByText("Signing out")).toBeInTheDocument();

    await act(async () => {
      refresh.resolve(providerSession(Date.now() + 600_000));
      signOut.resolve();
      await Promise.all([refreshing, signOut.promise]);
    });
    expectNoProtectedContent();
    expect(runtime.adapter.getSessionSnapshot().state).toBe("UNAUTHENTICATED");
    expectNoProtectedContent();
    expect(screen.getByRole("button", { name: "Sign in with GitHub" })).toBeEnabled();
  });

  it("signs out with the keyboard using the current-session host operation", async () => {
    const user = userEvent.setup();
    const runtime = createTestAuthRuntime();
    renderDashboard(runtime.adapter);
    await authenticate(runtime);

    const signOut = screen.getByRole("button", { name: "Sign out" });
    signOut.focus();
    expect(signOut).toHaveFocus();
    await act(async () => {
      await user.keyboard("{Enter}");
    });

    expect(runtime.sessionFence.publishSignOut).toHaveBeenCalledTimes(1);
    expect(runtime.provider.signOutLocal).toHaveBeenCalledTimes(1);
  });

  it("presents RECOVERABLE_ERROR with a supported retry and no diagnostics", async () => {
    const user = userEvent.setup();
    const prepareSignIn = vi
      .fn()
      .mockRejectedValueOnce(new AuthRuntimeError("TEMPORARY_PROVIDER_FAILURE", true))
      .mockResolvedValue({ redirectUrl: "https://provider.test/authorize" });
    const runtime = createTestAuthRuntime({}, { prepareSignIn });
    renderDashboard(runtime.adapter);
    runtime.emit("SIGNED_OUT", null);

    await user.click(screen.getByRole("button", { name: "Sign in with GitHub" }));

    expect(runtime.adapter.getSessionSnapshot().state).toBe("RECOVERABLE_ERROR");
    expect(screen.getByRole("alert")).toHaveTextContent("Sign-in failed");
    expect(screen.getByText("Sign-in failed, so this content is not available.")).toBeInTheDocument();
    expectNoProtectedContent();
    expectNoInternalVocabulary();

    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(prepareSignIn).toHaveBeenCalledTimes(2);
  });

  it("presents TERMINAL_SESSION_ERROR with sign-out as the only supported recovery", async () => {
    const runtime = createTestAuthRuntime({
      refresh: vi.fn(async () => {
        throw new AuthRuntimeError("REFRESH_FAILED");
      }),
    });
    renderDashboard(runtime.adapter);
    await authenticate(runtime);

    await act(async () => {
      await runtime.adapter.refreshSession().catch(() => undefined);
    });

    expect(runtime.adapter.getSessionSnapshot().state).toBe("TERMINAL_SESSION_ERROR");
    expect(screen.getByRole("alert")).toHaveTextContent("Your session ended");
    expect(screen.getByRole("button", { name: "Sign out" })).toBeEnabled();
    expect(screen.queryByRole("button", { name: "Try again" })).not.toBeInTheDocument();
    expectNoProtectedContent();
    expectNoInternalVocabulary();
  });

  it.each(["SIGNED_IN", "TOKEN_REFRESHED", "INITIAL_SESSION"] as const)(
    "keeps provider %s provisional until RESOLVE_SESSION",
    async (event) => {
      const resolution = deferred<AuthResolvedSession>();
      const runtime = createTestAuthRuntime({}, {
        resolveSession: vi.fn(() => resolution.promise),
      });
      renderDashboard(runtime.adapter);

      runtime.emit(event, providerSession(Date.now() + 600_000));
      expectNoProtectedContent();

      resolution.resolve({ state: "UNAUTHENTICATED", userReference: null });
      await waitFor(() =>
        expect(runtime.adapter.getSessionSnapshot().state).toBe("UNAUTHENTICATED"),
      );
      expectNoProtectedContent();
    },
  );

  it("unsubscribes from Auth session changes when it unmounts", () => {
    const runtime = createTestAuthRuntime();
    const unsubscribed = vi.fn();
    const observed: AuthAdapter = {
      beginSignIn: (intendedReturn) => runtime.adapter.beginSignIn(intendedReturn),
      processCallback: (request) => runtime.adapter.processCallback(request),
      getSessionSnapshot: () => runtime.adapter.getSessionSnapshot(),
      subscribeToSessionChanges: (listener) => {
        const unsubscribe = runtime.adapter.subscribeToSessionChanges(listener);
        return () => {
          unsubscribed();
          unsubscribe();
        };
      },
      getAccessTokenForApiRequest: () => runtime.adapter.getAccessTokenForApiRequest(),
      refreshSession: () => runtime.adapter.refreshSession(),
      signOut: () => runtime.adapter.signOut(),
    };

    const { unmount } = renderDashboard(observed);
    unmount();

    expect(unsubscribed).toHaveBeenCalledTimes(1);
    runtime.emit("SIGNED_IN", providerSession(Date.now() + 600_000));
    expect(screen.queryByText(PROTECTED_CONTENT)).not.toBeInTheDocument();
  });
});
