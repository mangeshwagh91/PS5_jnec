import cityMapBg from '@/assets/city-map-bg.jpg';
import type { ThreatAlert } from '@/data/mockData';

const severityPulse: Record<string, string> = {
  critical: 'bg-red-500',
  high: 'bg-amber-500',
  medium: 'bg-blue-500',
  low: 'bg-slate-400',
};

const ThreatMap = ({ alerts }: { alerts: ThreatAlert[] }) => (
  <div className="relative rounded-2xl overflow-hidden border border-slate-200 bg-white h-full min-h-[350px] shadow-sm">
    <div className="absolute top-4 left-4 z-10 bg-white/90 backdrop-blur-sm border border-slate-200 rounded-lg px-3 py-1.5">
      <span className="text-[11px] font-bold text-slate-600 tracking-wide uppercase">Live Threat Map</span>
    </div>
    <img
      src={cityMapBg}
      alt="Surveillance area map"
      className="w-full h-full object-cover opacity-90 brightness-110 contrast-110"
      width={1280}
      height={720}
    />
    <div className="absolute inset-0 bg-white/10 pointer-events-none" />
    {alerts.filter(a => a.status !== 'resolved').map((alert) => (
      <div
        key={alert.id}
        className="absolute group cursor-pointer"
        style={{ left: `${alert.coordinates.x}%`, top: `${alert.coordinates.y}%` }}
      >
        <div className={`w-3.5 h-3.5 rounded-full ${severityPulse[alert.severity]} ring-2 ring-white shadow-md`} />
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 hidden group-hover:block bg-white border border-slate-200 rounded-md px-2.5 py-1.5 whitespace-nowrap z-20 shadow-lg">
          <p className="text-[10px] font-semibold text-slate-800">{alert.id} • {alert.camera}</p>
          <p className="text-[10px] text-slate-500">{alert.location}</p>
        </div>
      </div>
    ))}
  </div>
);

export default ThreatMap;
