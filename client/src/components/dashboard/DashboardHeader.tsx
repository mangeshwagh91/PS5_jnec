import { Shield, Radio, Clock } from 'lucide-react';
import { useEffect, useState } from 'react';

const DashboardHeader = () => {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="border-b border-border bg-card/80 backdrop-blur-sm px-6 py-3 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-primary/10 border border-primary/30 flex items-center justify-center glow-primary">
          <Shield className="w-5 h-5 text-primary" />
        </div>
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-foreground">
            PS5 SENTINEL
          </h1>
          <p className="text-xs text-muted-foreground font-mono tracking-wider">
            MULTI-THREAT SURVEILLANCE
          </p>
        </div>
      </div>

      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <Radio className="w-3 h-3 text-success threat-blink" />
          <span className="text-xs font-mono text-success">SYSTEM ONLINE</span>
        </div>
        <div className="flex items-center gap-2 text-muted-foreground">
          <Clock className="w-3.5 h-3.5" />
          <span className="text-xs font-mono">
            {time.toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' })}
            {' '}
            {time.toLocaleTimeString('en-US', { hour12: false })}
          </span>
        </div>
      </div>
    </header>
  );
};

export default DashboardHeader;
