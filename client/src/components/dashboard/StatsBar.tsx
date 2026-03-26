import { Camera, AlertTriangle, CheckCircle, Timer } from 'lucide-react';
import type { DashboardStats } from '@/data/mockData';

const StatsBar = ({ stats }: { stats: DashboardStats }) => {
  const items = [
    { label: 'Active Cameras', value: `${stats.activeCameras}/${stats.totalCameras}`, icon: Camera, color: 'text-primary' },
    { label: 'Active Alerts', value: stats.totalAlerts, icon: AlertTriangle, color: 'text-warning' },
    { label: 'Critical', value: stats.criticalAlerts, icon: AlertTriangle, color: 'text-destructive' },
    { label: 'Resolved Today', value: stats.resolvedToday, icon: CheckCircle, color: 'text-success' },
    { label: 'Avg Response', value: stats.avgResponseTime, icon: Timer, color: 'text-primary' },
  ];

  return (
  <div className="grid grid-cols-5 gap-6 mb-8 mt-2">
    {items.map((stat) => (
      <div key={stat.label} className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm flex flex-col items-start gap-4 hover:shadow-md transition-shadow duration-300">
        <div className={`p-3 rounded-2xl bg-slate-50 border border-slate-100 ${stat.color}`}>
          <stat.icon className="w-6 h-6" />
        </div>
        <div>
          <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1">{stat.label}</p>
          <p className="text-2xl font-extrabold text-slate-900 tracking-tight">{stat.value}</p>
        </div>
      </div>
    ))}
  </div>
  );
};

export default StatsBar;
