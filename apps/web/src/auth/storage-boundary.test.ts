import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { afterEach, describe, expect, it } from "vitest";
import { createAuthBrowserClient } from "./supabase";

const authDirectory = dirname(fileURLToPath(import.meta.url));
const implementationFiles = readdirSync(authDirectory)
  .filter((name) => name.endsWith(".ts") && !name.endsWith(".test.ts"))
  .map((name) => join(authDirectory, name));

describe("token custody and secret safety", () => {
  it("contains no prohibited shadow persistence mechanism", () => {
    const source = implementationFiles.map((file) => readFileSync(file, "utf8")).join("\n");
    for (const prohibited of [
      /\blocalStorage\b/,
      /\bsessionStorage\b/,
      /\bindexedDB\b/,
      /\bRedux\b/i,
      /\bZustand\b/i,
      /service[- ]worker/i,
      /provider[- ]token cache/i,
    ]) {
      expect(source).not.toMatch(prohibited);
    }
  });

  it("never logs credentials or raw provider failures", () => {
    const source = implementationFiles.map((file) => readFileSync(file, "utf8")).join("\n");
    expect(source).not.toMatch(/console\.(?:debug|error|info|log|warn)/);
    expect(source).not.toContain("SUPABASE_GITHUB_CLIENT_SECRET");
    expect(source).not.toMatch(/eyJ[A-Za-z0-9_-]{16,}/);
  });

  it("uses only the official SSR client factories", () => {
    const source = readFileSync(join(authDirectory, "supabase.ts"), "utf8");
    const adapterSource = readFileSync(join(authDirectory, "adapter.ts"), "utf8");
    expect(source).toContain("createBrowserClient");
    expect(source).toContain("createServerClient");
    expect(source).not.toMatch(/\bcreateClient\s*\(/);
    expect(source).toContain('flowType: "pkce"');
    expect(source).toContain('scope: "local"');
    expect(source).not.toMatch(/\.auth\.setSession\s*\(/);
    expect(
      adapterSource.slice(
        adapterSource.indexOf("async #exchangeCallback"),
        adapterSource.indexOf("async #completedCallback"),
      ),
    ).not.toMatch(/signOut/i);
    expect(readFileSync(join(authDirectory, "supabase-server.ts"), "utf8")).toContain(
      "setResponseHeaders(headers)",
    );
  });
});

describe("deferred public environment validation", () => {
  const originalUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const originalKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

  afterEach(() => {
    if (originalUrl === undefined) delete process.env.NEXT_PUBLIC_SUPABASE_URL;
    else process.env.NEXT_PUBLIC_SUPABASE_URL = originalUrl;
    if (originalKey === undefined) delete process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
    else process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY = originalKey;
  });

  it("does not require runtime configuration merely to import the module", () => {
    expect(typeof createAuthBrowserClient).toBe("function");
  });

  it("fails clearly and safely only when a configured operation is invoked", () => {
    delete process.env.NEXT_PUBLIC_SUPABASE_URL;
    delete process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
    expect(() => createAuthBrowserClient("http://localhost:3000")).toThrowError(
      "Authentication operation failed",
    );
  });
});
