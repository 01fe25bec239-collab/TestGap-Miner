import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { AuthAdapter, AuthSessionSnapshot } from "@/auth";
import Home from "@/app/page";
import AuthSessionProvider from "@/providers/AuthSessionProvider";
import { renderWithTheme } from "@/test/renderWithTheme";

function snapshotAdapter(snapshot: AuthSessionSnapshot): AuthAdapter {
  return {
    beginSignIn: async () => {},
    processCallback: async () => {
      throw new Error("unused");
    },
    getSessionSnapshot: () => snapshot,
    subscribeToSessionChanges: (listener) => {
      listener(snapshot);
      return () => {};
    },
    getAccessTokenForApiRequest: async () => {
      throw new Error("unused");
    },
    refreshSession: async () => snapshot,
    signOut: async () => ({ ok: true, error: null, destination: "/" }),
  };
}

const AUTHENTICATED: AuthSessionSnapshot = Object.freeze({
  state: "AUTHENTICATED",
  userReference: "3f1c2d94-0a7b-4e55-9c11-6b2f8de41a03",
  refreshMode: null,
  canRenderProtectedContent: true,
  canMakeApiRequest: true,
});

const UNAUTHENTICATED: AuthSessionSnapshot = Object.freeze({
  state: "UNAUTHENTICATED",
  userReference: null,
  refreshMode: null,
  canRenderProtectedContent: false,
  canMakeApiRequest: false,
});

function renderOverview(snapshot: AuthSessionSnapshot) {
  return renderWithTheme(
    <AuthSessionProvider adapter={snapshotAdapter(snapshot)}>
      <Home />
    </AuthSessionProvider>,
  );
}

describe("Overview page", () => {
  it("identifies the page and reports the frontend foundation truthfully", () => {
    renderOverview(AUTHENTICATED);

    const headings = screen.getAllByRole("heading", { level: 1 });
    expect(headings).toHaveLength(1);
    expect(headings[0]).toHaveTextContent("TestGap Miner");
    expect(screen.getByText("Frontend foundation implemented")).toBeInTheDocument();

    for (const title of ["Application shell", "Authentication"]) {
      const card = screen.getByRole("heading", { name: title }).closest("div");
      expect(card).not.toBeNull();
      expect(within(card!).getByText("Implemented")).toBeInTheDocument();
    }

    const api = screen.getByRole("heading", { name: "API connection" }).closest("div");
    expect(api).not.toBeNull();
    expect(within(api!).getByText("Not connected")).toBeInTheDocument();

    const planned = screen.getByRole("heading", { name: "Runs and Evidence" }).closest("div");
    expect(planned).not.toBeNull();
    expect(within(planned!).getByText("Planned")).toBeInTheDocument();
  });

  it("keeps the foundation status behind Auth proof", () => {
    renderOverview(UNAUTHENTICATED);

    expect(screen.getByRole("heading", { name: "Foundation status" })).toBeInTheDocument();
    expect(screen.getByText("Sign in with GitHub to view this content.")).toBeInTheDocument();
    for (const title of ["Application shell", "Authentication", "API connection"]) {
      expect(screen.queryByRole("heading", { name: title })).not.toBeInTheDocument();
    }
  });

  it("does not fabricate product data or expose unauthorized controls", () => {
    renderOverview(AUTHENTICATED);

    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.queryByText(/run #?\d+|\b(?:passed|failed) tests?\b/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/repository/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/benchmark value|\b\d+(?:\.\d+)?%/i)).not.toBeInTheDocument();

    for (const name of [
      /submit (?:a )?run|run submission/i,
      /approve|approval/i,
      /auto[ -]?merge/i,
    ]) {
      expect(screen.queryByRole("button", { name })).not.toBeInTheDocument();
    }
  });
});
