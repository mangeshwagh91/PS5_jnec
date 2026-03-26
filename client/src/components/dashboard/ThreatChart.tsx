import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import type { TimelineEntry } from '@/lib/surveillanceApi';

const ThreatChart = ({ timeline }: { timeline: TimelineEntry[] }) => (
  <div className="bg-white border border-slate-200 rounded-xl flex flex-col shadow-sm">
    <div className="px-4 py-3 border-b border-slate-100">
      <h2 className="text-sm font-bold text-slate-800 tracking-tight uppercase">24h threat timeline</h2>
    </div>
    <div className="p-3 flex-1" style={{ minHeight: 200 }}>
      <ResponsiveContainer width="100%" height={180}>
        <AreaChart data={timeline}>
          <defs>
            <linearGradient id="weaponGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="hsl(0 75% 55%)" stopOpacity={0.35} />
              <stop offset="100%" stopColor="hsl(0 75% 55%)" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="garbageGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="hsl(38 94% 52%)" stopOpacity={0.35} />
              <stop offset="100%" stopColor="hsl(38 94% 52%)" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="hazardGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="hsl(221 83% 53%)" stopOpacity={0.35} />
              <stop offset="100%" stopColor="hsl(221 83% 53%)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="hour" tick={{ fill: 'hsl(215 16% 47%)', fontSize: 10 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: 'hsl(215 16% 47%)', fontSize: 10 }} axisLine={false} tickLine={false} width={20} />
          <Tooltip
            contentStyle={{
              background: 'hsl(0 0% 100%)',
              border: '1px solid hsl(214 32% 91%)',
              borderRadius: 6,
              fontSize: 11,
            }}
            labelStyle={{ color: 'hsl(222 47% 18%)' }}
          />
          <Area type="monotone" dataKey="weapon" stroke="hsl(0 75% 55%)" fill="url(#weaponGrad)" strokeWidth={1.75} />
          <Area type="monotone" dataKey="garbage" stroke="hsl(38 94% 52%)" fill="url(#garbageGrad)" strokeWidth={1.75} />
          <Area type="monotone" dataKey="hazard" stroke="hsl(221 83% 53%)" fill="url(#hazardGrad)" strokeWidth={1.75} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
    <div className="px-4 pb-3 flex items-center gap-4 text-[10px] font-semibold text-slate-500">
      <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500 inline-block" /> Weapon</span>
      <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500 inline-block" /> Garbage</span>
      <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500 inline-block" /> Hazard</span>
    </div>
  </div>
);

export default ThreatChart;
