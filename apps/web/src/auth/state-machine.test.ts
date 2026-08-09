import { describe, expect, it, vi } from "vitest";
import { AuthStateMachine, InvalidAuthTransition } from "./state-machine";
import { AUTH_SESSION_STATES } from "./types";

describe("AuthStateMachine", () => {
  it("preserves the exact nine-state vocabulary", () => {
    expect(AUTH_SESSION_STATES).toEqual([
      "INITIALIZING",
      "UNAUTHENTICATED",
      "SIGN_IN_PENDING",
      "CALLBACK_PROCESSING",
      "AUTHENTICATED",
      "REFRESH_PENDING",
      "SIGN_OUT_PENDING",
      "RECOVERABLE_ERROR",
      "TERMINAL_SESSION_ERROR",
    ]);
  });

  it("executes valid sign-in, refresh, and sign-out transitions", () => {
    const machine = new AuthStateMachine();
    machine.transition("UNAUTHENTICATED");
    machine.transition("SIGN_IN_PENDING");
    machine.transition("CALLBACK_PROCESSING");
    machine.transition("AUTHENTICATED", { userReference: "user-1" });
    machine.transition("REFRESH_PENDING", {
      refreshMode: "PROVEN_CREDENTIAL",
      userReference: "user-1",
    });
    machine.transition("AUTHENTICATED", { userReference: "user-1" });
    machine.transition("SIGN_OUT_PENDING");
    expect(machine.transition("UNAUTHENTICATED").state).toBe("UNAUTHENTICATED");
  });

  it("fails closed on an invalid transition", () => {
    const machine = new AuthStateMachine();
    expect(() => machine.transition("REFRESH_PENDING")).toThrow(InvalidAuthTransition);
    expect(machine.snapshot).toMatchObject({
      state: "TERMINAL_SESSION_ERROR",
      canRenderProtectedContent: false,
      canMakeApiRequest: false,
    });
  });

  it("requires an explicit refresh mode", () => {
    const machine = new AuthStateMachine();
    machine.transition("AUTHENTICATED", { userReference: "user-1" });
    expect(() => machine.transition("REFRESH_PENDING")).toThrow(InvalidAuthTransition);
    expect(machine.snapshot.state).toBe("TERMINAL_SESSION_ERROR");
  });

  it("keeps proven refresh visible but never request-eligible", () => {
    const machine = new AuthStateMachine();
    machine.transition("AUTHENTICATED", { userReference: "user-1" });
    const snapshot = machine.transition("REFRESH_PENDING", {
      refreshMode: "PROVEN_CREDENTIAL",
      userReference: "user-1",
    });
    expect(snapshot).toMatchObject({
      userReference: "user-1",
      canRenderProtectedContent: true,
      canMakeApiRequest: false,
    });
  });

  it("degrades refresh proof one-way and removes protected state", () => {
    const machine = new AuthStateMachine();
    machine.transition("AUTHENTICATED", { userReference: "user-1" });
    machine.transition("REFRESH_PENDING", {
      refreshMode: "PROVEN_CREDENTIAL",
      userReference: "user-1",
    });
    const snapshot = machine.transition("REFRESH_PENDING", {
      refreshMode: "UNPROVEN_CREDENTIAL",
    });
    expect(snapshot).toMatchObject({
      refreshMode: "UNPROVEN_CREDENTIAL",
      userReference: null,
      canRenderProtectedContent: false,
    });
  });

  it("supports explicit recovery and idempotent repeated state", () => {
    const machine = new AuthStateMachine();
    const listener = vi.fn();
    machine.subscribe(listener);
    machine.transition("UNAUTHENTICATED");
    machine.transition("SIGN_IN_PENDING");
    machine.transition("RECOVERABLE_ERROR");
    machine.transition("UNAUTHENTICATED");
    machine.transition("UNAUTHENTICATED");
    expect(machine.snapshot.state).toBe("UNAUTHENTICATED");
    expect(listener).toHaveBeenCalledTimes(5);
  });
});
