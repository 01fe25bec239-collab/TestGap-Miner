/**
 * Full-document navigation to a destination the Auth boundary authorized. A
 * document load is required rather than a client-side route change so the
 * browser Auth runtime reads the session the server just established.
 */
export function replaceWithSafeDestination(destination: string) {
  window.location.replace(destination);
}
