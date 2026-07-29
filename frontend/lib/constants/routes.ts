import {
  BarChart3,
  CalendarDays,
  Gauge,
  Inbox,
  Lightbulb,
  LineChart,
  Plug,
  ScrollText,
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
  { label: 'Analytics', href: '/analytics', icon: LineChart },
  { label: 'Calendar', href: '/calendar', icon: CalendarDays },
  { label: 'AI Studio', href: '/studio', icon: Sparkles },
  { label: 'Competitors', href: '/competitors', icon: Users },
  { label: 'Trends', href: '/trends', icon: TrendingUp },
  { label: 'Generator', href: '/generate', icon: Lightbulb },
  { label: 'Strategy', href: '/strategy', icon: ScrollText },
  { label: 'Integrations', href: '/integrations', icon: Plug },
  { label: 'Team', href: '/team', icon: Users },
  { label: 'Reports', href: '/reports', icon: BarChart3 },
  { label: 'Alerts', href: '/notifications', icon: Inbox },
  { label: 'Analysis', href: '/analysis', icon: BarChart3 },
  { label: 'Profile', href: '/profile', icon: Settings }
];

export const metricIcons = {
  business: BarChart3,
  trend: TrendingUp,
  competitors: Users,
  ideas: Lightbulb
};
