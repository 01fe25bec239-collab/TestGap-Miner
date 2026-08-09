export const PENDING_CORRELATION_TTL_MS = 10 * 60 * 1_000;
export const COMPLETED_CORRELATION_TTL_MS = 120 * 1_000;
export const CORRELATION_COOKIE_PREFIX = "testgap-auth-correlation-";
const SECURITY_POLICY_VERSION = /^[\x21-\x7e]{1,128}$/;

export type CompletedCallbackOutcome = Readonly<{
  userReference: string;
}>;

export type PendingCorrelation = Readonly<{
  lifecycle: "PENDING_ATTEMPT_CORRELATION";
  handle: string;
  flowId: string;
  securityPolicyVersion: string;
  intendedReturn: string;
  createdAt: number;
  expiresAt: number;
}>;

export type CompletedCorrelation = Readonly<{
  lifecycle: "COMPLETED_CALLBACK_CORRELATION";
  handle: string;
  flowId: string;
  securityPolicyVersion: string;
  outcome: CompletedCallbackOutcome;
  completedAt: number;
  expiresAt: number;
}>;

export type CorrelationRecord = PendingCorrelation | CompletedCorrelation;

export interface CorrelationStore {
  createPending(input: {
    handle: string;
    flowId: string;
    securityPolicyVersion: string;
    intendedReturn: string;
    now: number;
  }): Promise<PendingCorrelation>;
  lookup(handle: string, flowId: string, now: number): Promise<CorrelationRecord | null>;
  complete(
    handle: string,
    flowId: string,
    outcome: CompletedCallbackOutcome,
    now: number,
  ): Promise<{ record: CompletedCorrelation; consumedIntendedReturn: string } | null>;
  remove(handle: string): Promise<void>;
  cleanup(now: number): Promise<number>;
}

/**
 * LOCAL_NON_PRODUCTION_ONLY: process-local, non-durable, and not correct for
 * multi-instance or cross-region deployment. Replace the CorrelationStore
 * implementation for production without changing Auth semantics.
 */
export class LocalCorrelationStore implements CorrelationStore {
  #records = new Map<string, CorrelationRecord>();
  #available = true;

  setAvailable(available: boolean) {
    this.#available = available;
  }

  async createPending(input: {
    handle: string;
    flowId: string;
    securityPolicyVersion: string;
    intendedReturn: string;
    now: number;
  }): Promise<PendingCorrelation> {
    this.#assertAvailable();
    this.#deleteExpired(input.now);
    if (!isValidSecurityPolicyVersion(input.securityPolicyVersion)) {
      throw new Error("Invalid Security policy version");
    }
    if (this.#records.has(input.handle)) throw new Error("Correlation handle collision");

    const record: PendingCorrelation = Object.freeze({
      lifecycle: "PENDING_ATTEMPT_CORRELATION",
      handle: input.handle,
      flowId: input.flowId,
      securityPolicyVersion: input.securityPolicyVersion,
      intendedReturn: input.intendedReturn,
      createdAt: input.now,
      expiresAt: input.now + PENDING_CORRELATION_TTL_MS,
    });
    this.#records.set(input.handle, record);
    return record;
  }

  async lookup(handle: string, flowId: string, now: number): Promise<CorrelationRecord | null> {
    this.#assertAvailable();
    this.#deleteExpired(now);
    const record = this.#records.get(handle);
    return record?.flowId === flowId ? record : null;
  }

  async complete(
    handle: string,
    flowId: string,
    outcome: CompletedCallbackOutcome,
    now: number,
  ): Promise<{ record: CompletedCorrelation; consumedIntendedReturn: string } | null> {
    this.#assertAvailable();
    this.#deleteExpired(now);
    const pending = this.#records.get(handle);
    if (pending?.lifecycle !== "PENDING_ATTEMPT_CORRELATION" || pending.flowId !== flowId) {
      return null;
    }

    const record: CompletedCorrelation = Object.freeze({
      lifecycle: "COMPLETED_CALLBACK_CORRELATION",
      handle,
      flowId,
      securityPolicyVersion: pending.securityPolicyVersion,
      outcome: Object.freeze(outcome),
      completedAt: now,
      expiresAt: now + COMPLETED_CORRELATION_TTL_MS,
    });
    this.#records.set(handle, record);
    return { record, consumedIntendedReturn: pending.intendedReturn };
  }

  async remove(handle: string): Promise<void> {
    this.#assertAvailable();
    this.#records.delete(handle);
  }

  async cleanup(now: number): Promise<number> {
    this.#assertAvailable();
    return this.#deleteExpired(now);
  }

  #deleteExpired(now: number) {
    let removed = 0;
    for (const [handle, record] of this.#records) {
      if (record.expiresAt <= now) {
        this.#records.delete(handle);
        removed += 1;
      }
    }
    return removed;
  }

  #assertAvailable() {
    if (!this.#available) throw new Error("Correlation store unavailable");
  }
}

export function isValidSecurityPolicyVersion(value: string): boolean {
  return typeof value === "string" && SECURITY_POLICY_VERSION.test(value);
}

export function createOpaqueCorrelationHandle(): string {
  const bytes = new Uint8Array(32);
  globalThis.crypto.getRandomValues(bytes);
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

export type CorrelationCookie = Readonly<{
  name: string;
  value: string;
  options: Readonly<{
    httpOnly: true;
    secure: boolean;
    sameSite: "lax";
    path: "/auth/callback";
    maxAge: number;
  }>;
}>;

export function correlationCookie(handle: string, origin: string): CorrelationCookie {
  return Object.freeze({
    name: `${CORRELATION_COOKIE_PREFIX}${handle.slice(0, 16)}`,
    value: handle,
    options: Object.freeze({
      httpOnly: true,
      secure: origin !== "http://localhost:3000",
      sameSite: "lax",
      path: "/auth/callback",
      maxAge: PENDING_CORRELATION_TTL_MS / 1_000,
    }),
  });
}

export function completedCorrelationCookie(handle: string, origin: string): CorrelationCookie {
  const cookie = correlationCookie(handle, origin);
  return {
    ...cookie,
    options: { ...cookie.options, maxAge: COMPLETED_CORRELATION_TTL_MS / 1_000 },
  };
}

export function readCorrelationHandles(
  cookies: readonly Readonly<{ name: string; value: string }>[],
): string[] {
  return cookies
    .filter(
      ({ name, value }) =>
        name.startsWith(CORRELATION_COOKIE_PREFIX) && /^[a-f0-9]{64}$/.test(value),
    )
    .map(({ value }) => value);
}
