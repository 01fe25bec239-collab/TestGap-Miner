import type { Metadata } from "next";
import AuthCallbackView from "./AuthCallbackView";

export const metadata: Metadata = {
  title: "Completing sign-in — TestGap Miner",
  robots: { index: false, follow: false },
};

export default function AuthCallbackPage() {
  return <AuthCallbackView />;
}
