"use server";

import { processAuthCallback, type CallbackOutcome } from "@/providers/authServer";

/**
 * Relays the callback query to `AuthAdapter.processCallback` and returns only
 * the presentation-safe outcome. No provider diagnostic, internal callback
 * classification, correlation detail, PKCE detail, token or cookie crosses this
 * boundary.
 */
export async function completeAuthCallback(callbackQuery: string): Promise<CallbackOutcome> {
  return processAuthCallback(callbackQuery);
}
