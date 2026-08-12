import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { executeAuthSessionFenceHostRequest, validateAuthMutationRequest } from "@/auth";
import { AUTH_CSRF_COOKIE, applicationOrigin } from "@/providers/authConfig";
import { createAuthSessionFenceHost } from "@/providers/authServer";

const NO_STORE = { "cache-control": "private, no-store" } as const;
const FAILED = { error: "AUTH_REQUEST_FAILED" } as const;

export async function POST(request: Request) {
  const expectedCsrfToken = (await cookies()).get(AUTH_CSRF_COOKIE)?.value;
  const validation = expectedCsrfToken
    ? validateAuthMutationRequest(request, applicationOrigin(), expectedCsrfToken)
    : null;
  if (!validation?.ok) {
    return NextResponse.json(FAILED, { status: 403, headers: NO_STORE });
  }

  let input: unknown;
  try {
    input = await request.json();
  } catch {
    return NextResponse.json(FAILED, { status: 400, headers: NO_STORE });
  }

  try {
    const response = await executeAuthSessionFenceHostRequest(
      await createAuthSessionFenceHost(),
      input,
    );
    return NextResponse.json(response, { headers: NO_STORE });
  } catch {
    return NextResponse.json(FAILED, { status: 400, headers: NO_STORE });
  }
}
