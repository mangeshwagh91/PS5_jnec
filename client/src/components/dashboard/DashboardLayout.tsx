import { SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar';
import { AppSidebar } from '@/components/dashboard/AppSidebar';
import { Radio, Clock } from 'lucide-react';
import { useEffect, useState } from 'react';

const LiveClock = () => {
  const [time, setTime] = useState(new Date());
  useEffect(() => {
    const i = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(i);
  }, []);
  return (
    <div className="flex items-center gap-2 text-muted-foreground">
      <Clock className="w-3.5 h-3.5" />
      <span className="text-xs font-mono">
        {time.toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' })}{' '}
        {time.toLocaleTimeString('en-US', { hour12: false })}
      </span>
    </div>
  );
};

const DashboardLayout = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <SidebarProvider>
    <div className="min-h-screen flex w-full bg-slate-50/50">
      <AppSidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <header className="border-b border-border bg-white/80 backdrop-blur-md px-6 py-4 flex items-center justify-between sticky top-0 z-50">
          <div className="flex items-center gap-4">
            <SidebarTrigger className="text-slate-500 hover:text-slate-900 transition-colors" />
            <div className="h-6 w-px bg-slate-200" />
            <h1 className="text-lg font-bold tracking-tight text-slate-900">{title}</h1>
          </div>
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2 px-3 py-1 bg-emerald-50 rounded-full border border-emerald-100">
              <Radio className="w-3 h-3 text-emerald-500" />
              <span className="text-[10px] font-bold tracking-wider text-emerald-600 uppercase">System Online</span>
            </div>
            <LiveClock />
          </div>
        </header>
        <div className="flex-1 overflow-auto p-6">{children}</div>
      </div>
    </div>
  </SidebarProvider>
);

export default DashboardLayout;
