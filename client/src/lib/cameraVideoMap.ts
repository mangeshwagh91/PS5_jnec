const VIDEO_POOL = ['/videos/Firing.mp4', '/videos/smoke_fire.mp4'];
export const DEMO_CAMERA_IDS = ['CAM-012', 'CAM-013'] as const;

const EXPLICIT_CAMERA_VIDEO_MAP: Record<string, string> = {
  'CAM-012': '/videos/Firing.mp4',
  'CAM-013': '/videos/smoke_fire.mp4',
};

function hashCameraId(cameraId: string): number {
  let hash = 0;
  for (let i = 0; i < cameraId.length; i += 1) {
    hash = (hash * 31 + cameraId.charCodeAt(i)) >>> 0;
  }
  return hash;
}

export function getCameraVideoSource(cameraId: string): string {
  if (VIDEO_POOL.length === 0) {
    return '';
  }

  const explicitSrc = EXPLICIT_CAMERA_VIDEO_MAP[cameraId];
  if (explicitSrc) {
    return explicitSrc;
  }

  const index = hashCameraId(cameraId) % VIDEO_POOL.length;
  return VIDEO_POOL[index];
}

export function getCameraVideoFallback(cameraId: string): string {
  if (VIDEO_POOL.length <= 1) {
    return getCameraVideoSource(cameraId);
  }

  const primary = getCameraVideoSource(cameraId);
  const primaryIndex = VIDEO_POOL.findIndex((src) => src === primary);
  if (primaryIndex < 0) {
    return VIDEO_POOL[0];
  }

  const fallbackIndex = (primaryIndex + 1) % VIDEO_POOL.length;
  return VIDEO_POOL[fallbackIndex];
}

export function getDemoCameraSubset<T extends { id: string }>(cameras: T[]): T[] {
  const preferred = cameras.filter((camera) => DEMO_CAMERA_IDS.includes(camera.id as (typeof DEMO_CAMERA_IDS)[number]));
  if (preferred.length > 0) {
    return preferred.slice(0, 2);
  }
  return cameras.slice(0, 2);
}
