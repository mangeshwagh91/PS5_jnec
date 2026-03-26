import DashboardLayout from '@/components/dashboard/DashboardLayout';
import StatsBar from '@/components/dashboard/StatsBar';
import ThreatMap from '@/components/dashboard/ThreatMap';
import AlertFeed from '@/components/dashboard/AlertFeed';
import CameraGrid from '@/components/dashboard/CameraGrid';
import ThreatChart from '@/components/dashboard/ThreatChart';
import { mockStats } from '@/data/mockData';
import { useSurveillanceData } from '@/hooks/useSurveillanceData';

const Index = () => {
  const { alerts, stats, cameras, timeline } = useSurveillanceData();

  return (
    <DashboardLayout title="COMMAND CENTER">
      <StatsBar stats={stats ?? mockStats} />
      <div className="flex-1 px-6 pb-6 grid grid-cols-12 gap-4">
        <div className="col-span-8 flex flex-col gap-4">
          <div className="flex-1"><ThreatMap alerts={alerts} /></div>
          <div className="grid grid-cols-2 gap-4">
            <ThreatChart timeline={timeline} />
            <CameraGrid cameras={cameras} />
          </div>
        </div>
        <div className="col-span-4"><AlertFeed alerts={alerts} /></div>
      </div>
    </DashboardLayout>
  );
};

export default Index;
