import { Bell } from "lucide-react";

import { ComingSoon } from "@/components/coming-soon";

export default function Page() {
  return (
    <ComingSoon
      title="Notifications"
      description="Reminders, streak alerts, and daily insight pings."
      icon={Bell}
    />
  );
}
