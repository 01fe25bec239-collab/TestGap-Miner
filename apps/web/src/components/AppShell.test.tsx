import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";
import type { AuthAdapter, AuthSessionSnapshot } from "@/auth";
import AppShell from "@/components/AppShell";
import AuthSessionProvider from "@/providers/AuthSessionProvider";
import { renderWithTheme } from "@/test/renderWithTheme";

const UNAUTHENTICATED: AuthSessionSnapshot = Object.freeze({
  state: "UNAUTHENTICATED",
  userReference: null,
  refreshMode: null,
  canRenderProtectedContent: false,
  canMakeApiRequest: false,
});

const unauthenticatedAdapter: AuthAdapter = {
  beginSignIn: async () => {},
  processCallback: async () => {
    throw new Error("unused");
  },
  getSessionSnapshot: () => UNAUTHENTICATED,
  subscribeToSessionChanges: (listener) => {
    listener(UNAUTHENTICATED);
    return () => {};
  },
  getAccessTokenForApiRequest: async () => {
    throw new Error("unused");
  },
  refreshSession: async () => UNAUTHENTICATED,
  signOut: async () => ({ ok: true, error: null, destination: "/" }),
};

function renderShell(children: ReactNode) {
  return renderWithTheme(
    <AuthSessionProvider adapter={unauthenticatedAdapter}>
      <AppShell>{children}</AppShell>
    </AuthSessionProvider>,
  );
}

describe("AppShell", () => {
  it("exposes its identity, landmarks, skip link, and child content", () => {
    renderShell("Regression test content");

    expect(screen.getByText("TestGap Miner")).toBeInTheDocument();
    expect(screen.getByRole("banner")).toBeInTheDocument();
    expect(
      screen.getAllByRole("navigation", { name: "Primary navigation" }).length,
    ).toBeGreaterThan(0);

    const main = screen.getByRole("main");
    expect(main).toHaveAttribute("id", "main-content");
    expect(within(main).getByText("Regression test content")).toBeInTheDocument();

    expect(screen.getByRole("link", { name: "Skip to main content" })).toHaveAttribute(
      "href",
      "#main-content",
    );
  });

  it("marks Overview as the current implemented destination", () => {
    renderShell("Content");

    const overviewLinks = screen.getAllByRole("link", { name: "Overview" });
    expect(overviewLinks.length).toBeGreaterThan(0);
    for (const link of overviewLinks) {
      expect(link).toHaveAttribute("href", "/");
      expect(link).toHaveAttribute("aria-current", "page");
    }
  });

  it("presents planned navigation without interactive destinations", () => {
    renderShell("Content");

    for (const label of ["Runs", "Evidence", "Benchmarks"]) {
      expect(
        screen
          .getAllByText(label)
          .some((item) => item.closest("li")?.textContent?.includes("Planned")),
      ).toBe(true);
      expect(screen.queryByRole("link", { name: label, hidden: true })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: label, hidden: true })).not.toBeInTheDocument();
    }
  });

  it("opens and closes the mobile navigation through its named control", async () => {
    const user = userEvent.setup();
    renderShell("Content");

    const menuButton = screen.getByRole("button", { name: "Open primary navigation" });
    expect(menuButton).toHaveAttribute("aria-expanded", "false");
    expect(menuButton).toHaveAttribute("aria-controls", "mobile-primary-navigation");

    await user.click(menuButton);
    expect(menuButton).toHaveAttribute("aria-expanded", "true");
    expect(menuButton).toHaveAccessibleName("Close primary navigation");

    await user.click(menuButton);
    expect(menuButton).toHaveAttribute("aria-expanded", "false");
  });

  it("carries the authentication control in the shell header", () => {
    renderShell("Content");

    const header = screen.getByRole("banner");
    expect(
      within(header).getByRole("button", { name: "Sign in with GitHub" }),
    ).toBeInTheDocument();
  });

  it("does not expose unauthorized product controls", () => {
    renderShell("Content");

    const prohibited = /upload|execute|approval|auto[ -]?merge|edit production/i;
    expect(screen.queryByRole("button", { name: prohibited })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: prohibited })).not.toBeInTheDocument();
  });
});
