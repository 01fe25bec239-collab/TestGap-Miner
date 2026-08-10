import { describe, expect, it } from "vitest";
import {
  AUTH_CONTEXT_COOKIE,
  AUTH_SESSION_BINDING_COOKIE,
  AUTH_SESSION_FENCE_OPERATIONS,
  LOCAL_SIGN_OUT_TOMBSTONE_COOKIE,
  AuthFenceCookieStateStore,
  AuthSessionFenceService,
  BrowserLocalSignOutTombstone,
  LocalProcessAuthSynchronizationAuthority,
  authContextCookie,
  authSessionBindingCookie,
  createOpaqueAuthHandle,
  getSharedLocalProcessAuthSynchronizationAuthority,
  localSignOutTombstoneCookie,
  type AuthCookieDefinition,
  type AuthFenceStateStore,
  type AuthSynchronizationAuthority,
} from "./session-fence";

class MemoryState implements AuthFenceStateStore {
  contextHandle: string | null = null;
  bindingHandle: string | null = null;
  tombstone = false;
  contextWrites = 0;

  async readAuthContextHandle() {
    return this.contextHandle;
  }

  async writeAuthContextHandle(handle: string) {
    this.contextHandle = handle;
    this.contextWrites += 1;
  }

  async readSessionBindingHandle() {
    return this.bindingHandle;
  }

  async writeSessionBindingHandle(handle: string) {
    this.bindingHandle = handle;
  }

  async clearSessionBindingHandle() {
    this.bindingHandle = null;
  }

  async hasLocalSignOutTombstone() {
    return this.tombstone;
  }

  createLocalSignOutTombstone() {
    this.tombstone = true;
  }

  async clearLocalSignOutTombstone() {
    this.tombstone = false;
  }
}

function harness(
  authority = new LocalProcessAuthSynchronizationAuthority("LOCAL_NON_PRODUCTION_ONLY"),
  state = new MemoryState(),
) {
  return { authority, state, service: new AuthSessionFenceService(authority, state) };
}

async function associatedAttempt(
  service: AuthSessionFenceService,
  callbackLookupHandle = createOpaqueAuthHandle(),
) {
  const prepared = await service.prepareSignIn();
  const references = await service.associateSignInAttempt(
    prepared.signInAttemptReference,
    callbackLookupHandle,
  );
  return { ...prepared, callbackLookupHandle, references };
}

describe("Auth fence handles and cookie posture", () => {
  it("publishes the frozen Auth-owned semantic operation vocabulary", () => {
    expect(AUTH_SESSION_FENCE_OPERATIONS).toEqual([
      "PREPARE_SIGN_IN",
      "PUBLISH_SIGN_OUT",
      "RESOLVE_SESSION",
    ]);
  });

  it("uses fresh 256-bit opaque handles", () => {
    const first = createOpaqueAuthHandle();
    const second = createOpaqueAuthHandle();
    expect(first).toMatch(/^[a-f0-9]{64}$/);
    expect(second).toMatch(/^[a-f0-9]{64}$/);
    expect(second).not.toBe(first);
  });

  it("keeps context and binding HttpOnly, host-only, and browser-session scoped", () => {
    for (const cookie of [
      authContextCookie("a".repeat(64), "http://localhost:3000"),
      authSessionBindingCookie("b".repeat(64), "https://app.example"),
    ]) {
      expect(cookie.options).toMatchObject({
        httpOnly: true,
        sameSite: "lax",
        path: "/",
      });
      expect(cookie.options).not.toHaveProperty("domain");
      expect(cookie.options).not.toHaveProperty("expires");
      expect(cookie.options).not.toHaveProperty("maxAge");
    }
    expect(authContextCookie("a".repeat(64), "http://localhost:3000").options.secure).toBe(
      false,
    );
    expect(authSessionBindingCookie("b".repeat(64), "https://app.example").options.secure).toBe(
      true,
    );
  });

  it("keeps the tombstone browser-readable, deny-only, and secret-free", () => {
    const cookie = localSignOutTombstoneCookie("https://app.example");
    expect(cookie).toMatchObject({
      name: LOCAL_SIGN_OUT_TOMBSTONE_COOKIE,
      value: "1",
      options: { httpOnly: false, secure: true, sameSite: "lax", path: "/" },
    });
    expect(cookie.options).not.toHaveProperty("domain");
    expect(cookie.options).not.toHaveProperty("expires");
    expect(cookie.options).not.toHaveProperty("maxAge");
    expect(cookie.value).not.toMatch(/[a-f0-9]{32}/);
  });

  it("provides an Auth-owned browser tombstone helper without persistent storage", () => {
    const cookieDocument = { cookie: "" };
    const helper = new BrowserLocalSignOutTombstone(
      "http://localhost:3000",
      cookieDocument,
    );
    helper.create();
    expect(cookieDocument.cookie).toBe(
      `${LOCAL_SIGN_OUT_TOMBSTONE_COOKIE}=1; Path=/; SameSite=Lax`,
    );
    expect(helper.isActive()).toBe(true);
    helper.clearAfterAuthorizedReconciliation();
    expect(cookieDocument.cookie).toContain("Max-Age=0");
    expect(cookieDocument.cookie).not.toContain("Secure");
  });

  it("applies Auth cookie definitions through an injected server cookie boundary", async () => {
    const jar = new Map<string, string>();
    const mutations: AuthCookieDefinition[] = [];
    const state = new AuthFenceCookieStateStore("http://localhost:3000", {
      getAll: () => [...jar].map(([name, value]) => ({ name, value })),
      set: (cookie) => {
        mutations.push(cookie);
        if (cookie.options.maxAge === 0) jar.delete(cookie.name);
        else jar.set(cookie.name, cookie.value);
      },
    });
    await state.writeAuthContextHandle("a".repeat(64));
    await state.writeSessionBindingHandle("b".repeat(64));
    state.createLocalSignOutTombstone();
    expect(await state.readAuthContextHandle()).toBe("a".repeat(64));
    expect(await state.readSessionBindingHandle()).toBe("b".repeat(64));
    expect(await state.hasLocalSignOutTombstone()).toBe(true);
    expect(mutations.map(({ name }) => name)).toEqual([
      AUTH_CONTEXT_COOKIE,
      AUTH_SESSION_BINDING_COOKIE,
      LOCAL_SIGN_OUT_TOMBSTONE_COOKIE,
    ]);
  });
});

describe("LOCAL_NON_PRODUCTION_ONLY process authority", () => {
  it("fails closed when the Auth context or binding is missing", async () => {
    const { service } = harness();
    expect(await service.resolveFence()).toEqual({
      eligible: false,
      reason: "UNVERIFIED",
    });
  });

  it("advances one context generation monotonically", async () => {
    const { authority, state, service } = harness();
    await service.prepareSignIn();
    const context = state.contextHandle!;
    expect(authority.readCurrentGeneration(context)).toBe(0);
    service.createLocalSignOutTombstone();
    await service.publishSignOut();
    expect(authority.readCurrentGeneration(context)).toBe(1);
    await service.publishSignOut();
    expect(authority.readCurrentGeneration(context)).toBe(2);
  });

  it("keeps independent same-generation attempts current", async () => {
    const { service } = harness();
    const first = await associatedAttempt(service);
    const second = await associatedAttempt(service);
    expect(await service.validateCallback(first.callbackLookupHandle)).toMatchObject({
      eligible: true,
    });
    expect(await service.validateCallback(second.callbackLookupHandle)).toMatchObject({
      eligible: true,
    });
    expect(first.references.signInAttemptReference).not.toBe(
      second.references.signInAttemptReference,
    );
  });

  it("issues a fresh binding for every successful session establishment", async () => {
    const { state, service } = harness();
    const first = await associatedAttempt(service);
    await service.establishSession(first.callbackLookupHandle);
    const firstBinding = state.bindingHandle;
    const second = await associatedAttempt(service);
    await service.establishSession(second.callbackLookupHandle);
    expect(state.bindingHandle).toMatch(/^[a-f0-9]{64}$/);
    expect(state.bindingHandle).not.toBe(firstBinding);
  });

  it("reconciles a published sign-out before clearing its tombstone", async () => {
    const { authority, state, service } = harness();
    const oldAttempt = await associatedAttempt(service);
    const context = state.contextHandle!;
    service.createLocalSignOutTombstone();
    await service.publishSignOut();
    const prepared = await service.prepareSignIn();
    expect(state.tombstone).toBe(false);
    expect(state.contextHandle).toBe(context);
    expect(authority.readCurrentGeneration(context)).toBe(1);
    expect(await service.validateCallback(oldAttempt.callbackLookupHandle)).toEqual({
      eligible: false,
      reason: "STALE_PROVIDER_SESSION_MATERIAL",
    });
    await service.associateSignInAttempt(
      prepared.signInAttemptReference,
      createOpaqueAuthHandle(),
    );
  });

  it("reconciles outstanding authority state even when the tombstone is absent", async () => {
    const { state, service } = harness();
    await service.prepareSignIn();
    service.createLocalSignOutTombstone();
    await service.publishSignOut();

    state.tombstone = false;
    await expect(service.prepareSignIn()).resolves.toMatchObject({
      signInAttemptReference: expect.stringMatching(/^[a-f0-9]{64}$/),
    });

    state.tombstone = true;
    await expect(service.prepareSignIn()).rejects.toThrow("reconciliation failed");
  });

  it("leaves the tombstone active when publication cannot be proven", async () => {
    const { authority, state, service } = harness();
    await service.prepareSignIn();
    service.createLocalSignOutTombstone();
    authority.setAvailableForTests(false);
    await expect(service.publishSignOut()).rejects.toThrow("unavailable");
    authority.setAvailableForTests(true);
    await expect(service.prepareSignIn()).rejects.toThrow("reconciliation failed");
    expect(state.tombstone).toBe(true);
  });

  it("cannot replay a reconciled publication proof for a later failed sign-out", async () => {
    const { authority, state, service } = harness();
    await service.prepareSignIn();
    service.createLocalSignOutTombstone();
    await service.publishSignOut();
    await service.prepareSignIn();
    expect(state.tombstone).toBe(false);

    const currentAttempt = await associatedAttempt(service);
    service.createLocalSignOutTombstone();
    authority.setAvailableForTests(false);
    await expect(service.publishSignOut()).rejects.toThrow("unavailable");
    authority.setAvailableForTests(true);

    await expect(service.prepareSignIn()).rejects.toThrow("reconciliation failed");
    expect(state.tombstone).toBe(true);
    expect(await service.validateCallback(currentAttempt.callbackLookupHandle)).toEqual({
      eligible: false,
      reason: "TOMBSTONED",
    });
  });

  it("consumes reconciliation proof only after tombstone clearing succeeds", async () => {
    const { state, service } = harness();
    await service.prepareSignIn();
    service.createLocalSignOutTombstone();
    await service.publishSignOut();
    const clear = state.clearLocalSignOutTombstone.bind(state);
    state.clearLocalSignOutTombstone = async () => {
      throw new Error("cookie mutation failed");
    };
    await expect(service.prepareSignIn()).rejects.toThrow("cookie mutation failed");
    expect(state.tombstone).toBe(true);
    state.clearLocalSignOutTombstone = clear;
    await expect(service.prepareSignIn()).resolves.toMatchObject({
      signInAttemptReference: expect.stringMatching(/^[a-f0-9]{64}$/),
    });
    expect(state.tombstone).toBe(false);
  });

  it("accepts an alternate provider-neutral authority implementation", async () => {
    const backing = new LocalProcessAuthSynchronizationAuthority(
      "LOCAL_NON_PRODUCTION_ONLY",
    );
    const alternate = {
      subscribe: backing.subscribe.bind(backing),
      prepareSignIn: backing.prepareSignIn.bind(backing),
      completeSignInReconciliation:
        backing.completeSignInReconciliation.bind(backing),
      completeAuthorizedContextReset:
        backing.completeAuthorizedContextReset.bind(backing),
      readCurrentGeneration: backing.readCurrentGeneration.bind(backing),
      advanceSignOutGeneration: backing.advanceSignOutGeneration.bind(backing),
      associateAttempt: backing.associateAttempt.bind(backing),
      validateAttempt: backing.validateAttempt.bind(backing),
      createSessionBinding: backing.createSessionBinding.bind(backing),
      validateSessionBinding: backing.validateSessionBinding.bind(backing),
      invalidateBinding: backing.invalidateBinding.bind(backing),
      invalidateBindingForAttempt: backing.invalidateBindingForAttempt.bind(backing),
      abandonAttempt: backing.abandonAttempt.bind(backing),
      abandonAttemptForCallback: backing.abandonAttemptForCallback.bind(backing),
    } satisfies AuthSynchronizationAuthority;
    const service = new AuthSessionFenceService(alternate, new MemoryState());

    await expect(service.prepareSignIn()).resolves.toMatchObject({
      signInAttemptReference: expect.stringMatching(/^[a-f0-9]{64}$/),
    });
  });

  it("fails closed on unavailable authority and state loss", async () => {
    const { authority, state, service } = harness();
    const attempt = await associatedAttempt(service);
    await service.establishSession(attempt.callbackLookupHandle);
    authority.setAvailableForTests(false);
    expect(await service.resolveFence()).toEqual({
      eligible: false,
      reason: "AUTHORITY_UNAVAILABLE",
    });
    authority.setAvailableForTests(true);
    const writesBeforeLoss = state.contextWrites;
    authority.resetStateForTests();
    expect(await service.resolveFence()).toEqual({
      eligible: false,
      reason: "UNVERIFIED",
    });
    expect(state.contextWrites).toBe(writesBeforeLoss);
    expect(state.contextHandle).not.toBeNull();
  });

  it("resets a lost context without reconstructing its generation or binding", async () => {
    const { authority, state, service } = harness();
    const oldAttempt = await associatedAttempt(service);
    await service.establishSession(oldAttempt.callbackLookupHandle);
    const oldContext = state.contextHandle!;
    const oldBinding = state.bindingHandle!;
    service.createLocalSignOutTombstone();
    await service.publishSignOut();
    expect(authority.readCurrentGeneration(oldContext)).toBe(1);

    authority.resetStateForTests();
    state.bindingHandle = oldBinding;
    await expect(service.prepareSignIn()).resolves.toMatchObject({
      signInAttemptReference: expect.stringMatching(/^[a-f0-9]{64}$/),
    });

    expect(state.contextHandle).not.toBe(oldContext);
    expect(authority.readCurrentGeneration(state.contextHandle!)).toBe(0);
    expect(state.bindingHandle).toBeNull();
    expect(state.tombstone).toBe(false);
    expect(
      authority.validateSessionBinding(state.contextHandle!, oldBinding),
    ).toBeNull();
    expect(await service.validateCallback(oldAttempt.callbackLookupHandle)).toEqual({
      eligible: false,
      reason: "STALE_PROVIDER_SESSION_MATERIAL",
    });
  });

  it("keeps a failed context reset denied and safely retries it", async () => {
    const { authority, state, service } = harness();
    const attempt = await associatedAttempt(service);
    await service.establishSession(attempt.callbackLookupHandle);
    const oldContext = state.contextHandle;
    service.createLocalSignOutTombstone();
    authority.resetStateForTests();

    const writeContext = state.writeAuthContextHandle.bind(state);
    state.writeAuthContextHandle = async (handle) => {
      await writeContext(handle);
      state.writeAuthContextHandle = writeContext;
      throw new Error("cookie mutation failed");
    };
    await expect(service.prepareSignIn()).rejects.toThrow("cookie mutation failed");
    const freshContext = state.contextHandle;
    expect(freshContext).not.toBe(oldContext);
    expect(state.bindingHandle).toBeNull();
    expect(state.tombstone).toBe(true);

    await expect(service.prepareSignIn()).resolves.toMatchObject({
      signInAttemptReference: expect.stringMatching(/^[a-f0-9]{64}$/),
    });
    expect(state.contextHandle).toBe(freshContext);
    expect(state.bindingHandle).toBeNull();
    expect(state.tombstone).toBe(false);
  });

  it("does not let stale cleanup remove the current context or active tombstone", async () => {
    const { state, service } = harness();
    const attempt = await associatedAttempt(service);
    await service.establishSession(attempt.callbackLookupHandle);
    const context = state.contextHandle;
    service.createLocalSignOutTombstone();
    await service.cleanupStaleSessionMaterial();
    expect(state.contextHandle).toBe(context);
    expect(state.tombstone).toBe(true);
    expect(state.bindingHandle).toBeNull();
  });

  it("rejects a stale binding generation mismatch", async () => {
    const { state, service } = harness();
    const attempt = await associatedAttempt(service);
    await service.establishSession(attempt.callbackLookupHandle);
    const staleBinding = state.bindingHandle;
    service.createLocalSignOutTombstone();
    await service.publishSignOut();
    state.tombstone = false;
    state.bindingHandle = staleBinding;
    expect(await service.resolveFence()).toEqual({
      eligible: false,
      reason: "STALE_PROVIDER_SESSION_MATERIAL",
    });
  });

  it("does not rotate a newer context while validating an old callback", async () => {
    const authority = new LocalProcessAuthSynchronizationAuthority(
      "LOCAL_NON_PRODUCTION_ONLY",
    );
    const old = harness(authority);
    const oldAttempt = await associatedAttempt(old.service);
    const newer = harness(authority);
    await newer.service.prepareSignIn();
    old.state.contextHandle = newer.state.contextHandle;
    expect(await old.service.validateCallback(oldAttempt.callbackLookupHandle)).toEqual({
      eligible: false,
      reason: "STALE_PROVIDER_SESSION_MATERIAL",
    });
    expect(old.state.contextHandle).toBe(newer.state.contextHandle);
  });

  it("shares one explicitly local authority across callback and fence services", async () => {
    const authority = getSharedLocalProcessAuthSynchronizationAuthority({
      applicationOrigin: "http://localhost:3000",
      environmentClass: "LOCAL_DEVELOPMENT",
    });
    const callbackState = new MemoryState();
    const callbackService = new AuthSessionFenceService(authority, callbackState);
    const attempt = await associatedAttempt(callbackService);
    const routeState = new MemoryState();
    routeState.contextHandle = callbackState.contextHandle;
    const routeService = new AuthSessionFenceService(authority, routeState);
    routeService.createLocalSignOutTombstone();
    await routeService.publishSignOut();
    expect(await callbackService.validateCallback(attempt.callbackLookupHandle)).toEqual({
      eligible: false,
      reason: "STALE_PROVIDER_SESSION_MATERIAL",
    });
  });

  it("refuses to claim process-local safety outside exact local development", () => {
    expect(() =>
      getSharedLocalProcessAuthSynchronizationAuthority({
        applicationOrigin: "https://app.example",
        environmentClass: "LOCAL_DEVELOPMENT",
      }),
    ).toThrow("restricted to local development");
  });
});
