import {
  LayoutDashboard,
  Camera,
  AlertTriangle,
  Map,
  BarChart3,
  Settings,
  Bell,
  Shield,
  FileText,
} from 'lucide-react';
import { NavLink } from '@/components/NavLink';
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarFooter,
  useSidebar,
} from '@/components/ui/sidebar';

const mainItems = [
  { title: 'Dashboard', url: '/', icon: LayoutDashboard },
  { title: 'Threat Map', url: '/threat-map', icon: Map },
  { title: 'Alerts', url: '/alerts', icon: AlertTriangle },
  { title: 'Cameras', url: '/cameras', icon: Camera },
  { title: 'Analytics', url: '/analytics', icon: BarChart3 },
];

const systemItems = [
  { title: 'Notifications', url: '/notifications', icon: Bell },
  { title: 'Reports', url: '/reports', icon: FileText },
  { title: 'Settings', url: '/settings', icon: Settings },
];

export function AppSidebar() {
  const { state } = useSidebar();
  const collapsed = state === 'collapsed';

  return (
    <Sidebar collapsible="icon" className="border-r border-slate-200">
      <div className="px-5 py-6 flex items-center gap-3 border-b border-slate-100">
        <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center shrink-0 shadow-lg shadow-blue-200">
          <Shield className="w-5 h-5 text-white" />
        </div>
        {!collapsed && (
          <span className="text-base font-bold text-slate-900 tracking-tight">Sentinel AI</span>
        )}
      </div>

      <SidebarContent className="p-2">
        <SidebarGroup>
          <SidebarGroupLabel className="px-4 py-2 text-[10px] uppercase font-bold tracking-widest text-slate-400">
            Operations
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {mainItems.map((item) => (
                <SidebarMenuItem key={item.title} className="mb-1">
                  <SidebarMenuButton asChild>
                    <NavLink
                      to={item.url}
                      end
                      className="px-4 py-2.5 rounded-lg hover:bg-slate-100 text-slate-600 transition-all duration-200"
                      activeClassName="bg-blue-50 text-blue-700 font-semibold shadow-sm ring-1 ring-blue-100"
                    >
                      <item.icon className="mr-3 h-4 w-4" />
                      {!collapsed && <span className="text-sm">{item.title}</span>}
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup className="mt-4">
          <SidebarGroupLabel className="px-4 py-2 text-[10px] uppercase font-bold tracking-widest text-slate-400">
            System
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {systemItems.map((item) => (
                <SidebarMenuItem key={item.title} className="mb-1">
                  <SidebarMenuButton asChild>
                    <NavLink
                      to={item.url}
                      end
                      className="px-4 py-2.5 rounded-lg hover:bg-slate-100 text-slate-600 transition-all duration-200"
                      activeClassName="bg-blue-50 text-blue-700 font-semibold shadow-sm ring-1 ring-blue-100"
                    >
                      <item.icon className="mr-3 h-4 w-4" />
                      {!collapsed && <span className="text-sm">{item.title}</span>}
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="border-t border-slate-200 p-3">
        {!collapsed && (
          <div className="text-[10px] font-mono text-slate-400 text-center tracking-wider uppercase">
            v1.0.0 • compliant
          </div>
        )}
      </SidebarFooter>
    </Sidebar>
  );
}
