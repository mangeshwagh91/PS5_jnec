import DashboardLayout from '@/components/dashboard/DashboardLayout';
import type { CameraFeed } from '@/data/mockData';
import { useEffect, useState } from 'react';
import { Video, AlertTriangle, WifiOff } from 'lucide-react';
import { useSurveillanceData } from '@/hooks/useSurveillanceData';
import { getCameraVideoSource, getCameraVideoFallback } from '@/lib/cameraVideoMap';

const WEBCAM_CAMERA_ID = 'CAM-WEBCAM-01';

const statusConfig = {
  online: { label: 'Online', color: 'text-success', bg: 'bg-success/10 border-success/20', icon: Video },
  offline: { label: 'Offline', color: 'text-muted-foreground', bg: 'bg-muted border-border', icon: WifiOff },
  alert: { label: 'Alert', color: 'text-destructive', bg: 'bg-destructive/10 border-destructive/20', icon: AlertTriangle },
};

function getDemoCameraCards(cameras: CameraFeed[]): CameraFeed[] {
  const byId = new Map(cameras.map((camera) => [camera.id, camera]));
  const cam012 = byId.get('CAM-012') ?? {
    id: 'CAM-012',
    name: 'Gate B North',
    location: 'North Entrance',
    status: 'online',
    threatCount: 0,
  };

  const cam013 = byId.get('CAM-013') ?? {
    id: 'CAM-013',
    name: 'Lab Smoke/Fire Demo',
    location: 'Safety Wing',
    status: 'online',
    threatCount: 0,
  };

  const webcam = byId.get(WEBCAM_CAMERA_ID) ?? {
    id: WEBCAM_CAMERA_ID,
    name: 'Live Webcam',
    location: 'Local Device',
    status: 'online',
    threatCount: 0,
  };

  return [cam012, cam013, webcam];
}

const CameraPreview = ({ cameraId }: { cameraId: string }) => {
  const [src, setSrc] = useState(() => getCameraVideoSource(cameraId));
  const [failed, setFailed] = useState(false);
  const [usedFallback, setUsedFallback] = useState(false);
  const [snapshotTs, setSnapshotTs] = useState(() => Date.now());
  const isWebcam = cameraId === WEBCAM_CAMERA_ID;

  useEffect(() => {
    if (!isWebcam) {
      setSrc(getCameraVideoSource(cameraId));
    }
    setFailed(false);
    setUsedFallback(false);
  }, [cameraId, isWebcam]);

  useEffect(() => {
    if (!isWebcam) {
      return;
    }

    const timer = setInterval(() => {
      setSnapshotTs(Date.now());
    }, 500);

    return () => clearInterval(timer);
  }, [isWebcam]);

  return (
    <>
      {!failed ? (
        isWebcam ? (
          <img
            className="h-full w-full object-cover"
            src={`/live/${WEBCAM_CAMERA_ID}.jpg?t=${snapshotTs}`}
            alt="Live webcam"
            onError={() => setFailed(true)}
          />
        ) : (
          <video
            className="h-full w-full object-cover"
            autoPlay
            loop
            muted
            playsInline
            controls
            preload="auto"
            src={src}
            onError={() => {
              if (!usedFallback) {
                setSrc(getCameraVideoFallback(cameraId));
                setUsedFallback(true);
                return;
              }
              setFailed(true);
            }}
          />
        )
      ) : (
        <div className="flex h-full w-full items-center justify-center text-xs font-semibold text-muted-foreground">
          Video unavailable
        </div>
      )}
    </>
  );
};

const CamerasPage = () => {
  const { cameras } = useSurveillanceData();
  const visibleCameras = getDemoCameraCards(cameras);

  return (
    <DashboardLayout title="CAMERAS">
    <div className="p-6">
      <div className="flex items-center gap-4 mb-4 text-xs font-mono text-muted-foreground">
        <span>TOTAL: {visibleCameras.length}</span>
        <span className="text-success">● ONLINE: {visibleCameras.filter(c => c.status === 'online').length}</span>
        <span className="text-destructive">● ALERT: {visibleCameras.filter(c => c.status === 'alert').length}</span>
        <span>● OFFLINE: {visibleCameras.filter(c => c.status === 'offline').length}</span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {visibleCameras.map(cam => {
          const cfg = statusConfig[cam.status];
          return (
            <div key={cam.id} className={`rounded-lg border ${cfg.bg} p-4 cursor-pointer hover:scale-[1.02] transition-transform`}>
              <div className="aspect-video bg-background/50 rounded-md mb-3 flex items-center justify-center border border-border overflow-hidden">
                <CameraPreview cameraId={cam.id} />
              </div>
              <div className="flex items-center justify-between mb-1">
                <span className="font-mono text-xs text-muted-foreground">{cam.id}</span>
                <div className={`w-2 h-2 rounded-full ${cfg.color} bg-current ${cam.status === 'alert' ? 'threat-blink' : ''}`} />
              </div>
              <p className="text-sm font-medium text-foreground">{cam.name}</p>
              <p className="text-xs text-muted-foreground">{cam.location}</p>
              {cam.threatCount > 0 && (
                <p className="text-[10px] font-mono text-destructive mt-2">ALERT {cam.threatCount} active threat(s)</p>
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
