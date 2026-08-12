import CheckCircleRounded from "@mui/icons-material/CheckCircleRounded";
import ScheduleRounded from "@mui/icons-material/ScheduleRounded";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import ProtectedRegion from "@/components/ProtectedRegion";

const foundationStatus = [
  {
    title: "Application shell",
    status: "Implemented",
    detail: "Responsive navigation, theming, and the accessibility baseline are in place.",
    ready: true,
  },
  {
    title: "Authentication",
    status: "Implemented",
    detail: "GitHub sign-in, callback handling, and sign-out run through the Auth session runtime.",
    ready: true,
  },
  {
    title: "API connection",
    status: "Not connected",
    detail: "This foundation does not make requests or display backend data.",
    ready: false,
  },
  {
    title: "Runs and Evidence",
    status: "Planned",
    detail: "Workflow and execution-backed Evidence surfaces are not available yet.",
    ready: false,
  },
] as const;

export default function Home() {
  return (
    <Stack spacing={{ xs: 3, md: 4 }}>
      <Paper
        component="section"
        variant="outlined"
        sx={{
          overflow: "hidden",
          p: { xs: 3, sm: 5, md: 6 },
          background:
            "linear-gradient(135deg, var(--mui-palette-background-paper) 20%, var(--mui-palette-primary-light) 140%)",
        }}
      >
        <Stack spacing={2.5} sx={{ maxWidth: 760 }}>
          <Chip
            icon={<CheckCircleRounded aria-hidden="true" />}
            label="Frontend foundation implemented"
            color="success"
            variant="outlined"
            sx={{ alignSelf: "flex-start" }}
          />
          <Box>
            <Typography variant="overline" color="primary.main">
              Reviewable regression-test generation
            </Typography>
            <Typography id="page-title" variant="h1" sx={{ mt: 0.75 }}>
              TestGap Miner
            </Typography>
          </Box>
          <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 680 }}>
            The visual foundation is ready for the dashboard that will make generated Java
            regression tests and their execution evidence clear for human review.
          </Typography>
        </Stack>
      </Paper>

      <Box component="section" aria-labelledby="foundation-status-title">
        <Stack spacing={1} sx={{ mb: 2.5 }}>
          <Typography id="foundation-status-title" variant="h2">
            Foundation status
          </Typography>
          <Typography color="text.secondary">
            The shell is operational; workflow and Evidence features remain intentionally
            disconnected.
          </Typography>
        </Stack>

        <ProtectedRegion>
          <Box
            sx={{
              display: "grid",
              gap: 2,
              gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))" },
            }}
          >
            {foundationStatus.map(({ title, status, detail, ready }) => (
              <Paper key={title} variant="outlined" sx={{ p: 3 }}>
                <Stack direction="row" spacing={1.5} sx={{ alignItems: "flex-start" }}>
                  {ready ? (
                    <CheckCircleRounded color="success" aria-hidden="true" />
                  ) : (
                    <ScheduleRounded color="action" aria-hidden="true" />
                  )}
                  <Box>
                    <Typography variant="h3">{title}</Typography>
                    <Typography
                      variant="body2"
                      color={ready ? "success.dark" : "text.secondary"}
                      sx={{ fontWeight: 700, mt: 0.5 }}
                    >
                      {status}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      {detail}
                    </Typography>
                  </Box>
                </Stack>
              </Paper>
            ))}
          </Box>
        </ProtectedRegion>
      </Box>
    </Stack>
  );
}
