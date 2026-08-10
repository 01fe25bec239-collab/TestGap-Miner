import { cookies } from "next/headers";
import {
  createAuthCallbackProviderWithCookies,
  createAuthServerClientWithCookies,
} from "./supabase";

export async function createAuthServerClient(
  origin: string,
  setResponseHeaders: (headers: Readonly<Record<string, string>>) => void,
) {
  const cookieStore = await cookies();
  return createAuthServerClientWithCookies(origin, {
    getAll: () => cookieStore.getAll(),
    setAll: (cookiesToSet, headers) => {
      for (const { name, value, options } of cookiesToSet) {
        cookieStore.set(name, value, options);
      }
      setResponseHeaders(headers);
    },
  });
}

export async function createAuthCallbackProvider(
  origin: string,
  setResponseHeaders: (headers: Readonly<Record<string, string>>) => void,
) {
  const cookieStore = await cookies();
  return createAuthCallbackProviderWithCookies(origin, {
    getAll: () => cookieStore.getAll(),
    setAll: (cookiesToSet, headers) => {
      for (const { name, value, options } of cookiesToSet) {
        cookieStore.set(name, value, options);
      }
      setResponseHeaders(headers);
    },
  });
}
