import { CreditCard } from "lucide-react";

import { ComingSoon } from "@/components/coming-soon";

export default function Page() {
  return (
    <ComingSoon
      title="Subscription"
      description="Manage your plan, billing, and premium features."
      icon={CreditCard}
    />
  );
}
