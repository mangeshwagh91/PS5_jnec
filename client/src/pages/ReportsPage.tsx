import DashboardLayout from '@/components/dashboard/DashboardLayout';
import { FileText, Download } from 'lucide-react';

const reports = [
  { id: 'RPT-001', title: 'Daily Threat Summary', date: 'Mar 25, 2026', type: 'Automated' },
  { id: 'RPT-002', title: 'Weekly Incident Analysis', date: 'Mar 23, 2026', type: 'Automated' },
  { id: 'RPT-003', title: 'Camera Uptime Report', date: 'Mar 22, 2026', type: 'System' },
  { id: 'RPT-004', title: 'Monthly Security Audit', date: 'Mar 01, 2026', type: 'Manual' },
  { id: 'RPT-005', title: 'Zone Coverage Analysis', date: 'Feb 28, 2026', type: 'Automated' },
];

const ReportsPage = () => (
  <DashboardLayout title="REPORTS">
    <div className="p-6 max-w-4xl">
      <div className="bg-card border border-border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs font-mono text-muted-foreground">
              <th className="px-4 py-3">ID</th>
              <th className="px-4 py-3">REPORT</th>
              <th className="px-4 py-3">DATE</th>
              <th className="px-4 py-3">TYPE</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {reports.map(r => (
              <tr key={r.id} className="hover:bg-secondary/30 transition-colors">
                <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{r.id}</td>
                <td className="px-4 py-3 flex items-center gap-2 text-foreground">
                  <FileText className="w-4 h-4 text-primary" />{r.title}
                </td>
                <td className="px-4 py-3 text-xs text-muted-foreground">{r.date}</td>
                <td className="px-4 py-3"><span className="text-[10px] px-2 py-0.5 rounded-full bg-secondary text-secondary-foreground font-mono">{r.type}</span></td>
                <td className="px-4 py-3"><Download className="w-4 h-4 text-muted-foreground hover:text-primary cursor-pointer transition-colors" /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  </DashboardLayout>
);

export default ReportsPage;
