import type { LucideIcon } from "lucide-react";
import {
  BarChart3,
  Bell,
  BookOpen,
  Bot,
  Cable,
  CreditCard,
  Headphones,
  LayoutDashboard,
  ListChecks,
  Settings,
  Sparkles,
} from "lucide-react";

export type NavItem = {
  title: string;
  href: string;
  icon: LucideIcon;
  description: string;
  /** Pages flip this to true as they get real implementations. */
  ready: boolean;
};

export type NavGroup = {
  label: string;
  items: NavItem[];
};

export const navGroups: NavGroup[] = [
  {
    label: "Overview",
    items: [
      {
        title: "Dashboard",
        href: "/dashboard",
        icon: LayoutDashboard,
        description: "Your daily snapshot — streaks, momentum, and today's habits.",
        ready: true,
      },
    ],
  },
  {
    label: "Habits",
    items: [
      {
        title: "Habits",
        href: "/habits",
        icon: ListChecks,
        description: "Create, track, and complete your daily and weekly habits.",
        ready: true,
      },
      {
        title: "Analytics",
        href: "/analytics",
        icon: BarChart3,
        description: "Streaks, heatmaps, correlations, and progress reports.",
        ready: true,
      },
      {
        title: "AI Coach",
        href: "/ai-coach",
        icon: Bot,
        description: "AI-generated habit suggestions and coaching reviews.",
        ready: true,
      },
    ],
  },
  {
    label: "Growth",
    items: [
      {
        title: "Insights",
        href: "/insights",
        icon: Headphones,
        description: "Guided audio sessions to build focus and motivation.",
        ready: true,
      },
      {
        title: "Motivation",
        href: "/motivation",
        icon: Sparkles,
        description: "Structured quit/change programs with daily check-ins.",
        ready: true,
      },
      {
        title: "Reflection",
        href: "/reflection",
        icon: BookOpen,
        description: "Journal entries, mood tracking, and daily prompts.",
        ready: true,
      },
    ],
  },
  {
    label: "Account",
    items: [
      {
        title: "Notifications",
        href: "/notifications",
        icon: Bell,
        description: "Reminders, streak alerts, and daily insight pings.",
        ready: true,
      },
      {
        title: "Subscription",
        href: "/subscriptions",
        icon: CreditCard,
        description: "Manage your plan, billing, and premium features.",
        ready: true,
      },
      {
        title: "Integrations",
        href: "/integrations",
        icon: Cable,
        description: "Connect Apple Health, Google Fit, and calendar sync.",
        ready: true,
      },
      {
        title: "Settings",
        href: "/settings",
        icon: Settings,
        description: "Profile, preferences, privacy, and account controls.",
        ready: true,
      },
    ],
  },
];

export const navItems: NavItem[] = navGroups.flatMap((g) => g.items);
