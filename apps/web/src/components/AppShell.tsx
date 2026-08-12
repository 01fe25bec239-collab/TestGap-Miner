"use client";

import AssessmentRounded from "@mui/icons-material/AssessmentRounded";
import BiotechRounded from "@mui/icons-material/BiotechRounded";
import FactCheckRounded from "@mui/icons-material/FactCheckRounded";
import HomeRounded from "@mui/icons-material/HomeRounded";
import MenuRounded from "@mui/icons-material/MenuRounded";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import AppBar from "@mui/material/AppBar";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import type { ReactNode } from "react";
import { useState } from "react";
import AuthStatus from "./AuthStatus";

const drawerWidth = 264;
const mobileNavigationId = "mobile-primary-navigation";

const plannedItems = [
  { label: "Runs", icon: <BiotechRounded aria-hidden="true" /> },
  { label: "Evidence", icon: <FactCheckRounded aria-hidden="true" /> },
  { label: "Benchmarks", icon: <AssessmentRounded aria-hidden="true" /> },
] as const;

function Navigation({ closeDrawer }: Readonly<{ closeDrawer?: () => void }>) {
  return (
    <>
      <Toolbar>
        <Typography variant="overline" color="text.secondary">
          Workspace
        </Typography>
      </Toolbar>
      <Divider />
      <List sx={{ px: 1.5, py: 2 }}>
        <ListItem disablePadding>
          <ListItemButton
            component="a"
            href="/"
            selected
            aria-current="page"
            onClick={closeDrawer}
            sx={{ minHeight: 48, borderRadius: 1.5 }}
          >
            <ListItemIcon sx={{ minWidth: 40 }}>
              <HomeRounded aria-hidden="true" />
            </ListItemIcon>
            <ListItemText primary="Overview" slotProps={{ primary: { sx: { fontWeight: 700 } } }} />
          </ListItemButton>
        </ListItem>
      </List>
      <Typography variant="overline" color="text.secondary" sx={{ px: 3 }}>
        Planned surfaces
      </Typography>
      <List aria-label="Planned navigation items" sx={{ px: 1.5, py: 1 }}>
        {plannedItems.map(({ label, icon }) => (
          <ListItem key={label} sx={{ minHeight: 48, px: 2, color: "text.secondary" }}>
            <ListItemIcon sx={{ minWidth: 40, color: "text.disabled" }}>{icon}</ListItemIcon>
            <ListItemText primary={label} />
            <Chip label="Planned" size="small" variant="outlined" />
          </ListItem>
        ))}
      </List>
    </>
  );
}

export default function AppShell({ children }: Readonly<{ children: ReactNode }>) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <Box sx={{ display: "flex", minHeight: "100vh", overflowX: "clip" }}>
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>

      <AppBar
        component="header"
        position="fixed"
        color="inherit"
        elevation={0}
        sx={{
          borderBottom: 1,
          borderColor: "divider",
          zIndex: (muiTheme) => muiTheme.zIndex.drawer + 1,
          width: { md: `calc(100% - ${drawerWidth}px)` },
          ml: { md: `${drawerWidth}px` },
        }}
      >
        <Toolbar sx={{ gap: 1.5 }}>
          <IconButton
            color="primary"
            aria-label={mobileOpen ? "Close primary navigation" : "Open primary navigation"}
            aria-controls={mobileNavigationId}
            aria-expanded={mobileOpen}
            onClick={() => setMobileOpen((open) => !open)}
            sx={{ display: { md: "none" } }}
          >
            <MenuRounded aria-hidden="true" />
          </IconButton>
          <FactCheckRounded color="primary" aria-hidden="true" />
          <Typography component="p" variant="h6" sx={{ fontWeight: 750, letterSpacing: "-0.02em" }}>
            TestGap Miner
          </Typography>
          <Box sx={{ flexGrow: 1 }} />
          <AuthStatus />
        </Toolbar>
      </AppBar>

      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={() => setMobileOpen(false)}
        ModalProps={{ keepMounted: true }}
        slotProps={{
          paper: {
            component: "nav",
            id: mobileNavigationId,
            "aria-label": "Primary navigation",
            sx: { width: drawerWidth },
          },
        }}
        sx={{ display: { xs: "block", md: "none" } }}
      >
        <Navigation closeDrawer={() => setMobileOpen(false)} />
      </Drawer>

      <Drawer
        variant="permanent"
        slotProps={{
          paper: {
            component: "nav",
            "aria-label": "Primary navigation",
            sx: { width: drawerWidth },
          },
        }}
        sx={{
          display: { xs: "none", md: "block" },
          width: drawerWidth,
          flexShrink: 0,
        }}
      >
        <Navigation />
      </Drawer>

      <Box
        component="main"
        id="main-content"
        tabIndex={-1}
        sx={{ flexGrow: 1, minWidth: 0, px: { xs: 2, sm: 3, lg: 5 } }}
      >
        <Toolbar />
        <Box sx={{ width: "100%", maxWidth: 1200, mx: "auto", py: { xs: 3, md: 5 } }}>
          {children}
        </Box>
      </Box>
    </Box>
  );
}
