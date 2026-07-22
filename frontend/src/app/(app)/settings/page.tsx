import { Settings } from "lucide-react";

import { ComingSoon } from "@/components/coming-soon";

export default function Page() {
  return (
    <ComingSoon
      title="Settings"
      description="Profile, preferences, privacy, and account controls."
      icon={Settings}
    />
  );
}
