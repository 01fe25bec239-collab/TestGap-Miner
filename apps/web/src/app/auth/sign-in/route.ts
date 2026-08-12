import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { createAuthCsrfToken } from "@/auth";
import { AUTH_CSRF_COOKIE, applicationOrigin } from "@/providers/authConfig";

const NO_STORE = { "cache-control": "private, no-store" } as const;
const CSRF_TOKEN_MAX_AGE = 60 * 60;

/** Issues the mutation token the Auth boundary requires for sign-in. */
export async function GET() {
  const origin = applicationOrigin();
  const cookieStore = await cookies();
  let csrfToken = cookieStore.get(AUTH_CSRF_COOKIE)?.value;

  if (!csrfToken) {
    csrfToken = createAuthCsrfToken();
    cookieStore.set(AUTH_CSRF_COOKIE, csrfToken, {
      httpOnly: true,
      sameSite: "lax",
      secure: origin.startsWith("https://"),
      path: "/",
      maxAge: CSRF_TOKEN_MAX_AGE,
    });
  }

  return NextResponse.json({ csrfToken }, { headers: NO_STORE });
}
