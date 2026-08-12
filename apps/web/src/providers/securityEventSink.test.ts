import { describe, expect, it } from "vitest";
import type { AuthSecurityEvent } from "@/auth";
import { LocalAuthSecurityEventSink } from "./securityEventSink";

function event(requestReference: string): AuthSecurityEvent {
  return Object.freeze({
    eventName: "AUTH_INVALID_CALLBACK",
    classification: "INVALID_CALLBACK",
    occurredAt: "2026-08-11T00:00:00.000Z",
    environmentClass: "LOCAL_DEVELOPMENT",
    sourceComponent: "AUTH",
    outcome: "REJECTED",
    blockingEffect: "CALLBACK_REJECTED",
    actorType: "UNAUTHENTICATED",
    actorReference: "UNAUTHENTICATED",
    signInAttemptReference: null,
    callbackFlowReference: null,
    requestReference,
    correlationReference: null,
    policyVersion: "testgap-local-auth@1",
    sessionPreserved: false,
    reasonCode: "INVALID_CALLBACK",
    redactionStatus: "SECRET_FREE",
    callbackSuccess: false,
    rejectedCallbackDestinationUsed: false,
  });
}

describe("LocalAuthSecurityEventSink", () => {
  it("retains Auth-owned events without rewriting their fields", () => {
    const sink = new LocalAuthSecurityEventSink();
    const received = event("request-1");

    sink.emit(received);

    expect(sink.snapshot()).toEqual([received]);
    expect(sink.snapshot()[0]).toBe(received);
  });

  it("evicts the oldest event at the configured bound", () => {
    const sink = new LocalAuthSecurityEventSink(2);
    sink.emit(event("request-1"));
    sink.emit(event("request-2"));
    sink.emit(event("request-3"));

    expect(sink.snapshot().map(({ requestReference }) => requestReference)).toEqual([
      "request-2",
      "request-3",
    ]);
  });
});
