import DashboardLayout from '@/components/dashboard/DashboardLayout';
import type { CameraFeed, ThreatAlert } from '@/data/mockData';
import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Video, AlertTriangle, WifiOff } from 'lucide-react';
import { useSurveillanceData } from '@/hooks/useSurveillanceData';
import { uploadVideo, type VideoStream } from '@/lib/surveillanceApi';
import { useQueryClient } from '@tanstack/react-query';

const statusConfig = {
  online: { label: 'Online', color: 'text-success', bg: 'bg-success/10 border-success/20', icon: Video },
  offline: { label: 'Offline', color: 'text-muted-foreground', bg: 'bg-muted border-border', icon: WifiOff },
  alert: { label: 'Alert', color: 'text-destructive', bg: 'bg-destructive/10 border-destructive/20', icon: AlertTriangle },
};

type CameraCard = {
  camera: CameraFeed;
  source: string;
  isFocused: boolean;
};

function toAbsoluteVideoUrl(url: string): string {
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }

  const isProd = import.meta.env.PROD;
  const defaultApi = isProd ? 'https://ps5-jnec.onrender.com/api/v1' : 'http://localhost:8001/api/v1';
  const apiBase = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? defaultApi;
  const root = new URL(apiBase);
  root.pathname = '';
  root.search = '';
  root.hash = '';
  const prefix = root.toString().replace(/\/$/, '');
  return `${prefix}${url.startsWith('/') ? url : `/${url}`}`;
}

function getBackendOrigin(): string {
  const isProd = import.meta.env.PROD;
  const defaultApi = isProd ? 'https://ps5-jnec.onrender.com/api/v1' : 'http://localhost:8001/api/v1';
  const apiBase = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? defaultApi;
  const root = new URL(apiBase);
  root.pathname = '';
  root.search = '';
  root.hash = '';
  return root.toString().replace(/\/$/, '');
}

function getMjpegStreamUrl(cameraId: string): string {
  return `${getBackendOrigin()}/live/${encodeURIComponent(cameraId)}/stream`;
}

function getVideoSourceForCamera(cameraId: string, videos: VideoStream[]): string {
  if (videos.length === 0) {
    return '';
  }

  let hash = 0;
  for (let idx = 0; idx < cameraId.length; idx += 1) {
    hash = (hash * 31 + cameraId.charCodeAt(idx)) >>> 0;
  }

  const selected = videos[hash % videos.length];
  return toAbsoluteVideoUrl(selected.url);
}

function rankCamera(camera: CameraFeed): number {
  if (camera.status === 'alert' || camera.threatCount > 0) {
    return 0;
  }
  if (camera.status === 'online') {
    return 1;
  }
  return 2;
}

function getControlRoomCameraCards(
  cameras: CameraFeed[],
  videos: VideoStream[],
  alerts: ThreatAlert[],
  liveCameraIds: string[],
  focusedCameraId: string | null,
  onlyLive: boolean,
): CameraCard[] {
  const liveSet = new Set(liveCameraIds);
  const activeAlertCountByCamera = alerts.reduce<Record<string, number>>((acc, alert) => {
    if (alert.status !== 'active') {
      return acc;
    }
    acc[alert.camera] = (acc[alert.camera] ?? 0) + 1;
    return acc;
  }, {});

  const mappedCards: CameraCard[] = cameras
    .filter((baseCamera) => !onlyLive || liveSet.has(baseCamera.id))
    .map((baseCamera) => {
    const activeThreatCount = activeAlertCountByCamera[baseCamera.id] ?? 0;
    const camera = {
      ...baseCamera,
      status: activeThreatCount > 0 ? 'alert' : (liveSet.has(baseCamera.id) ? 'online' : 'offline'),
      threatCount: activeThreatCount,
    };

    return {
      camera,
      source: getVideoSourceForCamera(baseCamera.id, videos),
      isFocused: focusedCameraId === baseCamera.id,
    };
  });

  return mappedCards.sort((a, b) => {
    if (a.isFocused && !b.isFocused) {
      return -1;
    }
    if (!a.isFocused && b.isFocused) {
      return 1;
    }

    const rankDiff = rankCamera(a.camera) - rankCamera(b.camera);
    if (rankDiff !== 0) {
      return rankDiff;
    }

    const threatDiff = (b.camera.threatCount ?? 0) - (a.camera.threatCount ?? 0);
    if (threatDiff !== 0) {
      return threatDiff;
    }

    return a.camera.id.localeCompare(b.camera.id);
  });
}

const CameraPreview = ({ cameraId, source, useOverlayFrame, webcamStream }: { cameraId: string; source: string; useOverlayFrame: boolean; webcamStream?: MediaStream | null }) => {
  const [src, setSrc] = useState(source);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videoFailed, setVideoFailed] = useState(false);
  const [mjpegFailed, setMjpegFailed] = useState(false);
  const [mjpegLoaded, setMjpegLoaded] = useState(false);
  const [jpegFailed, setJpegFailed] = useState(false);
  const [snapshotTs, setSnapshotTs] = useState(() => Date.now());

  useEffect(() => {
    setSrc(source);
    setVideoFailed(false);
    setMjpegFailed(false);
    setMjpegLoaded(false);
    setJpegFailed(false);
  }, [cameraId, source]);

  useEffect(() => {
    if (webcamStream && videoRef.current) {
      videoRef.current.srcObject = webcamStream;
    }
  }, [webcamStream]);

  useEffect(() => {
    if (!useOverlayFrame || mjpegFailed || mjpegLoaded) {
      return;
    }

    const timeout = setTimeout(() => {
      setMjpegFailed(true);
    }, 2000);

    return () => clearTimeout(timeout);
  }, [useOverlayFrame, mjpegFailed, mjpegLoaded]);

  useEffect(() => {
    if (!useOverlayFrame || !mjpegFailed || jpegFailed) {
      return;
    }

    const timer = setInterval(() => {
      setSnapshotTs(Date.now());
    }, 450);

    return () => clearInterval(timer);
  }, [useOverlayFrame, mjpegFailed, jpegFailed]);

  return (
    <div className="h-full w-full">
      {webcamStream ? (
        <video
          ref={videoRef}
          className="h-full w-full object-cover scale-x-[-1]"
          autoPlay
          muted
          playsInline
        />
      ) : useOverlayFrame && !mjpegFailed ? (
        <img
          className="h-full w-full object-cover"
          src={getMjpegStreamUrl(cameraId)}
          alt={`${cameraId} threat overlay stream`}
          onLoad={() => {
            setMjpegLoaded(true);
          }}
          onError={() => {
            setMjpegFailed(true);
          }}
        />
      ) : useOverlayFrame && !jpegFailed ? (
        <img
          className="h-full w-full object-cover"
          src={`/live/${cameraId}.jpg?t=${snapshotTs}`}
          alt={`${cameraId} threat overlay`}
          onError={() => {
            setJpegFailed(true);
          }}
        />
      ) : !videoFailed && source ? (
        <video
          className="h-full w-full object-cover"
          autoPlay
          loop
          muted
          playsInline
          preload="auto"
          src={src}
          onError={() => {
            setVideoFailed(true);
          }}
        />
      ) : (
        <div className="flex flex-col h-full w-full items-center justify-center text-[10px] font-bold text-slate-400 bg-slate-50">
          <div className="relative flex items-center justify-center w-10 h-10 mb-2">
            <div className="absolute inset-0 rounded-full border-2 border-dashed border-slate-300 animate-[spin_8s_linear_infinite]" />
            <div className="w-3 h-3 rounded-full bg-slate-300 animate-pulse" />
          </div>
          <span className="tracking-widest">LINK SECURED</span>
        </div>
      )}
    </div>
  );
};

const CamerasPage = () => {
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState('');
  const [webcamEnabled, setWebcamEnabled] = useState(false);
  const [webcamStream, setWebcamStream] = useState<MediaStream | null>(null);
  const { cameras, videos, alerts, liveCameraIds } = useSurveillanceData();
  const focusedCameraId = searchParams.get('focus');
  const visibleCameras = getControlRoomCameraCards(cameras, videos, alerts, liveCameraIds, focusedCameraId, true);
  
  // If no workers are running but webcam is enabled, ensure we show at least one slot
  const wallCameras = visibleCameras.length === 0 && webcamEnabled 
    ? [{ 
        camera: { id: 'WEBCAM-01', name: 'User Webcam Feed', location: 'Local Testing', status: 'online' as const, threatCount: 0 }, 
        source: '', 
        isFocused: false 
      }]
    : visibleCameras.slice(0, 16);

  useEffect(() => {
    let stream: MediaStream | null = null;
    if (webcamEnabled) {
      navigator.mediaDevices.getUserMedia({ video: true })
        .then(s => {
          stream = s;
          setWebcamStream(s);
        })
        .catch(err => {
          console.error("Webcam failed:", err);
          setWebcamEnabled(false);
          setUploadMessage("Failed to access webcam. Please check permissions.");
        });
    } else {
      if (webcamStream) {
        webcamStream.getTracks().forEach(track => track.stop());
        setWebcamStream(null);
      }
    }
    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
    };
  }, [webcamEnabled]);

  const openUploadDialog = () => {
    fileInputRef.current?.click();
  };

  const handleFileSelected = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (!selectedFile) {
      return;
    }

    setIsUploading(true);
    setUploadMessage('Uploading video...');

    try {
      await uploadVideo(selectedFile);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['surveillance', 'videos'] }),
        queryClient.invalidateQueries({ queryKey: ['surveillance', 'live-cameras'] }),
      ]);
      setUploadMessage(`Uploaded: ${selectedFile.name}`);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Upload failed';
      setUploadMessage(message);
    } finally {
      setIsUploading(false);
      event.target.value = '';
    }
  };

  return (
    <DashboardLayout title="CAMERAS">
    <div className="p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-6">
          <label className="flex items-center gap-2 text-xs font-medium cursor-pointer">
            <span className={webcamEnabled ? 'text-primary font-bold' : 'text-muted-foreground'}>WEBCAM TEST</span>
            <div 
              onClick={() => setWebcamEnabled(!webcamEnabled)}
              className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${webcamEnabled ? 'bg-primary' : 'bg-muted'}`}
            >
              <span
                aria-hidden="true"
                className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-background shadow ring-0 transition duration-200 ease-in-out ${webcamEnabled ? 'translate-x-4' : 'translate-x-0'}`}
              />
            </div>
          </label>
        </div>
        <div className="flex items-center gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept="video/mp4,video/webm,video/quicktime,video/x-msvideo,video/x-matroska"
            className="hidden"
            onChange={handleFileSelected}
          />
          <button
            type="button"
            onClick={openUploadDialog}
            disabled={isUploading}
            className="rounded-md border border-border px-3 py-1.5 text-xs font-medium text-foreground hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isUploading ? 'Uploading...' : 'Upload Video'}
          </button>
        </div>
      </div>
      {uploadMessage ? <p className="mb-3 text-xs text-muted-foreground">{uploadMessage}</p> : null}
      <div className="flex items-center gap-4 mb-4 text-xs font-mono text-muted-foreground">
        <span>TOTAL: {visibleCameras.length}</span>
        <span className="text-success">â— ONLINE: {visibleCameras.filter(c => c.camera.status === 'online').length}</span>
        <span className="text-destructive">â— ALERT: {visibleCameras.filter(c => c.camera.status === 'alert').length}</span>
        <span>â— OFFLINE: {visibleCameras.filter(c => c.camera.status === 'offline').length}</span>
      </div>
      {wallCameras.length === 0 ? (
        <div className="rounded-lg border border-border bg-muted/30 p-4 text-sm text-muted-foreground">
          No live dashcam feed found. Start workers or upload videos to test playback.
        </div>
      ) : null}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {wallCameras.map(({ camera: cam, source, isFocused }, index) => {
          const cfg = statusConfig[cam.status];
          const isWebcamSlot = webcamEnabled && index === 0;
          return (
            <div
              key={cam.id}
              className={`rounded-lg border ${isWebcamSlot ? 'bg-primary/5 border-primary/20' : cfg.bg} p-3 cursor-pointer hover:scale-[1.01] transition-transform ${
                isFocused ? 'ring-2 ring-destructive ring-offset-2 ring-offset-background' : ''
              }`}
            >
              <div className="aspect-video bg-background/50 rounded-md mb-2 flex items-center justify-center border border-border overflow-hidden">
                <CameraPreview 
                  cameraId={cam.id} 
                  source={source} 
                  useOverlayFrame={cam.status !== 'offline'} 
                  webcamStream={isWebcamSlot ? webcamStream : null}
                />
              </div>
              <div className="flex items-center justify-between mb-0.5">
                <span className="font-mono text-xs text-muted-foreground">{isWebcamSlot ? "WEBCAM-01" : cam.id}</span>
                <div className={`w-2 h-2 rounded-full ${isWebcamSlot ? 'bg-primary' : cfg.color} bg-current ${cam.status === 'alert' ? 'threat-blink' : ''}`} />
              </div>
              <p className="text-xs font-medium text-foreground leading-tight">{isWebcamSlot ? "User Webcam Feed" : cam.name}</p>
              <p className="text-xs text-muted-foreground">{isWebcamSlot ? "Local Testing" : cam.location}</p>
              {cam.threatCount > 0 && !isWebcamSlot && (
                <p className="text-[10px] font-mono text-destructive mt-1">ALERT {cam.threatCount} active threat(s)</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  </DashboardLayout>
  );
};

export default CamerasPage;


