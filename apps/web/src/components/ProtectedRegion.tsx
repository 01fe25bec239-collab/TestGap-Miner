"use client";

import Paper from "@mui/material/Paper";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import type { ReactNode } from "react";
import type { AuthSessionState } from "@/auth";
import { useAuthSession } from "@/providers/AuthSessionProvider";

const GATE_MESSAGE: Readonly<Record<AuthSessionState, string>> = {
  INITIALIZING: "Checking your sign-in status.",
  UNAUTHENTICATED: "Sign in with GitHub to view this content.",
  SIGN_IN_PENDING: "Taking you to GitHub to sign in.",
  CALLBACK_PROCESSING: "Completing sign-in.",
  AUTHENTICATED: "Loading your content.",
  REFRESH_PENDING: "Reverifying your session before showing this content.",
  SIGN_OUT_PENDING: "Signing out.",
  RECOVERABLE_ERROR: "Sign-in failed, so this content is not available.",
  TERMINAL_SESSION_ERROR: "Your session ended, so this content is not available.",
};

const PLACEHOLDER_STATES = new Set<AuthSessionState>([
  "INITIALIZING",
  "SIGN_IN_PENDING",
  "CALLBACK_PROCESSING",
  "REFRESH_PENDING",
  "SIGN_OUT_PENDING",
]);

/**
 * Mounts protected presentation only while the Auth snapshot proves it may be
 * rendered. Protected children are never rendered speculatively, so no
 * authenticated content can appear before Auth proof or survive sign-out.
 */
export default function ProtectedRegion({ children }: Readonly<{ children: ReactNode }>) {
  const { snapshot } = useAuthSession();
  if (snapshot.canRenderProtectedContent) return <>{children}</>;

  return (
    <Paper variant="outlined" sx={{ p: 3 }}>
      <Stack spacing={2}>
        <Typography role="status" variant="body1" color="text.secondary">
          {GATE_MESSAGE[snapshot.state]}
        </Typography>
        {PLACEHOLDER_STATES.has(snapshot.state) ? (
          <Stack spacing={1} aria-hidden="true">
            <Skeleton variant="rounded" height={24} width="45%" />
            <Skeleton variant="rounded" height={96} />
          </Stack>
        ) : null}
      </Stack>
    </Paper>
  );
}
