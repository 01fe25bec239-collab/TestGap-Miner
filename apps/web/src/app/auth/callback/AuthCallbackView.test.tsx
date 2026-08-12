import { screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import AuthCallbackView from "@/app/auth/callback/AuthCallbackView";
import { renderWithTheme } from "@/test/renderWithTheme";
import { completeAuthCallback } from "./actions";
import { resolveBrowserAuthSession } from "@/providers/AuthSessionProvider";
import { replaceWithSafeDestination } from "@/providers/navigation";

vi.mock("./actions", () => ({ completeAuthCallback: vi.fn() }));
vi.mock("@/providers/AuthSessionProvider", () => ({ resolveBrowserAuthSession: vi.fn() }));
vi.mock("@/providers/navigation", () => ({ replaceWithSafeDestination: vi.fn() }));

const process = vi.mocked(completeAuthCallback);
const resolveSession = vi.mocked(resolveBrowserAuthSession);
const navigate = vi.mocked(replaceWithSafeDestination);

const CALLBACK_QUERY = "?code=provider-authorization-code&sb_flow_id=flowabcdefgh";

/** Never rendered, never stored, never logged. */
const FORBIDDEN_TEXT = [
  "provider-authorization-code",
  "flowabcdefgh",
  "INVALID_CALLBACK",
  "STATE_VALIDATION_FAILED",
  "PKCE_VALIDATION_FAILED",
  "SESSION_EXCHANGE_FAILED",
  "SIGN_IN_FAILED",
  "code=",
];

function expectSafeFailurePresentation() {
  expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Sign-in failed");
  expect(screen.getByRole("alert")).toHaveTextContent("We could not sign you in");
  expect(screen.queryByText(/successful|sign-in complete|welcome back/i)).not.toBeInTheDocument();

  const rendered = document.body.textContent ?? "";
  for (const term of FORBIDDEN_TEXT) expect(rendered).not.toContain(term);
}

beforeEach(() => {
  vi.clearAllMocks();
  resolveSession.mockResolvedValue({ state: "AUTHENTICATED", userReference: "user-reference" });
  window.history.replaceState(null, "", `/auth/callback${CALLBACK_QUERY}`);
});

afterEach(() => {
  window.history.replaceState(null, "", "/");
});

describe("/auth/callback presentation", () => {
  it("shows accessible progress while Auth is processing the callback", () => {
    process.mockReturnValue(new Promise(() => {}));
    renderWithTheme(<AuthCallbackView />);

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Completing sign-in");
    expect(screen.getByRole("status")).toHaveTextContent("Verifying your sign-in with GitHub");
    expect(navigate).not.toHaveBeenCalled();
  });

  it("relays the callback to Auth and removes it from browser history", async () => {
    const replaceState = vi.spyOn(window.history, "replaceState");
    process.mockResolvedValue({ ok: true, destination: "/" });

    renderWithTheme(<AuthCallbackView />);
    await screen.findByText("Sign-in complete. Taking you to TestGap Miner.");

    expect(process).toHaveBeenCalledWith(CALLBACK_QUERY);
    expect(replaceState).toHaveBeenCalledWith(null, "", "/auth/callback");
    expect(window.location.search).toBe("");
    replaceState.mockRestore();
  });

  it("navigates only to the destination Auth returned", async () => {
    process.mockResolvedValue({ ok: true, destination: "/" });

    renderWithTheme(<AuthCallbackView />);
    await screen.findByText("Sign-in complete. Taking you to TestGap Miner.");

    expect(navigate).toHaveBeenCalledTimes(1);
    expect(navigate).toHaveBeenCalledWith("/");
  });

  it("does not treat callback ok:true alone as authenticated success", async () => {
    resolveSession.mockReturnValue(new Promise(() => {}));
    process.mockResolvedValue({ ok: true, destination: "/" });

    renderWithTheme(<AuthCallbackView />);
    await screen.findByText("Verifying your sign-in with GitHub. This only takes a moment.");

    expect(screen.queryByText(/sign-in complete/i)).not.toBeInTheDocument();
    expect(navigate).not.toHaveBeenCalled();
  });

  it("fails closed when callback succeeds but RESOLVE_SESSION is unauthenticated", async () => {
    resolveSession.mockResolvedValue({ state: "UNAUTHENTICATED", userReference: null });
    process.mockResolvedValue({ ok: true, destination: "/" });

    renderWithTheme(<AuthCallbackView />);
    await screen.findByRole("alert");

    expectSafeFailurePresentation();
    expect(navigate).not.toHaveBeenCalled();
  });

  it("presents one safe failure experience without diagnostics", async () => {
    process.mockResolvedValue({ ok: false, destination: null });

    renderWithTheme(<AuthCallbackView />);
    await screen.findByRole("alert");

    expectSafeFailurePresentation();
    expect(navigate).not.toHaveBeenCalled();
    expect(screen.getByRole("link", { name: "Return to TestGap Miner" })).toHaveAttribute(
      "href",
      "/",
    );
  });

  it("never claims success when Auth rejected the callback but preserved a session", async () => {
    process.mockResolvedValue({ ok: false, destination: "/" });

    renderWithTheme(<AuthCallbackView />);
    await screen.findByRole("alert");

    expectSafeFailurePresentation();
    expect(navigate).not.toHaveBeenCalled();
    expect(screen.getByRole("link", { name: "Return to TestGap Miner" })).toHaveAttribute(
      "href",
      "/",
    );
  });

  it("fails closed when the callback request itself cannot be completed", async () => {
    process.mockRejectedValue(new Error("transport failure"));

    renderWithTheme(<AuthCallbackView />);
    await screen.findByRole("alert");

    expectSafeFailurePresentation();
    expect(navigate).not.toHaveBeenCalled();
  });
});
