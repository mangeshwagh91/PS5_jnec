import DashboardLayout from '@/components/dashboard/DashboardLayout';
import StatsBar from '@/components/dashboard/StatsBar';
import ThreatMap from '@/components/dashboard/ThreatMap';
import AlertFeed from '@/components/dashboard/AlertFeed';
import CameraGrid from '@/components/dashboard/CameraGrid';
import ThreatChart from '@/components/dashboard/ThreatChart';
import { useSurveillanceData } from '@/hooks/useSurveillanceData';

const FALLBACK_STATS = {
  totalCameras: 0,
  activeCameras: 0,
  totalAlerts: 0,
  criticalAlerts: 0,
  resolvedToday: 0,
  avgResponseTime: '--',
};

const Index = () => {
  const { alerts, stats, cameras, timeline } = useSurveillanceData();

  return (
    <DashboardLayout title="Operational Overview">
    <div className="max-w-[1600px] mx-auto w-full">
      <StatsBar stats={stats ?? FALLBACK_STATS} />
      <div className="grid grid-cols-12 gap-8 items-stretch">
        <div className="col-span-12 lg:col-span-8 flex flex-col gap-8">
          <div className="h-[500px] shadow-sm rounded-2xl overflow-hidden border border-slate-200">
            <ThreatMap alerts={alerts} />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
              <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-6">Threat level trends</h3>
              <ThreatChart timeline={timeline} />
            </div>
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
               <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-6">Connected devices</h3>
              <CameraGrid cameras={cameras} />
            </div>
          </div>
        </div>
        <div className="col-span-12 lg:col-span-4 h-full">
           <AlertFeed alerts={alerts} />
        </div>
      </div>
    </div>
  </DashboardLayout>
  );
};

export default Index;
