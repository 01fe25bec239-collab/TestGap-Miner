"use client";

import ErrorOutlineRounded from "@mui/icons-material/ErrorOutlineRounded";
import GitHub from "@mui/icons-material/GitHub";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import type { ReactNode } from "react";
import { useAuthSession } from "@/providers/AuthSessionProvider";

function Progress({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <Stack role="status" direction="row" spacing={1} sx={{ alignItems: "center" }}>
      <CircularProgress size={18} aria-hidden="true" />
      <Typography variant="body2" color="text.secondary">
        {children}
      </Typography>
    </Stack>
  );
}

function Failure({ message, action }: Readonly<{ message: string; action: ReactNode }>) {
  return (
    <Stack role="alert" direction="row" spacing={1} sx={{ alignItems: "center" }}>
      <ErrorOutlineRounded color="error" aria-hidden="true" />
      <Typography variant="body2" color="error.main" sx={{ fontWeight: 700 }}>
        {message}
      </Typography>
      {action}
    </Stack>
  );
}

function SignedInIdentity({ userReference }: Readonly<{ userReference: string }>) {
  return (
    <Chip
      variant="outlined"
      size="small"
      label={userReference}
      aria-label={`Signed in as ${userReference}`}
      sx={{ maxWidth: 220 }}
    />
  );
}

/**
 * The authenticated and unauthenticated shell control. Every branch is chosen
 * from the Auth session snapshot; this component holds no session state of its
 * own and never reads provider data, tokens or cookies.
 */
export default function AuthStatus() {
  const { snapshot, configured, signIn, signOut } = useAuthSession();

  const signOutButton = (
    <Button color="inherit" variant="outlined" size="small" onClick={signOut}>
      Sign out
    </Button>
  );

  if (!configured) {
    return (
      <Stack role="status" direction="row" spacing={1} sx={{ alignItems: "center" }}>
        <ErrorOutlineRounded color="warning" aria-hidden="true" />
        <Typography variant="body2" color="text.secondary">
          Sign-in is unavailable in this environment
        </Typography>
      </Stack>
    );
  }

  switch (snapshot.state) {
    case "INITIALIZING":
      return <Progress>Checking your sign-in status</Progress>;

    case "UNAUTHENTICATED":
      return (
        <Button
          variant="contained"
          size="small"
          startIcon={<GitHub aria-hidden="true" />}
          onClick={signIn}
        >
          Sign in with GitHub
        </Button>
      );

    case "SIGN_IN_PENDING":
      return (
        <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
          <Button
            variant="contained"
            size="small"
            disabled
            startIcon={<CircularProgress size={16} aria-hidden="true" color="inherit" />}
          >
            Sign in with GitHub
          </Button>
          <Typography role="status" variant="body2" color="text.secondary">
            Taking you to GitHub to sign in
          </Typography>
        </Stack>
      );

    case "CALLBACK_PROCESSING":
      return <Progress>Completing sign-in</Progress>;

    case "AUTHENTICATED":
      return (
        <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
          {snapshot.userReference ? (
            <SignedInIdentity userReference={snapshot.userReference} />
          ) : null}
          {signOutButton}
        </Stack>
      );

    case "REFRESH_PENDING":
      return (
        <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
          {snapshot.userReference ? (
            <SignedInIdentity userReference={snapshot.userReference} />
          ) : null}
          <Progress>Reverifying your session</Progress>
          {signOutButton}
        </Stack>
      );

    case "SIGN_OUT_PENDING":
      return <Progress>Signing out</Progress>;

    case "RECOVERABLE_ERROR":
      return (
        <Failure
          message="Sign-in failed"
          action={
            <Button variant="outlined" size="small" onClick={signIn}>
              Try again
            </Button>
          }
        />
      );

    case "TERMINAL_SESSION_ERROR":
      return <Failure message="Your session ended" action={signOutButton} />;
  }
}
