import Link from "next/link";
import { ArrowRight, Flame } from "lucide-react";

import { navGroups } from "@/config/nav";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export default function Home() {
  return (
    <div className="flex flex-1 flex-col">
      <header className="mx-auto flex w-full max-w-5xl items-center justify-between px-6 py-6">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Flame className="h-4.5 w-4.5" />
          </div>
          <span className="text-base font-semibold tracking-tight">Habit</span>
        </div>
        <div className="flex items-center gap-2">
          <Link href="/login" className={buttonVariants({ variant: "ghost", size: "sm" })}>
            Log in
          </Link>
          <Link href="/signup" className={buttonVariants({ size: "sm" })}>
            Get started
          </Link>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-16 px-6 pb-24 pt-8">
        <section className="flex flex-col items-center gap-5 text-center">
          <Badge variant="secondary">Now building in public</Badge>
          <h1 className="max-w-2xl text-4xl font-semibold tracking-tight sm:text-5xl">
            Build habits that actually stick.
          </h1>
          <p className="max-w-xl text-balance text-muted-foreground sm:text-lg">
            Track daily habits, break bad ones, journal your mood, and get
            AI-powered coaching — all in one place.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            <Link href="/signup" className={buttonVariants({ size: "lg" })}>
              Create your account
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/dashboard"
              className={buttonVariants({ size: "lg", variant: "outline" })}
            >
              Preview the dashboard
            </Link>
          </div>
        </section>

        <section className="flex flex-col gap-8">
          {navGroups.map((group) => (
            <div key={group.label} className="flex flex-col gap-3">
              <h2 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                {group.label}
              </h2>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  return (
                    <Link key={item.href} href={item.href}>
                      <Card className="h-full transition-colors hover:border-primary/40 hover:bg-muted/40">
                        <CardContent className="flex items-start gap-3 py-1">
                          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted">
                            <Icon className="h-4.5 w-4.5 text-muted-foreground" />
                          </div>
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <p className="text-sm font-medium">{item.title}</p>
                              {!item.ready && (
                                <Badge variant="outline" className="text-[10px]">
                                  Soon
                                </Badge>
                              )}
                            </div>
                            <p className="text-xs text-muted-foreground">
                              {item.description}
                            </p>
                          </div>
                        </CardContent>
                      </Card>
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </section>
      </main>
    </div>
  );
}
