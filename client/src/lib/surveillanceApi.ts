import {
	alertTimeline,
	mockAlerts,
	mockCameras,
	mockStats,
	type CameraFeed,
	type DashboardStats,
	type ThreatAlert,
	type ThreatType,
} from '@/data/mockData';

type AlertStatus = 'active' | 'acknowledged' | 'resolved';
type Severity = 'critical' | 'high' | 'medium' | 'low';

type AlertsResponse = {
	total: number;
	items: BackendAlert[];
};

type BackendAlert = {
	id: string;
	camera_id: string;
	location: string;
	threat_type: ThreatType;
	severity: Severity;
	status: AlertStatus;
	coordinates: { x: number; y: number };
	created_at: string;
};

type BackendStats = {
	total_cameras: number;
	active_cameras: number;
	total_alerts: number;
	critical_alerts: number;
	resolved_today: number;
	avg_response_time: string;
};

type BackendCamera = {
	id: string;
	name: string;
	location: string;
	status: 'online' | 'offline' | 'alert';
	threat_count: number;
};

type BackendVideo = {
	filename: string;
	label: string;
	url: string;
};

type BackendVideosResponse = {
	items: BackendVideo[];
};

type BackendLiveCamerasResponse = {
	items: string[];
};

type BackendVideoUploadResponse = {
	item: BackendVideo;
};

export type VideoStream = {
	filename: string;
	label: string;
	url: string;
};

export type TimelineEntry = {
	hour: string;
	weapon: number;
	garbage: number;
	hazard: number;
	intrusion: number;
	fire: number;
};

const isProd = import.meta.env.PROD;
const defaultApi = isProd ? 'https://ps5-jnec.onrender.com/api/v1' : 'http://localhost:8001/api/v1';
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? defaultApi;
const API_ROLE = (import.meta.env.VITE_SURVEILLANCE_ROLE as string | undefined) ?? 'admin';

function toRelativeTime(isoDate: string): string {
	const created = Date.parse(isoDate);
	if (Number.isNaN(created)) {
		return 'just now';
	}

	const diffMs = Date.now() - created;
	const diffMinutes = Math.max(0, Math.floor(diffMs / 60000));

	if (diffMinutes < 1) {
		return 'just now';
	}

	if (diffMinutes < 60) {
		return `${diffMinutes} min ago`;
	}

	const diffHours = Math.floor(diffMinutes / 60);
	if (diffHours < 24) {
		return `${diffHours}h ago`;
	}

	const diffDays = Math.floor(diffHours / 24);
	return `${diffDays}d ago`;
}

function buildDescription(alert: BackendAlert): string {
	const label = alert.threat_type.charAt(0).toUpperCase() + alert.threat_type.slice(1);
	return `${label} activity detected`;
}

function mapAlert(alert: BackendAlert): ThreatAlert {
	return {
		id: alert.id,
		type: alert.threat_type,
		severity: alert.severity,
		location: alert.location,
		camera: alert.camera_id,
		timestamp: toRelativeTime(alert.created_at),
		description: buildDescription(alert),
		status: alert.status,
		coordinates: alert.coordinates,
	};
}

function mapStats(stats: BackendStats): DashboardStats {
	return {
		totalCameras: stats.total_cameras,
		activeCameras: stats.active_cameras,
		totalAlerts: stats.total_alerts,
		criticalAlerts: stats.critical_alerts,
		resolvedToday: stats.resolved_today,
		avgResponseTime: stats.avg_response_time,
	};
}

function mapCamera(camera: BackendCamera): CameraFeed {
	return {
		id: camera.id,
		name: camera.name,
		location: camera.location,
		status: camera.status,
		threatCount: camera.threat_count,
	};
}

async function requestJson<T>(path: string): Promise<T> {
	const response = await fetch(`${API_BASE_URL}${path}`, {
		headers: {
			'x-user-role': API_ROLE,
			'x-role': API_ROLE,
		},
	});

	if (!response.ok) {
		throw new Error(`Request failed for ${path}: ${response.status}`);
	}

	return (await response.json()) as T;
}

export async function fetchAlerts(): Promise<ThreatAlert[]> {
	try {
		const response = await requestJson<AlertsResponse>('/alerts?limit=100');
		return response.items.map(mapAlert);
	} catch {
		return mockAlerts;
	}
}

export async function fetchStats(): Promise<DashboardStats> {
	try {
		const response = await requestJson<BackendStats>('/stats');
		return mapStats(response);
	} catch {
		return mockStats;
	}
}

export async function fetchCameras(): Promise<CameraFeed[]> {
	try {
		const response = await requestJson<BackendCamera[]>('/cameras');
		return response.map(mapCamera);
	} catch {
		return mockCameras;
	}
}

export async function fetchTimeline(): Promise<TimelineEntry[]> {
	try {
		return await requestJson<TimelineEntry[]>('/analytics/timeline');
	} catch {
		return alertTimeline;
	}
}

export async function fetchVideos(): Promise<VideoStream[]> {
	try {
		const response = await requestJson<BackendVideosResponse>('/videos');
		return response.items;
	} catch {
		return [];
	}
}

export async function fetchLiveCameras(): Promise<string[]> {
	try {
		const response = await requestJson<BackendLiveCamerasResponse>('/live-cameras');
		return response.items;
	} catch {
		return [];
	}
}

export async function uploadVideo(file: File): Promise<VideoStream> {
	const formData = new FormData();
	formData.append('file', file);

	const response = await fetch(`${API_BASE_URL}/videos/upload`, {
		method: 'POST',
		headers: {
			'x-user-role': API_ROLE,
			'x-role': API_ROLE,
		},
		body: formData,
	});

	if (!response.ok) {
		let detail = `Upload failed: ${response.status}`;
		try {
			const payload = (await response.json()) as { detail?: string };
			if (payload?.detail) {
				detail = payload.detail;
			}
		} catch {
			// Keep default message.
		}
		throw new Error(detail);
	}

	const payload = (await response.json()) as BackendVideoUploadResponse;
	return payload.item;
}

export function getAlertsWebSocketUrl(): string {
	const explicit = import.meta.env.VITE_ALERTS_WS_URL as string | undefined;
	if (explicit) {
		return explicit;
	}

	const apiUrl = new URL(API_BASE_URL);
	apiUrl.protocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:';
	apiUrl.pathname = '/ws/alerts';
	apiUrl.search = '';
	apiUrl.hash = '';
	return apiUrl.toString();
}
