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

function rankCamera(camera: CameraFeed): number {
  if (camera.status === 'alert' || camera.threatCount > 0) {
    return 0;
  }
  if (camera.status === 'online') {
    return 1;
  }
  return 2;
}

function getOrderedCameraCards(cameras: CameraFeed[], maxCards: number): CameraFeed[] {
  if (cameras.length === 0) {
    return [];
  }

  const ordered = [...cameras].sort((a, b) => {
    const rankDiff = rankCamera(a) - rankCamera(b);
    if (rankDiff !== 0) {
      return rankDiff;
    }

    const threatDiff = (b.threatCount ?? 0) - (a.threatCount ?? 0);
    if (threatDiff !== 0) {
      return threatDiff;
    }

    return a.id.localeCompare(b.id);
  });

  return ordered.slice(0, Math.max(maxCards, 1));
}

function getBackendOrigin(): string {
  const apiBase = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8001/api/v1';
  const root = new URL(apiBase);
  root.pathname = '';
  root.search = '';
  root.hash = '';
  return root.toString().replace(/\/$/, '');
}

function getMjpegStreamUrl(cameraId: string): string {
  return `${getBackendOrigin()}/live/${encodeURIComponent(cameraId)}/stream`;
}

const CameraPreview = ({ cameraId, useOverlayFrame }: { cameraId: string; useOverlayFrame: boolean }) => {
  const [src, setSrc] = useState(() => getCameraVideoSource(cameraId));
  const [failed, setFailed] = useState(false);
  const [usedFallback, setUsedFallback] = useState(false);
  const [mjpegFailed, setMjpegFailed] = useState(false);
  const [mjpegLoaded, setMjpegLoaded] = useState(false);
  const [jpegFailed, setJpegFailed] = useState(false);
  const [snapshotTs, setSnapshotTs] = useState(() => Date.now());
  const isWebcam = cameraId === WEBCAM_CAMERA_ID;
  const wantsImagePreview = isWebcam || useOverlayFrame;

  useEffect(() => {
    if (!isWebcam) {
      setSrc(getCameraVideoSource(cameraId));
    }
    setFailed(false);
    setUsedFallback(false);
    setMjpegFailed(false);
    setMjpegLoaded(false);
    setJpegFailed(false);
  }, [cameraId, isWebcam]);

  useEffect(() => {
    if (!wantsImagePreview || mjpegFailed || mjpegLoaded) {
      return;
    }

    const timeout = setTimeout(() => {
      setMjpegFailed(true);
    }, isWebcam ? 1500 : 2000);

    return () => clearTimeout(timeout);
  }, [isWebcam, wantsImagePreview, mjpegFailed, mjpegLoaded]);

  useEffect(() => {
    const shouldPollSnapshot = wantsImagePreview && mjpegFailed && !jpegFailed;
    if (!shouldPollSnapshot) {
      return;
    }

    const timer = setInterval(() => {
      setSnapshotTs(Date.now());
    }, isWebcam ? 500 : 450);

    return () => clearInterval(timer);
  }, [isWebcam, wantsImagePreview, mjpegFailed, jpegFailed]);

  return (
    <>
      {!failed ? (
        wantsImagePreview && !mjpegFailed ? (
          <img
            className="h-full w-full object-cover"
            src={getMjpegStreamUrl(cameraId)}
            alt={isWebcam ? 'Live webcam' : `${cameraId} threat overlay stream`}
            onLoad={() => {
              setMjpegLoaded(true);
            }}
            onError={() => {
              setMjpegFailed(true);
            }}
          />
        ) : wantsImagePreview && !jpegFailed ? (
          <img
            className="h-full w-full object-cover"
            src={`/live/${cameraId}.jpg?t=${snapshotTs}`}
            alt={isWebcam ? 'Live webcam' : `${cameraId} threat overlay`}
            onError={() => {
              if (isWebcam) {
                setFailed(true);
                return;
              }
              setJpegFailed(true);
            }}
          />
        ) : isWebcam ? (
          <div className="flex h-full w-full items-center justify-center text-[10px] font-semibold text-slate-500">
            Video unavailable
          </div>
        ) : (
          <video
            className="h-full w-full object-cover"
            autoPlay
            loop
            muted
            playsInline
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
  const visibleCameras = getOrderedCameraCards(cameras, 8);

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
            <CameraPreview cameraId={cam.id} useOverlayFrame={cam.status !== 'offline'} />
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
