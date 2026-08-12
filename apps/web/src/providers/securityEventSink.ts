import type { AuthSecurityEvent } from "@/auth";

const DEFAULT_RETENTION = 100;

/** Process-local, bounded inspection sink for the local Dashboard runtime. */
export class LocalAuthSecurityEventSink {
  #events: AuthSecurityEvent[] = [];

  constructor(private readonly retention = DEFAULT_RETENTION) {
    if (!Number.isSafeInteger(retention) || retention < 1) {
      throw new Error("Auth security event retention must be a positive integer");
    }
  }

  emit = (event: AuthSecurityEvent) => {
    this.#events.push(event);
    if (this.#events.length > this.retention) this.#events.shift();
  };

  snapshot(): readonly AuthSecurityEvent[] {
    return Object.freeze([...this.#events]);
  }
}

export const localAuthSecurityEventSink = new LocalAuthSecurityEventSink();
