import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import AppShell from "@/components/AppShell";
import { renderWithTheme } from "@/test/renderWithTheme";

describe("AppShell", () => {
  it("exposes its identity, landmarks, skip link, and child content", () => {
    renderWithTheme(<AppShell>Regression test content</AppShell>);

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
    renderWithTheme(<AppShell>Content</AppShell>);

    const overviewLinks = screen.getAllByRole("link", { name: "Overview" });
    expect(overviewLinks.length).toBeGreaterThan(0);
    for (const link of overviewLinks) {
      expect(link).toHaveAttribute("href", "/");
      expect(link).toHaveAttribute("aria-current", "page");
    }
  });

  it("presents planned navigation without interactive destinations", () => {
    renderWithTheme(<AppShell>Content</AppShell>);

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
    renderWithTheme(<AppShell>Content</AppShell>);

    const menuButton = screen.getByRole("button", { name: "Open primary navigation" });
    expect(menuButton).toHaveAttribute("aria-expanded", "false");
    expect(menuButton).toHaveAttribute("aria-controls", "mobile-primary-navigation");

    await user.click(menuButton);
    expect(menuButton).toHaveAttribute("aria-expanded", "true");
    expect(menuButton).toHaveAccessibleName("Close primary navigation");

    await user.click(menuButton);
    expect(menuButton).toHaveAttribute("aria-expanded", "false");
  });

  it("does not expose unauthorized product controls", () => {
    renderWithTheme(<AppShell>Content</AppShell>);

    const prohibited = /sign[ -]?(?:in|out)|upload|execute|approval|auto[ -]?merge|edit production/i;
    expect(screen.queryByRole("button", { name: prohibited })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: prohibited })).not.toBeInTheDocument();
  });
});
