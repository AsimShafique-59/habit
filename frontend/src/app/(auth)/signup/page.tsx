import { UserPlus } from "lucide-react";

import { ComingSoon } from "@/components/coming-soon";

export default function Page() {
  return (
    <ComingSoon
      title="Sign up"
      description="Create your account to start building better habits."
      icon={UserPlus}
    />
  );
}
