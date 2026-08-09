export const DEFAULT_AUTH_DESTINATION = "/" as const;

const CONTROL_CHARACTER = /[\u0000-\u001f\u007f]/;
const SCHEME = /[a-z][a-z0-9+.-]*:/i;
const ENCODED_DELIMITER = /%(?:00|0a|0d|2f|3a|40|5c)/i;
const NESTED_REDIRECT = /^(?:continue|destination|next|redirect|redirect_uri|return|return_to|url)$/i;

export function validateIntendedReturn(candidate?: string): string {
  if (!candidate) return DEFAULT_AUTH_DESTINATION;
  if (
    !candidate.startsWith("/") ||
    candidate.startsWith("//") ||
    candidate.startsWith("/\\") ||
    candidate.includes("\\") ||
    candidate.includes("@") ||
    CONTROL_CHARACTER.test(candidate) ||
    SCHEME.test(candidate)
  ) {
    return DEFAULT_AUTH_DESTINATION;
  }

  let decoded: string;
  try {
    decoded = decodeURIComponent(candidate);
  } catch {
    return DEFAULT_AUTH_DESTINATION;
  }

  if (
    decoded.startsWith("//") ||
    decoded.startsWith("/\\") ||
    decoded.includes("\\") ||
    decoded.includes("@") ||
    CONTROL_CHARACTER.test(decoded) ||
    SCHEME.test(decoded) ||
    ENCODED_DELIMITER.test(decoded)
  ) {
    return DEFAULT_AUTH_DESTINATION;
  }

  try {
    const parsed = new URL(decoded, "https://auth.invalid");
    if (parsed.origin !== "https://auth.invalid" || parsed.pathname === "/auth/callback") {
      return DEFAULT_AUTH_DESTINATION;
    }
    for (const [name, value] of parsed.searchParams) {
      if (NESTED_REDIRECT.test(name) && (SCHEME.test(value) || value.startsWith("//"))) {
        return DEFAULT_AUTH_DESTINATION;
      }
    }
  } catch {
    return DEFAULT_AUTH_DESTINATION;
  }

  return decoded;
}
