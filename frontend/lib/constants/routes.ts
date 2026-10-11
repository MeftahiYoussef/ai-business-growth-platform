import {
  BarChart3,
  CalendarDays,
  Gauge,
  Inbox,
  Lightbulb,
  Settings,
  Sparkles,
  TrendingUp,
  Users
} from 'lucide-react';

export const publicRoutes = ['/login', '/register', '/forgot-password'];
export const protectedRoutes = [
  '/onboarding',
  '/dashboard',
  '/competitors',
  '/trends',
  '/generate',
  '/studio',
  '/calendar',
  '/analytics',
  '/integrations',
  '/team',
  '/reports',
  '/notifications',
  '/strategy',
  '/analysis',
  '/profile',
  '/settings'
];

export const navItems = [
  { label: 'Dashboard', href: '/dashboard', icon: Gauge },
  { label: 'Calendar', href: '/calendar', icon: CalendarDays },
  { label: 'AI Studio', href: '/studio', icon: Sparkles },
  { label: 'Reports', href: '/reports', icon: BarChart3 },
  { label: 'Alerts', href: '/notifications', icon: Inbox },
  { label: 'Profile', href: '/profile', icon: Settings }
];

export const metricIcons = {
  business: BarChart3,
  trend: TrendingUp,
  competitors: Users,
  ideas: Lightbulb
};
