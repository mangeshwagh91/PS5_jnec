export type ThreatType = 'weapon' | 'garbage' | 'hazard' | 'intrusion' | 'fire';
export type Severity = 'critical' | 'high' | 'medium' | 'low';

export interface ThreatAlert {
  id: string;
  type: ThreatType;
  severity: Severity;
  location: string;
  camera: string;
  timestamp: string;
  description: string;
  status: 'active' | 'acknowledged' | 'resolved';
  coordinates: { x: number; y: number };
}

export interface CameraFeed {
  id: string;
  name: string;
  location: string;
  status: 'online' | 'offline' | 'alert';
  threatCount: number;
}

export interface DashboardStats {
  totalCameras: number;
  activeCameras: number;
  totalAlerts: number;
  criticalAlerts: number;
  resolvedToday: number;
  avgResponseTime: string;
}

export const mockAlerts: ThreatAlert[] = [
  { id: 'ALT-001', type: 'weapon', severity: 'critical', location: 'Gate B - North Entrance', camera: 'CAM-012', timestamp: '2 min ago', description: 'Firearm detected in surveillance zone', status: 'active', coordinates: { x: 35, y: 25 } },
  { id: 'ALT-002', type: 'garbage', severity: 'medium', location: 'Parking Lot C', camera: 'CAM-045', timestamp: '8 min ago', description: 'Illegal dumping activity detected', status: 'active', coordinates: { x: 65, y: 55 } },
  { id: 'ALT-003', type: 'hazard', severity: 'high', location: 'Chemical Storage Unit 3', camera: 'CAM-078', timestamp: '12 min ago', description: 'Chemical spill detected near storage', status: 'acknowledged', coordinates: { x: 80, y: 35 } },
  { id: 'ALT-004', type: 'intrusion', severity: 'high', location: 'Perimeter Fence - East', camera: 'CAM-023', timestamp: '15 min ago', description: 'Unauthorized access attempt detected', status: 'active', coordinates: { x: 90, y: 70 } },
  { id: 'ALT-005', type: 'fire', severity: 'critical', location: 'Warehouse District B', camera: 'CAM-091', timestamp: '18 min ago', description: 'Smoke and heat signature detected', status: 'active', coordinates: { x: 45, y: 75 } },
  { id: 'ALT-006', type: 'garbage', severity: 'low', location: 'Residential Block 7', camera: 'CAM-034', timestamp: '25 min ago', description: 'Debris accumulation detected', status: 'resolved', coordinates: { x: 20, y: 60 } },
  { id: 'ALT-007', type: 'weapon', severity: 'high', location: 'Transit Hub - Platform 2', camera: 'CAM-056', timestamp: '32 min ago', description: 'Knife detected in crowd', status: 'acknowledged', coordinates: { x: 55, y: 40 } },
  { id: 'ALT-008', type: 'hazard', severity: 'medium', location: 'Construction Zone Alpha', camera: 'CAM-067', timestamp: '45 min ago', description: 'Structural instability warning', status: 'resolved', coordinates: { x: 30, y: 85 } },
];

export const mockCameras: CameraFeed[] = [
  { id: 'CAM-012', name: 'Gate B North', location: 'North Entrance', status: 'alert', threatCount: 1 },
  { id: 'CAM-023', name: 'Perimeter East', location: 'East Fence', status: 'alert', threatCount: 1 },
  { id: 'CAM-034', name: 'Residential 7', location: 'Block 7', status: 'online', threatCount: 0 },
  { id: 'CAM-045', name: 'Parking C', location: 'Lot C', status: 'alert', threatCount: 1 },
  { id: 'CAM-056', name: 'Transit Hub', location: 'Platform 2', status: 'online', threatCount: 0 },
  { id: 'CAM-067', name: 'Construction A', location: 'Zone Alpha', status: 'online', threatCount: 0 },
  { id: 'CAM-078', name: 'Chemical Storage', location: 'Unit 3', status: 'alert', threatCount: 1 },
  { id: 'CAM-091', name: 'Warehouse B', location: 'District B', status: 'alert', threatCount: 1 },
  { id: 'CAM-102', name: 'Main Gate', location: 'South Entry', status: 'online', threatCount: 0 },
  { id: 'CAM-113', name: 'Rooftop 5', location: 'Building 5', status: 'offline', threatCount: 0 },
];

export const mockStats: DashboardStats = {
  totalCameras: 128,
  activeCameras: 121,
  totalAlerts: 47,
  criticalAlerts: 5,
  resolvedToday: 34,
  avgResponseTime: '2m 34s',
};

export const threatColors: Record<ThreatType, string> = {
  weapon: 'text-destructive',
  garbage: 'text-warning',
  hazard: 'text-warning',
  intrusion: 'text-primary',
  fire: 'text-destructive',
};

export const severityColors: Record<Severity, string> = {
  critical: 'bg-destructive/20 text-destructive border-destructive/30',
  high: 'bg-warning/20 text-warning border-warning/30',
  medium: 'bg-primary/20 text-primary border-primary/30',
  low: 'bg-muted text-muted-foreground border-border',
};

export const threatIcons: Record<ThreatType, string> = {
  weapon: 'WPN',
  garbage: 'GBG',
  hazard: 'HZD',
  intrusion: 'INT',
  fire: 'FIR',
};

export const alertTimeline = [
  { hour: '00:00', weapon: 0, garbage: 1, hazard: 0, intrusion: 1, fire: 0 },
  { hour: '04:00', weapon: 0, garbage: 2, hazard: 1, intrusion: 0, fire: 0 },
  { hour: '08:00', weapon: 1, garbage: 3, hazard: 0, intrusion: 2, fire: 0 },
  { hour: '12:00', weapon: 2, garbage: 5, hazard: 2, intrusion: 1, fire: 1 },
  { hour: '16:00', weapon: 1, garbage: 4, hazard: 1, intrusion: 3, fire: 0 },
  { hour: '20:00', weapon: 3, garbage: 2, hazard: 1, intrusion: 2, fire: 1 },
  { hour: 'Now', weapon: 1, garbage: 1, hazard: 1, intrusion: 1, fire: 1 },
];
