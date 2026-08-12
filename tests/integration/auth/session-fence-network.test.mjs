import assert from "node:assert/strict";
import { once } from "node:events";
import http from "node:http";
import net from "node:net";
import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import test from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

const APP_ORIGIN = "http://localhost:3000";
const APP_PORT = 3000;
const REQUEST_TIMEOUT_MS = 5_000;
const STARTUP_TIMEOUT_MS = 45_000;
const CSRF_COOKIE = "testgap-auth-csrf";
const CONTEXT_COOKIE = "testgap-auth-context";
const BINDING_COOKIE = "testgap-auth-session-binding";
const TOMBSTONE_COOKIE = "testgap-auth-signed-out";
const PROVIDER_COOKIE = "sb-127-auth-token";
const CORRELATION_COOKIE_PREFIX = "testgap-auth-correlation-";
const FIXTURE_AUTHORIZATION_CODE = "fixture-authorization-code";
const TEST_DIR = path.dirname(fileURLToPath(import.meta.url));
const WEB_DIR = path.resolve(TEST_DIR, "../../../apps/web");

class CookieJar {
  #cookies = new Map();

  clone() {
    const copy = new CookieJar();
    copy.#cookies = new Map(
      [...this.#cookies].map(([name, cookie]) => [name, { ...cookie }]),
    );
    return copy;
  }

  get(name) {
    return this.#cookies.get(name)?.value;
  }

  has(name) {
    return this.#cookies.has(name);
  }

  names() {
    return [...this.#cookies.keys()];
  }

  delete(name) {
    this.#cookies.delete(name);
  }

  set(name, value, options = {}) {
    this.#cookies.set(name, { value, path: options.path ?? "/", secure: false });
  }

  header(pathname) {
    return [...this.#cookies]
      .filter(([, cookie]) => pathname.startsWith(cookie.path) && !cookie.secure)
      .map(([name, cookie]) => `${name}=${cookie.value}`)
      .join("; ");
  }

  absorb(response) {
    const metadata = setCookieHeaders(response.headers).map(parseSetCookie);
    for (const cookie of metadata) {
      if (cookie.maxAge === 0) this.#cookies.delete(cookie.name);
      else {
        this.#cookies.set(cookie.name, {
          value: cookie.value,
          path: cookie.path ?? "/",
          secure: cookie.secure,
        });
      }
    }
    return metadata.map(({ value: _value, ...safe }) => safe);
  }

  secretValues() {
    return [...this.#cookies.values()]
      .map(({ value }) => value)
      .filter((value) => value.length >= 16);
  }
}

function setCookieHeaders(headers) {
  if (typeof headers.getSetCookie === "function") return headers.getSetCookie();
  const combined = headers.get("set-cookie");
  return combined ? [combined] : [];
}

function parseSetCookie(header) {
  const [pair, ...attributes] = header.split(";").map((part) => part.trim());
  const separator = pair.indexOf("=");
  const cookie = {
    name: pair.slice(0, separator),
    value: pair.slice(separator + 1),
    httpOnly: false,
    sameSite: null,
    secure: false,
    maxAge: null,
    path: null,
  };
  for (const attribute of attributes) {
    const [rawName, ...rawValue] = attribute.split("=");
    const name = rawName.toLowerCase();
    const value = rawValue.join("=");
    if (name === "httponly") cookie.httpOnly = true;
    else if (name === "secure") cookie.secure = true;
    else if (name === "samesite") cookie.sameSite = value.toLowerCase();
    else if (name === "max-age") cookie.maxAge = Number(value);
    else if (name === "path") cookie.path = value;
  }
  return cookie;
}

function cookieMetadata(metadata, name) {
  const cookie = metadata.find((candidate) => candidate.name === name);
  assert.ok(cookie, `expected Set-Cookie metadata for ${name}`);
  return cookie;
}

function assertCookieMetadata(cookie, expected) {
  for (const [field, value] of Object.entries(expected)) {
    assert.ok(cookie[field] === value, `${cookie.name} ${field} differed`);
  }
}

function assertExactRecord(body, expected) {
  assert.ok(body && typeof body === "object" && !Array.isArray(body), "expected JSON object");
  const actualKeys = Object.keys(body).sort();
  const expectedKeys = Object.keys(expected).sort();
  assert.ok(
    actualKeys.join("\0") === expectedKeys.join("\0"),
    `unexpected response fields: ${actualKeys.join(", ")}`,
  );
  for (const [key, value] of Object.entries(expected)) {
    assert.ok(body[key] === value, `response field ${key} differed`);
  }
}

const SENSITIVE_KEY = /(?:access_?token|refresh_?token|authorization|provider.?cookie|provider.?session|session.?binding|auth.?context|contextHandle|bindingHandle|signInAttemptReference|callbackFlowReference|correlationReference|authorizationCode|pkce|verifier)/i;

function assertNoSensitiveResponse(body, jar) {
  const secrets = jar.secretValues();
  const visit = (value) => {
    if (Array.isArray(value)) return value.forEach(visit);
    if (value && typeof value === "object") {
      for (const [key, child] of Object.entries(value)) {
        assert.ok(!SENSITIVE_KEY.test(key), `sensitive response field: ${key}`);
        visit(child);
      }
      return;
    }
    if (typeof value !== "string") return;
    assert.ok(!/^bearer\s+/i.test(value), "bearer credential appeared in response");
    assert.ok(
      !secrets.some((secret) => value.includes(secret)),
      "cookie or session secret appeared in response",
    );
  };
  visit(body);
}

async function requestText(jar, pathname, options = {}) {
  const url = new URL(pathname, APP_ORIGIN);
  const headers = new Headers(options.headers);
  const cookie = jar.header(url.pathname);
  if (cookie && options.sendCookies !== false) headers.set("cookie", cookie);
  const response = await fetch(url, {
    ...options,
    headers,
    redirect: "manual",
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
  });
  const metadata = jar.absorb(response);
  const text = await response.text();
  return { response, text, metadata };
}

async function requestJson(jar, pathname, options = {}) {
  const result = await requestText(jar, pathname, options);
  let body;
  try {
    body = JSON.parse(result.text);
  } catch {
    assert.fail("expected a JSON response body");
  }
  return { ...result, body };
}

async function post(jar, body, csrfToken, overrides = {}) {
  const headers = new Headers({
    accept: "application/json",
    "content-type": "application/json",
    origin: APP_ORIGIN,
    "sec-fetch-site": "same-origin",
    "x-auth-csrf": csrfToken,
  });
  for (const [name, value] of Object.entries(overrides.headers ?? {})) {
    if (value === null) headers.delete(name);
    else headers.set(name, value);
  }
  return requestJson(jar, "/auth/session-fence", {
    method: "POST",
    headers,
    body: overrides.rawBody ?? JSON.stringify(body),
    sendCookies: overrides.sendCookies,
  });
}

function assertAuthResponse(result, status, expected, jar) {
  assert.ok(result.response.status === status, `expected HTTP ${status}`);
  assert.ok(
    result.response.headers.get("content-type")?.startsWith("application/json"),
    "expected JSON content type",
  );
  assert.ok(
    result.response.headers.get("cache-control") === "private, no-store",
    "Auth response must be private, no-store",
  );
  assertExactRecord(result.body, expected);
  assertNoSensitiveResponse(result.body, jar);
}

function fakeProviderSession(providerOrigin) {
  const base64url = (value) => Buffer.from(JSON.stringify(value)).toString("base64url");
  const now = Math.floor(Date.now() / 1_000);
  const accessToken = `${base64url({ alg: "none", typ: "JWT" })}.${base64url({
    aud: "authenticated",
    exp: now + 3_600,
    iss: `${providerOrigin}/auth/v1`,
    sub: "fixture-user",
  })}.fixture`;
  return {
    access_token: accessToken,
    refresh_token: "fixture-refresh-token-never-logged",
    expires_at: now + 3_600,
    expires_in: 3_600,
    token_type: "bearer",
    user: {
      id: "fixture-user",
      aud: "authenticated",
      role: "authenticated",
      email: "fixture@example.test",
      app_metadata: { provider: "github", providers: ["github"] },
      user_metadata: {},
      identities: [],
      created_at: new Date(0).toISOString(),
      updated_at: new Date(0).toISOString(),
    },
  };
}

function fakeProviderSessionCookie(providerOrigin) {
  return `base64-${Buffer.from(JSON.stringify(fakeProviderSession(providerOrigin))).toString("base64url")}`;
}

function providerFlowId(jar) {
  const prefix = `${PROVIDER_COOKIE}-flow-`;
  const suffix = "-code-verifier";
  const cookieName = jar.names().find(
    (name) => name.startsWith(prefix) && name.endsWith(suffix),
  );
  assert.ok(cookieName, "PREPARE_SIGN_IN did not establish provider PKCE state");
  return cookieName.slice(prefix.length, -suffix.length);
}

async function completeCallback(jar, callbackUrl) {
  const page = await requestText(jar, callbackUrl, {
    headers: { accept: "text/html" },
  });
  assert.ok(page.response.status === 200, "callback route did not render");
  assert.ok(
    page.response.headers.get("content-type")?.startsWith("text/html"),
    "callback route did not return HTML",
  );

  const scriptPaths = [...new Set(
    [...page.text.matchAll(/<script[^>]+src="([^"]+\.js)"/g)].map((match) => match[1]),
  )];
  const scripts = await Promise.all(scriptPaths.map(async (scriptPath) => {
    const response = await fetch(new URL(scriptPath, APP_ORIGIN), {
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
    assert.ok(response.ok, `callback client script failed: ${scriptPath}`);
    return response.text();
  }));
  const actionId = scripts
    .map((script) => script.match(/\{"([a-f0-9]{42})":\{"name":"completeAuthCallback"\}\}/)?.[1])
    .find(Boolean);
  assert.ok(actionId, "callback action was not exposed by the rendered application");

  const callbackQuery = new URL(callbackUrl).search;
  const action = await requestText(jar, "/auth/callback", {
    method: "POST",
    headers: {
      accept: "text/x-component",
      "content-type": "text/plain;charset=UTF-8",
      "next-action": actionId,
      origin: APP_ORIGIN,
    },
    body: JSON.stringify([callbackQuery]),
  });
  assert.ok(action.response.status === 200, "callback action failed");
  assert.ok(
    action.response.headers.get("content-type")?.startsWith("text/x-component"),
    "callback action did not return a React server response",
  );
  const resultLine = action.text.split("\n").find((line) => /^\d+:\{"ok":/.test(line));
  assert.ok(resultLine, "callback action result was absent");
  const body = JSON.parse(resultLine.slice(resultLine.indexOf(":") + 1));
  assertNoSensitiveResponse(body, jar);
  return { ...action, body };
}

async function followProviderSignIn(provider, jar, redirectUrl) {
  provider.prepareAuthorization(providerFlowId(jar));
  const navigation = await fetch(redirectUrl, {
    redirect: "manual",
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
  });
  assert.ok(navigation.status === 302, "loopback provider navigation failed");
  const callbackUrl = navigation.headers.get("location");
  assert.ok(callbackUrl, "loopback provider did not return a callback redirect");
  const callback = new URL(callbackUrl);
  assert.ok(callback.origin === APP_ORIGIN && callback.pathname === "/auth/callback");
  assert.ok(callback.searchParams.get("code") === FIXTURE_AUTHORIZATION_CODE);
  assert.ok(callback.searchParams.get("sb_flow_id") === providerFlowId(jar));
  return completeCallback(jar, callbackUrl);
}

async function createProviderFixture() {
  const requests = [];
  let userMode = "success";
  let authorizationFlowId = null;
  let gate = null;
  let origin;
  const server = http.createServer(async (request, response) => {
    const requestUrl = new URL(request.url, "http://fixture.invalid");
    const { pathname } = requestUrl;
    requests.push({ method: request.method, pathname });
    if (pathname === "/auth/v1/authorize") {
      const redirectTo = requestUrl.searchParams.get("redirect_to");
      if (!authorizationFlowId || !redirectTo) {
        response.writeHead(400, { "content-type": "application/json" });
        response.end(JSON.stringify({ message: "authorization fixture was not prepared" }));
        return;
      }
      const callback = new URL(redirectTo);
      callback.searchParams.set("code", FIXTURE_AUTHORIZATION_CODE);
      callback.searchParams.set("sb_flow_id", authorizationFlowId);
      authorizationFlowId = null;
      response.writeHead(302, { "cache-control": "no-store", location: callback.toString() });
      response.end();
      return;
    }
    if (pathname === "/auth/v1/token" && requestUrl.searchParams.get("grant_type") === "pkce") {
      let rawBody = "";
      for await (const chunk of request) rawBody += chunk;
      let body;
      try {
        body = JSON.parse(rawBody);
      } catch {
        body = null;
      }
      if (
        request.method !== "POST" ||
        body?.auth_code !== FIXTURE_AUTHORIZATION_CODE ||
        typeof body?.code_verifier !== "string" ||
        body.code_verifier.length < 43
      ) {
        response.writeHead(400, { "content-type": "application/json" });
        response.end(JSON.stringify({ message: "invalid PKCE exchange" }));
        return;
      }
      response.writeHead(200, {
        "cache-control": "no-store",
        "content-type": "application/json",
      });
      response.end(JSON.stringify(fakeProviderSession(origin)));
      return;
    }
    if (pathname === "/auth/v1/user") {
      if (gate) {
        gate.arrive();
        await gate.release;
        gate = null;
      }
      if (userMode === "success") {
        response.writeHead(200, { "content-type": "application/json" });
        response.end(JSON.stringify({
          id: "fixture-user",
          aud: "authenticated",
          role: "authenticated",
          email: "fixture@example.test",
          app_metadata: { provider: "github", providers: ["github"] },
          user_metadata: {},
          identities: [],
          created_at: new Date(0).toISOString(),
          updated_at: new Date(0).toISOString(),
        }));
        return;
      }
      const status = userMode === "rejected" ? 401 : 503;
      response.writeHead(status, { "content-type": "application/json" });
      response.end(JSON.stringify({ message: "provider fixture denied validation" }));
      return;
    }
    response.writeHead(404, { "content-type": "application/json" });
    response.end(JSON.stringify({ message: "not found" }));
  });
  await new Promise((resolve, reject) => {
    server.listen(0, "127.0.0.1", resolve);
    server.once("error", reject);
  });
  const address = server.address();
  assert.ok(address && typeof address === "object");
  origin = `http://127.0.0.1:${address.port}`;
  return {
    origin,
    requests,
    setUserMode(mode) {
      userMode = mode;
    },
    prepareAuthorization(flowId) {
      authorizationFlowId = flowId;
    },
    armUserGate() {
      let arrive;
      let release;
      const arrived = new Promise((resolve) => { arrive = resolve; });
      const released = new Promise((resolve) => { release = resolve; });
      gate = { arrive, release: released };
      return { arrived, release };
    },
    async close() {
      server.closeAllConnections();
      await new Promise((resolve) => server.close(resolve));
    },
  };
}

async function assertPortAvailable() {
  const probe = net.createServer();
  await new Promise((resolve, reject) => {
    probe.once("error", reject);
    probe.listen(APP_PORT, "localhost", resolve);
  }).catch((error) => {
    if (error?.code === "EADDRINUSE") {
      assert.fail("localhost:3000 is occupied; refusing to launch the Integration runtime");
    }
    throw error;
  });
  await new Promise((resolve) => probe.close(resolve));
}

function launchApp(providerOrigin) {
  const child = spawn(
    "npm",
    ["run", "dev", "--", "--hostname", "localhost", "--port", String(APP_PORT)],
    {
      cwd: WEB_DIR,
      detached: true,
      env: {
        ...process.env,
        DASHBOARD_ORIGIN: APP_ORIGIN,
        NEXT_PUBLIC_SUPABASE_URL: providerOrigin,
        NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: "integration-fixture-publishable-key",
        NEXT_TELEMETRY_DISABLED: "1",
      },
      stdio: ["ignore", "pipe", "pipe"],
    },
  );
  let capturedBytes = 0;
  for (const stream of [child.stdout, child.stderr]) {
    stream.on("data", (chunk) => {
      // Capture a bounded amount for lifecycle diagnostics without emitting logs or secrets.
      capturedBytes = Math.min(capturedBytes + chunk.length, 64 * 1024);
    });
  }
  return { child, capturedBytes: () => capturedBytes };
}

async function waitForApp(child) {
  const deadline = Date.now() + STARTUP_TIMEOUT_MS;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) assert.fail("Next.js exited before readiness");
    try {
      const response = await fetch(`${APP_ORIGIN}/auth/sign-in`, {
        headers: { accept: "application/json" },
        signal: AbortSignal.timeout(1_500),
      });
      if (response.status === 200) {
        await response.arrayBuffer();
        return;
      }
    } catch {
      // The bounded poll continues until readiness or deadline.
    }
    await delay(100);
  }
  assert.fail("Next.js did not become ready within the startup deadline");
}

function processGroupExists(pid) {
  try {
    process.kill(-pid, 0);
    return true;
  } catch (error) {
    if (error?.code === "ESRCH") return false;
    throw error;
  }
}

async function stopApp(child) {
  if (child.exitCode === null) {
    try {
      process.kill(-child.pid, "SIGTERM");
    } catch (error) {
      if (error?.code !== "ESRCH") throw error;
    }
    await Promise.race([once(child, "exit"), delay(5_000)]);
  }
  if (processGroupExists(child.pid)) {
    process.kill(-child.pid, "SIGKILL");
    const deadline = Date.now() + 3_000;
    while (processGroupExists(child.pid) && Date.now() < deadline) await delay(25);
  }
  assert.ok(!processGroupExists(child.pid), "Next.js process group was not cleaned up");
}

function installSignalCleanup(child) {
  const cleanup = () => {
    try {
      process.kill(-child.pid, "SIGKILL");
    } catch {
      // The child is already gone.
    }
  };
  process.once("exit", cleanup);
  process.once("SIGINT", cleanup);
  process.once("SIGTERM", cleanup);
  return () => {
    process.off("exit", cleanup);
    process.off("SIGINT", cleanup);
    process.off("SIGTERM", cleanup);
  };
}

test("merged Auth session fence is fail-closed across real loopback HTTP", { timeout: 90_000 }, async () => {
  await assertPortAvailable();
  const provider = await createProviderFixture();
  const runtime = launchApp(provider.origin);
  const removeSignalCleanup = installSignalCleanup(runtime.child);
  let appStopped = false;

  try {
    await waitForApp(runtime.child);
    assert.ok(runtime.capturedBytes() > 0, "Next.js stdout/stderr was not captured");

    const jar = new CookieJar();
    const csrf = await requestJson(jar, "/auth/sign-in", {
      headers: { accept: "application/json" },
    });
    assertAuthResponse(csrf, 200, { csrfToken: csrf.body.csrfToken }, new CookieJar());
    assert.ok(typeof csrf.body.csrfToken === "string" && csrf.body.csrfToken.length === 64);
    const csrfToken = csrf.body.csrfToken;
    assertCookieMetadata(cookieMetadata(csrf.metadata, CSRF_COOKIE), {
      httpOnly: true,
      sameSite: "lax",
      secure: false,
      maxAge: 3_600,
      path: "/",
    });

    const missingBinding = await post(jar, { operation: "RESOLVE_SESSION" }, csrfToken);
    assertAuthResponse(
      missingBinding,
      200,
      { state: "UNAUTHENTICATED", userReference: null },
      jar,
    );

    const prepared = await post(
      jar,
      { operation: "PREPARE_SIGN_IN", intendedReturn: "/runs?view=mine" },
      csrfToken,
    );
    assertAuthResponse(prepared, 200, { redirectUrl: prepared.body.redirectUrl }, jar);
    assert.ok(typeof prepared.body.redirectUrl === "string", "redirectUrl must be a string");
    const redirect = new URL(prepared.body.redirectUrl);
    assert.ok(redirect.origin === provider.origin, "redirect must target the loopback provider");
    assert.ok(redirect.pathname === "/auth/v1/authorize", "unexpected provider route");
    assert.ok(redirect.searchParams.get("provider") === "github", "unexpected provider");
    assert.ok(
      redirect.searchParams.get("redirect_to")?.startsWith(`${APP_ORIGIN}/auth/callback`),
      "unexpected callback destination",
    );
    assertCookieMetadata(cookieMetadata(prepared.metadata, CONTEXT_COOKIE), {
      httpOnly: true,
      sameSite: "lax",
      secure: false,
      path: "/",
    });
    assert.ok(jar.has(CONTEXT_COOKIE), "PREPARE_SIGN_IN did not establish Auth context");
    const contextBeforeInvalidRequests = jar.get(CONTEXT_COOKIE);
    const preparedJar = jar.clone();
    const correlationCookies = jar.names().filter(
      (name) => name.startsWith(CORRELATION_COOKIE_PREFIX),
    );
    assert.ok(correlationCookies.length === 1, "PREPARE_SIGN_IN did not establish correlation");
    assert.ok(/^[a-f0-9]{64}$/.test(jar.get(correlationCookies[0])));

    provider.setUserMode("success");
    const tokenRequestsBeforeCallback = provider.requests.filter(
      ({ pathname }) => pathname === "/auth/v1/token",
    ).length;
    const callback = await followProviderSignIn(
      provider,
      jar,
      prepared.body.redirectUrl,
    );
    assert.ok(
      provider.requests.filter(({ pathname }) => pathname === "/auth/v1/authorize").length === 1,
      "expected exactly one provider-navigation request",
    );
    assert.ok(
      provider.requests.filter(({ pathname }) => pathname === "/auth/v1/token").length ===
        tokenRequestsBeforeCallback + 1,
      "callback rejected a correlated PKCE flow before provider code exchange",
    );
    assertExactRecord(callback.body, { ok: true, destination: "/runs?view=mine" });
    assert.ok(jar.has(PROVIDER_COOKIE), "callback did not establish a provider session");
    assert.ok(jar.has(BINDING_COOKIE), "callback did not establish a session binding");
    assert.ok(!jar.has(TOMBSTONE_COOKIE), "callback unexpectedly established a tombstone");
    assertCookieMetadata(cookieMetadata(callback.metadata, BINDING_COOKIE), {
      httpOnly: true,
      sameSite: "lax",
      secure: false,
      path: "/",
    });

    const authenticated = await post(jar, { operation: "RESOLVE_SESSION" }, csrfToken);
    assertAuthResponse(
      authenticated,
      200,
      { state: "AUTHENTICATED", userReference: "fixture-user" },
      jar,
    );
    assert.ok(authenticated.body.userReference.length > 0, "userReference must be non-empty");
    const eligibleSessionJar = jar.clone();

    const invalidCases = [
      {
        body: { operation: "PUBLISH_SIGN_OUT" },
        overrides: { headers: { origin: null } },
        status: 403,
      },
      {
        body: { operation: "PUBLISH_SIGN_OUT" },
        overrides: { headers: { origin: "https://foreign.example.test" } },
        status: 403,
      },
      {
        body: { operation: "PREPARE_SIGN_IN" },
        overrides: { headers: { "x-auth-csrf": "incorrect-csrf-token" } },
        status: 403,
      },
      {
        body: { operation: "PREPARE_SIGN_IN" },
        overrides: { headers: { "x-auth-csrf": null } },
        status: 403,
      },
      {
        body: { operation: "PUBLISH_SIGN_OUT" },
        removeCsrfCookie: true,
        status: 403,
      },
      {
        body: null,
        overrides: { rawBody: "{" },
        status: 400,
      },
      {
        body: { operation: "DELETE_EVERYTHING" },
        status: 400,
      },
      {
        body: { operation: "RESOLVE_SESSION", extra: true },
        status: 400,
      },
    ];
    for (const invalid of invalidCases) {
      const invalidJar = preparedJar.clone();
      if (invalid.removeCsrfCookie) invalidJar.delete(CSRF_COOKIE);
      const result = await post(invalidJar, invalid.body, csrfToken, invalid.overrides);
      assertAuthResponse(result, invalid.status, { error: "AUTH_REQUEST_FAILED" }, invalidJar);
      assert.ok(invalidJar.get(CONTEXT_COOKIE) === contextBeforeInvalidRequests);
      assert.ok(!invalidJar.has(TOMBSTONE_COOKIE), "rejected mutation created a tombstone");
    }

    const providerCookie = fakeProviderSessionCookie(provider.origin);
    for (const mode of ["success", "rejected", "unavailable"]) {
      provider.setUserMode(mode);
      const provisionalJar = preparedJar.clone();
      provisionalJar.set(PROVIDER_COOKIE, providerCookie);
      const beforeUserRequests = provider.requests.filter(
        ({ pathname }) => pathname === "/auth/v1/user",
      ).length;
      const unresolved = await post(
        provisionalJar,
        { operation: "RESOLVE_SESSION" },
        csrfToken,
      );
      assertAuthResponse(
        unresolved,
        200,
        { state: "UNAUTHENTICATED", userReference: null },
        provisionalJar,
      );
      assert.ok(
        provider.requests.filter(({ pathname }) => pathname === "/auth/v1/user").length ===
          beforeUserRequests + 1,
        `provider ${mode} path was not exercised`,
      );
    }

    provider.setUserMode("success");
    const delayedResolveJar = jar.clone();
    const gate = provider.armUserGate();
    const delayedResolve = post(
      delayedResolveJar,
      { operation: "RESOLVE_SESSION" },
      csrfToken,
    );
    await Promise.race([
      gate.arrived,
      delay(REQUEST_TIMEOUT_MS).then(() => assert.fail("provider barrier was not reached")),
    ]);
    let published;
    try {
      published = await post(jar, { operation: "PUBLISH_SIGN_OUT" }, csrfToken);
    } finally {
      gate.release();
    }
    assertAuthResponse(published, 200, { ok: true }, jar);
    const resolvedAfterPublish = await delayedResolve;
    assertAuthResponse(
      resolvedAfterPublish,
      200,
      { state: "UNAUTHENTICATED", userReference: null },
      delayedResolveJar,
    );

    assert.ok(jar.get(CONTEXT_COOKIE) === contextBeforeInvalidRequests);
    assert.ok(jar.has(TOMBSTONE_COOKIE), "PUBLISH_SIGN_OUT did not create a tombstone");
    assertCookieMetadata(cookieMetadata(published.metadata, TOMBSTONE_COOKIE), {
      httpOnly: false,
      sameSite: "lax",
      secure: false,
      path: "/",
    });
    assertCookieMetadata(cookieMetadata(published.metadata, BINDING_COOKIE), {
      httpOnly: true,
      sameSite: "lax",
      secure: false,
      maxAge: 0,
      path: "/",
    });

    const tombstoneBeforeResolve = jar.get(TOMBSTONE_COOKIE);
    const afterSignOut = await post(jar, { operation: "RESOLVE_SESSION" }, csrfToken);
    assertAuthResponse(
      afterSignOut,
      200,
      { state: "UNAUTHENTICATED", userReference: null },
      jar,
    );
    assert.ok(jar.get(TOMBSTONE_COOKIE) === tombstoneBeforeResolve);

    const staleReplayJar = jar.clone();
    staleReplayJar.set(PROVIDER_COOKIE, eligibleSessionJar.get(PROVIDER_COOKIE));
    staleReplayJar.set(BINDING_COOKIE, eligibleSessionJar.get(BINDING_COOKIE));
    const staleProviderObserved = await post(
      staleReplayJar,
      { operation: "RESOLVE_SESSION" },
      csrfToken,
    );
    assertAuthResponse(
      staleProviderObserved,
      200,
      { state: "UNAUTHENTICATED", userReference: null },
      staleReplayJar,
    );
    assert.ok(staleReplayJar.get(TOMBSTONE_COOKIE) === tombstoneBeforeResolve);

    const failedAfterTombstone = await post(
      jar,
      { operation: "PREPARE_SIGN_IN" },
      csrfToken,
      { headers: { "x-auth-csrf": "incorrect-csrf-token" } },
    );
    assertAuthResponse(
      failedAfterTombstone,
      403,
      { error: "AUTH_REQUEST_FAILED" },
      jar,
    );
    assert.ok(jar.get(TOMBSTONE_COOKIE) === tombstoneBeforeResolve);

    const reconciled = await post(
      jar,
      { operation: "PREPARE_SIGN_IN", intendedReturn: "/runs" },
      csrfToken,
    );
    assertAuthResponse(reconciled, 200, { redirectUrl: reconciled.body.redirectUrl }, jar);
    assert.ok(!jar.has(TOMBSTONE_COOKIE), "authorized PREPARE_SIGN_IN did not clear tombstone");
    assertCookieMetadata(cookieMetadata(reconciled.metadata, TOMBSTONE_COOKIE), {
      httpOnly: false,
      sameSite: "lax",
      secure: false,
      maxAge: 0,
      path: "/",
    });

    const freshCallback = await followProviderSignIn(provider, jar, reconciled.body.redirectUrl);
    assertExactRecord(freshCallback.body, { ok: true, destination: "/runs" });
    const freshSession = await post(jar, { operation: "RESOLVE_SESSION" }, csrfToken);
    assertAuthResponse(
      freshSession,
      200,
      { state: "AUTHENTICATED", userReference: "fixture-user" },
      jar,
    );

    await stopApp(runtime.child);
    appStopped = true;
    await assert.rejects(
      fetch(`${APP_ORIGIN}/auth/session-fence`, {
        signal: AbortSignal.timeout(500),
      }),
    );
  } finally {
    if (!appStopped) await stopApp(runtime.child);
    removeSignalCleanup();
    await provider.close();
  }
});
