import type { CameraFeed } from '@/data/mockData';
import { useEffect, useState } from 'react';
import { Video, AlertTriangle } from 'lucide-react';
import { getCameraVideoSource, getCameraVideoFallback } from '@/lib/cameraVideoMap';

const WEBCAM_CAMERA_ID = 'CAM-WEBCAM-01';

const statusStyle: Record<string, string> = {
  online: 'bg-emerald-500',
  offline: 'bg-slate-300',
  alert: 'bg-red-500',
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
        <div className="flex h-full w-full items-center justify-center text-[10px] font-semibold text-slate-500">
          Video unavailable
        </div>
      )}
    </>
  );
};

const CameraGrid = ({ cameras }: { cameras: CameraFeed[] }) => {
  const visibleCameras = getDemoCameraCards(cameras);

  return (
    <div className="bg-white border border-slate-200 rounded-xl flex flex-col shadow-sm">
      <div className="px-4 py-3 border-b border-slate-100">
        <h2 className="text-sm font-bold text-slate-800 tracking-tight uppercase">Camera status</h2>
      </div>
      <div className="p-3 grid grid-cols-2 gap-2.5 overflow-y-auto max-h-[280px]">
        {visibleCameras.map((cam) => (
        <div
          key={cam.id}
          className={`rounded-lg border p-3 text-xs transition-colors cursor-pointer hover:bg-slate-50 ${
            cam.status === 'alert'
              ? 'border-red-200 bg-red-50/40'
              : 'border-slate-200 bg-white'
          }`}
        >
          <div className="aspect-video rounded-md mb-2 overflow-hidden border border-slate-200 bg-slate-100">
            <CameraPreview cameraId={cam.id} />
          </div>
          <div className="flex items-center justify-between mb-1">
            <span className="font-mono text-slate-500">{cam.id}</span>
            <div className={`w-2.5 h-2.5 rounded-full ${statusStyle[cam.status]}`} />
          </div>
          <p className="text-slate-800 font-semibold truncate">{cam.name}</p>
          <div className="flex items-center gap-1 mt-1 text-slate-500">
            {cam.status === 'alert' ? (
              <AlertTriangle className="w-3 h-3 text-red-600" />
            ) : (
              <Video className="w-3 h-3" />
            )}
            <span className="text-[10px]">{cam.location}</span>
          </div>
        </div>
        ))}
      </div>
    </div>
  );
};

export default CameraGrid;
