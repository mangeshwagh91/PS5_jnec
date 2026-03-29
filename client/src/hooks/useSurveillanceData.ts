import { useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  fetchAlerts,
  fetchCameras,
  fetchLiveCameras,
  fetchStats,
  fetchTimeline,
  fetchVideos,
  getAlertsWebSocketUrl,
} from '@/lib/surveillanceApi';

type AlertSocketMessage = {
  type?: string;
};

export function useSurveillanceData() {
  const queryClient = useQueryClient();

  const alertsQuery = useQuery({
    queryKey: ['surveillance', 'alerts'],
    queryFn: fetchAlerts,
    refetchInterval: 15000,
  });

  const statsQuery = useQuery({
    queryKey: ['surveillance', 'stats'],
    queryFn: fetchStats,
    refetchInterval: 20000,
  });

  const camerasQuery = useQuery({
    queryKey: ['surveillance', 'cameras'],
    queryFn: fetchCameras,
    refetchInterval: 20000,
  });

  const timelineQuery = useQuery({
    queryKey: ['surveillance', 'timeline'],
    queryFn: fetchTimeline,
    refetchInterval: 30000,
  });

  const videosQuery = useQuery({
    queryKey: ['surveillance', 'videos'],
    queryFn: fetchVideos,
    refetchInterval: 10000,
  });

  const liveCamerasQuery = useQuery({
    queryKey: ['surveillance', 'live-cameras'],
    queryFn: fetchLiveCameras,
    refetchInterval: 5000,
  });

  useEffect(() => {
    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let heartbeatTimer: ReturnType<typeof setInterval> | null = null;
    let backoffMs = 1000;
    let stopped = false;

    const invalidateAll = () => {
      queryClient.invalidateQueries({ queryKey: ['surveillance', 'alerts'] });
      queryClient.invalidateQueries({ queryKey: ['surveillance', 'stats'] });
      queryClient.invalidateQueries({ queryKey: ['surveillance', 'timeline'] });
      queryClient.invalidateQueries({ queryKey: ['surveillance', 'cameras'] });
    };

    const scheduleReconnect = () => {
      if (stopped || reconnectTimer) {
        return;
      }

      reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        connect();
      }, backoffMs);

      backoffMs = Math.min(backoffMs * 2, 30000);
    };

    const clearHeartbeat = () => {
      if (heartbeatTimer) {
        clearInterval(heartbeatTimer);
        heartbeatTimer = null;
      }
    };

    const connect = () => {
      if (stopped) {
        return;
      }

      socket = new WebSocket(getAlertsWebSocketUrl());

      socket.onopen = () => {
        backoffMs = 1000;
        clearHeartbeat();
        heartbeatTimer = setInterval(() => {
          if (socket?.readyState === WebSocket.OPEN) {
            socket.send('ping');
          }
        }, 20000);
      };

      socket.onmessage = (event) => {
        let parsed: AlertSocketMessage = {};
        try {
          parsed = JSON.parse(event.data) as AlertSocketMessage;
        } catch {
          invalidateAll();
          return;
        }

        if (parsed.type === 'connection.pong' || parsed.type === 'connection.ready') {
          return;
        }

        invalidateAll();
      };

      socket.onerror = () => {
        socket?.close();
      };

      socket.onclose = () => {
        clearHeartbeat();
        scheduleReconnect();
      };
    };

    connect();

    return () => {
      stopped = true;
      clearHeartbeat();
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }
      socket?.close();
    };
  }, [queryClient]);

  return {
    alerts: alertsQuery.data ?? [],
    stats: statsQuery.data,
    cameras: camerasQuery.data ?? [],
    liveCameraIds: liveCamerasQuery.data ?? [],
    timeline: timelineQuery.data ?? [],
    videos: videosQuery.data ?? [],
    isLoading:
      alertsQuery.isLoading ||
      statsQuery.isLoading ||
      camerasQuery.isLoading ||
      timelineQuery.isLoading ||
      videosQuery.isLoading ||
      liveCamerasQuery.isLoading,
  };
}
