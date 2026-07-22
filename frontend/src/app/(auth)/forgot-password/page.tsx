import { KeyRound } from "lucide-react";

import { ComingSoon } from "@/components/coming-soon";

export default function Page() {
  return (
    <ComingSoon
      title="Reset password"
      description="Password reset via email link is on the way."
      icon={KeyRound}
    />
  );
}
