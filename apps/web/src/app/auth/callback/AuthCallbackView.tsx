"use client";

import ErrorOutlineRounded from "@mui/icons-material/ErrorOutlineRounded";
import Alert from "@mui/material/Alert";
import AlertTitle from "@mui/material/AlertTitle";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { useEffect, useState } from "react";
import { DEFAULT_AUTH_DESTINATION } from "@/auth";
import { resolveBrowserAuthSession } from "@/providers/AuthSessionProvider";
import { replaceWithSafeDestination } from "@/providers/navigation";
import { completeAuthCallback } from "./actions";
import type { CallbackOutcome } from "@/providers/authServer";

export default function AuthCallbackView() {
  const [outcome, setOutcome] = useState<CallbackOutcome | null>(null);

  useEffect(() => {
    let active = true;
    // The query is relayed to the Auth boundary unread and removed from browser
    // history immediately. It is never parsed, rendered, logged or stored.
    const callbackQuery = window.location.search;
    window.history.replaceState(null, "", window.location.pathname);

    void (async () => {
      try {
        const result = await completeAuthCallback(callbackQuery);
        const resolved = result.ok ? await resolveBrowserAuthSession() : null;
        if (!active) return;
        setOutcome(
          result.ok && result.destination && resolved?.state === "AUTHENTICATED"
            ? result
            : { ok: false, destination: null },
        );
      } catch {
        if (active) setOutcome({ ok: false, destination: null });
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (outcome?.ok && outcome.destination) replaceWithSafeDestination(outcome.destination);
  }, [outcome]);

  if (!outcome || outcome.ok) {
    return (
      <Paper component="section" variant="outlined" sx={{ p: { xs: 3, md: 5 } }}>
        <Stack spacing={2} sx={{ alignItems: "flex-start" }}>
          <Typography id="page-title" variant="h1">
            Completing sign-in
          </Typography>
          <Stack role="status" direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
            <CircularProgress size={22} aria-hidden="true" />
            <Typography color="text.secondary">
              {outcome
                ? "Sign-in complete. Taking you to TestGap Miner."
                : "Verifying your sign-in with GitHub. This only takes a moment."}
            </Typography>
          </Stack>
        </Stack>
      </Paper>
    );
  }

  return (
    <Paper component="section" variant="outlined" sx={{ p: { xs: 3, md: 5 } }}>
      <Stack spacing={2.5} sx={{ alignItems: "flex-start" }}>
        <Typography id="page-title" variant="h1">
          Sign-in failed
        </Typography>
        <Alert
          severity="error"
          icon={<ErrorOutlineRounded aria-hidden="true" />}
          sx={{ width: "100%" }}
        >
          <AlertTitle>We could not sign you in</AlertTitle>
          Your sign-in attempt was not accepted. No account, session or repository access has
          changed. You can return to TestGap Miner and try signing in again.
        </Alert>
        <Button variant="contained" href={outcome.destination ?? DEFAULT_AUTH_DESTINATION}>
          Return to TestGap Miner
        </Button>
      </Stack>
    </Paper>
  );
}
