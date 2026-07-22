import Link from "next/link";
import { Flame } from "lucide-react";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-1 flex-col items-center justify-center gap-8 bg-muted/30 p-6">
      <Link href="/" className="flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <Flame className="h-4.5 w-4.5" />
        </div>
        <span className="text-base font-semibold tracking-tight">Habit</span>
      </Link>
      {children}
    </div>
  );
}
