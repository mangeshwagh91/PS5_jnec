import DashboardLayout from '@/components/dashboard/DashboardLayout';
import ThreatChart from '@/components/dashboard/ThreatChart';
import { useSurveillanceData } from '@/hooks/useSurveillanceData';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const AnalyticsPage = () => {
  const { alerts, stats, timeline } = useSurveillanceData();

  const typeData = ['weapon', 'garbage', 'hazard', 'intrusion', 'fire'].map(type => ({
    name: type,
    count: alerts.filter(a => a.type === type).length,
  }));

  const severityData = [
    { name: 'Critical', value: alerts.filter(a => a.severity === 'critical').length, color: 'hsl(0,72%,51%)' },
    { name: 'High', value: alerts.filter(a => a.severity === 'high').length, color: 'hsl(38,92%,50%)' },
    { name: 'Medium', value: alerts.filter(a => a.severity === 'medium').length, color: 'hsl(185,80%,45%)' },
    { name: 'Low', value: alerts.filter(a => a.severity === 'low').length, color: 'hsl(215,15%,50%)' },
  ];

  return (
    <DashboardLayout title="ANALYTICS">
    <div className="p-6 space-y-6">
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Total Alerts (24h)', value: stats?.totalAlerts ?? 0 },
          { label: 'Avg Response Time', value: stats?.avgResponseTime ?? '--' },
          {
            label: 'Resolution Rate',
            value: `${Math.round(((stats?.resolvedToday ?? 0) / Math.max(stats?.totalAlerts ?? 1, 1)) * 100)}%`,
          },
        ].map(s => (
          <div key={s.label} className="bg-card border border-border rounded-lg p-5">
            <p className="text-xs text-muted-foreground font-mono">{s.label}</p>
            <p className="text-3xl font-semibold font-mono text-foreground mt-1">{s.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <ThreatChart timeline={timeline} />

        <div className="bg-card border border-border rounded-lg p-4">
          <h2 className="text-sm font-semibold text-foreground tracking-wide mb-3">ALERTS BY TYPE</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={typeData}>
              <XAxis dataKey="name" tick={{ fill: 'hsl(215,15%,50%)', fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'hsl(215,15%,50%)', fontSize: 10 }} axisLine={false} tickLine={false} width={20} />
              <Tooltip contentStyle={{ background: 'hsl(220,18%,10%)', border: '1px solid hsl(220,15%,18%)', borderRadius: 6, fontSize: 11 }} />
              <Bar dataKey="count" fill="hsl(185,80%,45%)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-card border border-border rounded-lg p-4">
        <h2 className="text-sm font-semibold text-foreground tracking-wide mb-3">SEVERITY DISTRIBUTION</h2>
        <div className="flex items-center gap-8">
          <ResponsiveContainer width={200} height={200}>
            <PieChart>
              <Pie data={severityData} dataKey="value" cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={4}>
                {severityData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
              </Pie>
              <Tooltip contentStyle={{ background: 'hsl(220,18%,10%)', border: '1px solid hsl(220,15%,18%)', borderRadius: 6, fontSize: 11 }} />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-2">
            {severityData.map(s => (
              <div key={s.name} className="flex items-center gap-2 text-xs">
                <span className="w-3 h-3 rounded-full inline-block" style={{ background: s.color }} />
                <span className="text-foreground">{s.name}</span>
                <span className="text-muted-foreground font-mono">({s.value})</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  </DashboardLayout>
  );
};

export default AnalyticsPage;
