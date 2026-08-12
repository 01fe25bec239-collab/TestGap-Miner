import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const providerSource = readFileSync(
  resolve(process.cwd(), "src/providers/AuthSessionProvider.tsx"),
  "utf8",
);
const signInRouteSource = readFileSync(
  resolve(process.cwd(), "src/app/auth/sign-in/route.ts"),
  "utf8",
);

describe("UI Auth composition", () => {
  it("uses the merged browser bridge and browser adapter", () => {
    expect(providerSource).toContain("createAuthBrowserSessionFenceBridge");
    expect(providerSource).toContain("createBrowserAuthAdapter");
    expect(providerSource).not.toContain("createAuthAdapter");
  });

  it("keeps the legacy sign-in route as CSRF acquisition only", () => {
    expect(signInRouteSource).toContain("export async function GET");
    expect(signInRouteSource).not.toMatch(/export async function POST/);
  });
});
