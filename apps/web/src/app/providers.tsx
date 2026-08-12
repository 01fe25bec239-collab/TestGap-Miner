"use client";

import CssBaseline from "@mui/material/CssBaseline";
import { ThemeProvider } from "@mui/material/styles";
import type { ReactNode } from "react";
import AuthSessionProvider from "@/providers/AuthSessionProvider";
import theme from "@/theme";

export default function Providers({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AuthSessionProvider>{children}</AuthSessionProvider>
    </ThemeProvider>
  );
}
