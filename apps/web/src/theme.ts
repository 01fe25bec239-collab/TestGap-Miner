"use client";

import { createTheme } from "@mui/material/styles";

const systemFont = [
  "system-ui",
  "-apple-system",
  "BlinkMacSystemFont",
  '"Segoe UI"',
  "sans-serif",
].join(",");

const theme = createTheme({
  cssVariables: true,
  palette: {
    mode: "light",
    primary: {
      main: "#2457C5",
      dark: "#173B86",
      light: "#DCE7FF",
    },
    success: {
      main: "#237A57",
      dark: "#14513A",
    },
    background: {
      default: "#F4F6FA",
      paper: "#FFFFFF",
    },
    text: {
      primary: "#162033",
      secondary: "#4B5870",
    },
    divider: "#D7DDEA",
  },
  spacing: 8,
  shape: {
    borderRadius: 12,
  },
  typography: {
    fontFamily: systemFont,
    h1: {
      fontSize: "clamp(2.25rem, 6vw, 4rem)",
      fontWeight: 750,
      letterSpacing: "-0.045em",
      lineHeight: 1.05,
    },
    h2: {
      fontSize: "clamp(1.5rem, 3vw, 2rem)",
      fontWeight: 700,
      letterSpacing: "-0.025em",
      lineHeight: 1.2,
    },
    h3: {
      fontSize: "1rem",
      fontWeight: 700,
      lineHeight: 1.35,
    },
    body1: {
      fontSize: "1.0625rem",
      lineHeight: 1.7,
    },
    body2: {
      lineHeight: 1.55,
    },
    overline: {
      fontWeight: 750,
      letterSpacing: "0.08em",
    },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          minHeight: "100vh",
        },
      },
    },
    MuiButtonBase: {
      styleOverrides: {
        root: {
          "&.Mui-focusVisible": {
            outline: "3px solid #173B86",
            outlineOffset: 2,
          },
        },
      },
    },
    MuiIconButton: {
      styleOverrides: {
        root: {
          minWidth: 44,
          minHeight: 44,
        },
      },
    },
    MuiLink: {
      defaultProps: {
        underline: "hover",
      },
      styleOverrides: {
        root: {
          "&:focus-visible": {
            outline: "3px solid #173B86",
            outlineOffset: 2,
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        rounded: {
          borderRadius: 16,
        },
      },
    },
  },
});

export default theme;
