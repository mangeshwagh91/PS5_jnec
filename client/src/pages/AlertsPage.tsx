import DashboardLayout from '@/components/dashboard/DashboardLayout';
import { severityColors, threatIcons } from '@/data/mockData';
import { useState } from 'react';
import { useSurveillanceData } from '@/hooks/useSurveillanceData';

type Filter = 'all' | 'active' | 'acknowledged' | 'resolved';

const AlertsPage = () => {
  const [filter, setFilter] = useState<Filter>('all');
  const { alerts } = useSurveillanceData();
  const filtered = filter === 'all' ? alerts : alerts.filter(a => a.status === filter);
  const filters: Filter[] = ['all', 'active', 'acknowledged', 'resolved'];

  return (
    <DashboardLayout title="ALERTS">
      <div className="p-6">
        <div className="flex items-center gap-2 mb-4">
          {filters.map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-md text-xs font-mono uppercase transition-colors ${
                filter === f ? 'bg-primary/20 text-primary border border-primary/30' : 'bg-secondary text-muted-foreground border border-border hover:bg-secondary/80'
              }`}
            >
              {f} ({f === 'all' ? alerts.length : alerts.filter(a => a.status === f).length})
            </button>
          ))}
        </div>
        <div className="bg-card border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs font-mono text-muted-foreground">
                <th className="px-4 py-3">ID</th>
                <th className="px-4 py-3">TYPE</th>
                <th className="px-4 py-3">SEVERITY</th>
                <th className="px-4 py-3">DESCRIPTION</th>
                <th className="px-4 py-3">LOCATION</th>
                <th className="px-4 py-3">CAMERA</th>
                <th className="px-4 py-3">TIME</th>
                <th className="px-4 py-3">STATUS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filtered.map(alert => (
                <tr key={alert.id} className="hover:bg-secondary/30 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{alert.id}</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center mr-2 px-1.5 py-0.5 rounded bg-slate-100 text-[10px] font-mono text-slate-600">
                      {threatIcons[alert.type]}
                    </span>
                    <span className="text-xs capitalize">{alert.type}</span>
                  </td>
                  <td className="px-4 py-3"><span className={`text-[10px] px-1.5 py-0.5 rounded border font-mono uppercase ${severityColors[alert.severity]}`}>{alert.severity}</span></td>
                  <td className="px-4 py-3 text-xs text-foreground max-w-[200px] truncate">{alert.description}</td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">{alert.location}</td>
                  <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{alert.camera}</td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">{alert.timestamp}</td>
                  <td className="px-4 py-3">
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-mono uppercase ${
                      alert.status === 'active' ? 'bg-destructive/20 text-destructive' :
                      alert.status === 'acknowledged' ? 'bg-warning/20 text-warning' :
                      'bg-success/20 text-success'
                    }`}>{alert.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default AlertsPage;
