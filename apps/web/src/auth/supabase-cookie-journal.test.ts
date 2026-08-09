import { afterEach, describe, expect, it, vi } from "vitest";
import { createAuthCallbackProviderWithCookies } from "./supabase";

const flowId = "callback_flow_1234";
const storageKey = "sb-project-auth-token";

function encoded(value: unknown) {
  return `base64-${Buffer.from(JSON.stringify(value)).toString("base64url")}`;
}

describe("installed Supabase SSR callback mutation behavior", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("stages the real SDK session write while retaining its PKCE cleanup", async () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://project.supabase.co");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "publishable-key");
    const fetch = vi.fn(async () =>
      new Response(
        JSON.stringify({
          access_token: "sdk-access-token",
          refresh_token: "sdk-refresh-token",
          expires_in: 3600,
          token_type: "bearer",
          user: { id: "user-one", app_metadata: {}, user_metadata: {}, aud: "authenticated" },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetch);
    const applied = vi.fn();
    const provider = await createAuthCallbackProviderWithCookies("http://localhost:3000", {
      getAll: () => [
        {
          name: `${storageKey}-flow-${flowId}-code-verifier`,
          value: encoded("sdk-verifier"),
        },
        { name: `${storageKey}-flows-code-verifier`, value: encoded([flowId]) },
        { name: `${storageKey}-code-verifier`, value: encoded("sdk-verifier") },
      ],
      setAll: applied,
    });

    const exchange = await provider.exchangeCode("authorization-code", flowId);
    expect(applied).not.toHaveBeenCalled();
    await exchange.prepareSessionCommit();
    expect(applied).not.toHaveBeenCalled();
    await exchange.discardSession();

    expect(fetch).toHaveBeenCalledTimes(1);
    expect(applied).toHaveBeenCalledTimes(1);
    const mutations = applied.mock.calls[0][0] as Array<{ name: string; value: string }>;
    expect(mutations.some(({ name }) => name === storageKey)).toBe(false);
    expect(mutations).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ name: `${storageKey}-flow-${flowId}-code-verifier`, value: "" }),
        expect.objectContaining({ name: `${storageKey}-flows-code-verifier`, value: "" }),
        expect.objectContaining({ name: `${storageKey}-code-verifier`, value: "" }),
      ]),
    );
  });
});
