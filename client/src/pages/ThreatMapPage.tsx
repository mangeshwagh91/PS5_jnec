import DashboardLayout from '@/components/dashboard/DashboardLayout';
import ThreatMap from '@/components/dashboard/ThreatMap';
import { severityColors, threatIcons } from '@/data/mockData';
import { useSurveillanceData } from '@/hooks/useSurveillanceData';
import { useNavigate } from 'react-router-dom';

const ThreatMapPage = () => {
  const navigate = useNavigate();
  const { alerts } = useSurveillanceData();
  const activeAlerts = alerts.filter((a) => a.status !== 'resolved');

  return (
    <DashboardLayout title="THREAT MAP">
    <div className="p-6 grid grid-cols-12 gap-4 h-full">
      <div className="col-span-9 h-[calc(100vh-120px)]">
        <ThreatMap alerts={alerts} />
      </div>
      <div className="col-span-3 bg-card border border-border rounded-lg p-4 overflow-y-auto max-h-[calc(100vh-120px)]">
        <h2 className="text-xs font-mono text-muted-foreground tracking-widest mb-3">ACTIVE ZONES</h2>
        <div className="space-y-2">
          {activeAlerts.map(alert => (
            <div key={alert.id} className="border border-border rounded-md p-3 hover:bg-secondary/50 transition-colors">
              <div className="flex items-center gap-2 mb-1">
                <span className="inline-flex items-center justify-center px-1.5 py-0.5 rounded bg-slate-100 text-[10px] font-mono text-slate-600">
                  {threatIcons[alert.type]}
                </span>
                <span className="font-mono text-xs text-muted-foreground">{alert.id}</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded border font-mono uppercase ml-auto ${severityColors[alert.severity]}`}>
                  {alert.severity}
                </span>
              </div>
              <p className="text-xs text-foreground">{alert.location}</p>
              <p className="text-[10px] text-muted-foreground mt-1">{alert.camera} • {alert.timestamp}</p>
              <button
                type="button"
                className="mt-2 text-[10px] font-mono uppercase text-primary hover:underline"
                onClick={() => navigate(`/cameras?focus=${encodeURIComponent(alert.camera)}`)}
              >
                Open Camera Feed
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  </DashboardLayout>
  );
};

export default ThreatMapPage;
