import { threatIcons } from '@/data/mockData';
import type { ThreatAlert } from '@/data/mockData';
import { Badge } from '@/components/ui/badge';

const AlertFeed = ({ alerts }: { alerts: ThreatAlert[] }) => (
  <div className="bg-white border border-slate-200 rounded-2xl flex flex-col h-full shadow-sm overflow-hidden">
    <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
      <h2 className="text-sm font-bold text-slate-800 tracking-tight uppercase">Live alerts</h2>
      <Badge variant="secondary" className="bg-red-100 text-red-700 hover:bg-red-100 border-none px-2.5 py-0.5 rounded-full font-bold text-[10px]">
        {alerts.filter(a => a.status === 'active').length} Active
      </Badge>
    </div>
    <div className="flex-1 overflow-y-auto">
      {alerts.map((alert) => (
        <div
          key={alert.id}
          className={`px-5 py-4 hover:bg-slate-50 transition-all duration-200 cursor-pointer border-b border-slate-50 last:border-0 ${
            alert.status === 'resolved' ? 'opacity-40 grayscale' : ''
          }`}
        >
          <div className="flex items-start gap-4">
            <div className={`p-2 rounded-xl bg-slate-100 shadow-inner flex items-center justify-center`}>
              <span className="text-[10px] font-bold tracking-wider text-slate-600">{threatIcons[alert.type]}</span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between mb-1.5">
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                  alert.severity === 'critical' ? 'bg-red-100 text-red-700' :
                  alert.severity === 'high' ? 'bg-orange-100 text-orange-700' :
                  'bg-blue-100 text-blue-700'
                }`}>
                  {alert.severity}
                </span>
                <span className="text-[10px] font-bold text-slate-400 tabular-nums">{alert.timestamp}</span>
              </div>
              <p className="text-sm font-semibold text-slate-800 leading-tight mb-1">{alert.description}</p>
              <div className="flex items-center gap-2 text-[11px] font-medium text-slate-500">
                <span className="truncate">{alert.camera}</span>
                <span className="text-slate-300">•</span>
                <span className="truncate">{alert.location}</span>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  </div>
);

export default AlertFeed;
