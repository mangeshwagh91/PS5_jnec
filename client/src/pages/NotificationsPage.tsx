import DashboardLayout from '@/components/dashboard/DashboardLayout';
import { Check } from 'lucide-react';
import { threatIcons, severityColors } from '@/data/mockData';
import { useSurveillanceData } from '@/hooks/useSurveillanceData';

const NotificationsPage = () => {
  const { alerts } = useSurveillanceData();

  return (
    <DashboardLayout title="NOTIFICATIONS">
    <div className="p-6 max-w-3xl">
      <div className="space-y-2">
        {alerts.map((alert, i) => (
          <div
            key={alert.id}
            className={`flex items-start gap-3 p-4 rounded-lg border transition-colors cursor-pointer hover:bg-secondary/50 ${
              i < 3 ? 'border-primary/20 bg-primary/5' : 'border-border bg-card'
            }`}
          >
            <span className="inline-flex items-center justify-center mt-0.5 px-1.5 py-0.5 rounded bg-slate-100 text-[10px] font-mono text-slate-600">
              {threatIcons[alert.type]}
            </span>
            <div className="flex-1">
              <p className="text-sm text-foreground">{alert.description}</p>
              <p className="text-xs text-muted-foreground mt-1">{alert.location} • {alert.camera} • {alert.timestamp}</p>
            </div>
            <span className={`text-[10px] px-1.5 py-0.5 rounded border font-mono uppercase ${severityColors[alert.severity]}`}>
              {alert.severity}
            </span>
            {i >= 3 && <Check className="w-4 h-4 text-muted-foreground" />}
          </div>
        ))}
      </div>
    </div>
  </DashboardLayout>
  );
};

export default NotificationsPage;
