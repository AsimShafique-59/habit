import { LogIn } from "lucide-react";

import { ComingSoon } from "@/components/coming-soon";

export default function Page() {
  return (
    <ComingSoon
      title="Login"
      description="Email/password, Apple, and Google sign-in are on the way."
      icon={LogIn}
    />
  );
}
