import type { DashboardStats, ThreatAlert, CameraFeed, ThreatType, Severity } from '@/data/mockData';

export interface TimelineEntry {
  hour: string;
  weapon: number;
  garbage: number;
  hazard: number;
  intrusion: number;
  fire: number;
}

interface ApiAlert {
  id: string;
  camera_id: string;
  location: string;
  threat_type: ThreatType;
  confidence: number;
  severity: Severity;
  status: ThreatAlert['status'];
  coordinates: { x: number; y: number };
  created_at: string;
}

interface ApiAlertsResponse {
  total: number;
  items: ApiAlert[];
}

interface ApiCamera {
  id: string;
  name: string;
  location: string;
  status: CameraFeed['status'];
  threat_count: number;
}

interface ApiStats {
  total_cameras: number;
  active_cameras: number;
  total_alerts: number;
  critical_alerts: number;
  resolved_today: number;
  avg_response_time: string;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1';

const THREAT_DESCRIPTION: Record<ThreatType, string> = {
  weapon: 'Weapon detected in surveillance zone',
  garbage: 'Illegal dumping activity detected',
  hazard: 'Safety hazard detected',
  intrusion: 'Unauthorized access attempt detected',
  fire: 'Fire and smoke signature detected',
};

function toRelativeTime(isoString: string): string {
  const ms = Date.now() - new Date(isoString).getTime();
  const minutes = Math.max(Math.floor(ms / 60000), 0);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hr ago`;
  const days = Math.floor(hours / 24);
  return `${days} day ago`;
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      'X-User-Role': 'admin',
    },
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function fetchAlerts(): Promise<ThreatAlert[]> {
  const data = await fetchJson<ApiAlertsResponse>('/alerts?limit=200');
  return data.items.map((item) => ({
    id: item.id,
    type: item.threat_type,
    severity: item.severity,
    location: item.location,
    camera: item.camera_id,
    timestamp: toRelativeTime(item.created_at),
    description: THREAT_DESCRIPTION[item.threat_type],
    status: item.status,
    coordinates: item.coordinates,
  }));
}

export async function fetchStats(): Promise<DashboardStats> {
  const data = await fetchJson<ApiStats>('/stats');
  return {
    totalCameras: data.total_cameras,
    activeCameras: data.active_cameras,
    totalAlerts: data.total_alerts,
    criticalAlerts: data.critical_alerts,
    resolvedToday: data.resolved_today,
    avgResponseTime: data.avg_response_time,
  };
}

export async function fetchCameras(): Promise<CameraFeed[]> {
  const data = await fetchJson<ApiCamera[]>('/cameras');
  return data.map((item) => ({
    id: item.id,
    name: item.name,
    location: item.location,
    status: item.status,
    threatCount: item.threat_count,
  }));
}

export async function fetchTimeline(): Promise<TimelineEntry[]> {
  return fetchJson<TimelineEntry[]>('/analytics/timeline');
}

export function getAlertsWebSocketUrl(): string {
  if (import.meta.env.VITE_WS_ALERTS_URL) {
    return import.meta.env.VITE_WS_ALERTS_URL;
  }

  const base = API_BASE.replace('/api/v1', '');
  return base.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws/alerts';
}
