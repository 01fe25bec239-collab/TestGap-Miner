import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Home from "@/app/page";
import { renderWithTheme } from "@/test/renderWithTheme";

describe("Overview page", () => {
  it("identifies the page and reports the frontend foundation truthfully", () => {
    renderWithTheme(<Home />);

    const headings = screen.getAllByRole("heading", { level: 1 });
    expect(headings).toHaveLength(1);
    expect(headings[0]).toHaveTextContent("TestGap Miner");
    expect(screen.getByText("Frontend foundation implemented")).toBeInTheDocument();

    const applicationShell = screen
      .getByRole("heading", { name: "Application shell" })
      .closest("div");
    expect(applicationShell).not.toBeNull();
    expect(within(applicationShell!).getByText("Implemented")).toBeInTheDocument();

    for (const title of ["Authentication", "API connection"]) {
      const status = screen.getByRole("heading", { name: title }).closest("div");
      expect(status).not.toBeNull();
      expect(within(status!).getByText("Not connected")).toBeInTheDocument();
    }

    const planned = screen.getByRole("heading", { name: "Runs and Evidence" }).closest("div");
    expect(planned).not.toBeNull();
    expect(within(planned!).getByText("Planned")).toBeInTheDocument();
  });

  it("does not fabricate product data or expose unauthorized controls", () => {
    renderWithTheme(<Home />);

    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.queryByText(/run #?\d+|\b(?:passed|failed) tests?\b/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/repository/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/benchmark value|\b\d+(?:\.\d+)?%/i)).not.toBeInTheDocument();

    for (const name of [
      /sign[ -]?in/i,
      /submit (?:a )?run|run submission/i,
      /approve|approval/i,
      /auto[ -]?merge/i,
    ]) {
      expect(screen.queryByRole("button", { name })).not.toBeInTheDocument();
    }
  });
});
