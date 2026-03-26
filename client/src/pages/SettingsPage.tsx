import DashboardLayout from '@/components/dashboard/DashboardLayout';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';

const sections = [
  {
    title: 'ALERT CONFIGURATION',
    items: [
      { label: 'Weapon Detection Alerts', desc: 'Receive alerts for firearm and weapon detections', default: true },
      { label: 'Garbage Dumping Alerts', desc: 'Monitor illegal dumping activity', default: true },
      { label: 'Hazard Alerts', desc: 'Chemical spills, structural issues, fire', default: true },
      { label: 'Intrusion Detection', desc: 'Perimeter breach and unauthorized access', default: true },
    ],
  },
  {
    title: 'NOTIFICATIONS',
    items: [
      { label: 'Push Notifications', desc: 'Browser push for critical alerts', default: true },
      { label: 'Sound Alerts', desc: 'Audible alarm on critical threats', default: false },
      { label: 'Email Digest', desc: 'Daily summary of all incidents', default: true },
    ],
  },
  {
    title: 'SYSTEM',
    items: [
      { label: 'Auto-acknowledge Low Severity', desc: 'Automatically acknowledge low-severity alerts after 30 min', default: false },
      { label: 'Camera Health Monitoring', desc: 'Alert when cameras go offline', default: true },
    ],
  },
];

const SettingsPage = () => (
  <DashboardLayout title="SETTINGS">
    <div className="p-6 max-w-2xl space-y-8">
      {sections.map(section => (
        <div key={section.title}>
          <h2 className="text-xs font-mono text-muted-foreground tracking-widest mb-4">{section.title}</h2>
          <div className="bg-card border border-border rounded-lg divide-y divide-border">
            {section.items.map(item => (
              <div key={item.label} className="flex items-center justify-between p-4">
                <div>
                  <p className="text-sm text-foreground">{item.label}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">{item.desc}</p>
                </div>
                <Switch defaultChecked={item.default} />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  </DashboardLayout>
);

export default SettingsPage;
