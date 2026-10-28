import { useCallback, useEffect, useRef, useState } from "react";
import { Camera, CameraResultType, CameraSource } from "@capacitor/camera";
import { Capacitor } from "@capacitor/core";
import { pickGalleryBlob } from "../lib/device";
import { CapturePhaseBar } from "./CapturePhaseBar";

export type CaptureSource = "LIVE_CAMERA" | "OWNER_GALLERY_UPLOAD";

type Props = {
  title?: string;
  hint?: string;
  allowGallery?: boolean;
  onCapture: (blob: Blob, source: CaptureSource) => void;
  onCancel: () => void;
};

async function openBrowserStream(): Promise<MediaStream> {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error("Camera API not available in this browser.");
  }
  const attempts: MediaStreamConstraints[] = [
    { audio: false, video: { facingMode: { ideal: "environment" } } },
    { audio: false, video: { facingMode: { ideal: "user" } } },
    { audio: false, video: true },
  ];
  let last: unknown;
  for (const constraints of attempts) {
    try {
      return await navigator.mediaDevices.getUserMedia(constraints);
    } catch (e) {
      last = e;
    }
  }
  throw last instanceof Error ? last : new Error("Camera permission denied or no camera found.");
}

export function EvidenceCapture({
  title = "Take photo",
  hint = "Frame the subject clearly inside the guides.",
  allowGallery = true,
  onCapture,
  onCancel,
}: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const isNative = Capacitor.isNativePlatform();

  const stopStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
  }, []);

  const startBrowserPreview = useCallback(async () => {
    setError(null);
    setReady(false);
    stopStream();
    try {
      const stream = await openBrowserStream();
      streamRef.current = stream;
      const video = videoRef.current;
      if (!video) {
        stream.getTracks().forEach((t) => t.stop());
        return;
      }
      video.srcObject = stream;
      video.setAttribute("playsinline", "true");
      video.muted = true;
      await video.play();
      setReady(true);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Unable to open camera.";
      setError(`${msg} You can upload from gallery instead.`);
      setReady(false);
    }
  }, [stopStream]);

  useEffect(() => {
    if (isNative) return;
    void startBrowserPreview();
    return () => stopStream();
  }, [isNative, startBrowserPreview, stopStream]);

  const shootBrowser = async () => {
    const video = videoRef.current;
    if (!video || !ready) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(
      (blob) => {
        if (blob) {
          stopStream();
          onCapture(blob, "LIVE_CAMERA");
        } else setError("Could not encode photograph.");
      },
      "image/jpeg",
      0.92,
    );
  };

  const shootNative = async () => {
    setBusy(true);
    setError(null);
    try {
      const photo = await Camera.getPhoto({
        quality: 90,
        resultType: CameraResultType.Uri,
        source: CameraSource.Camera,
        correctOrientation: true,
        saveToGallery: false,
      });
      if (!photo.webPath) throw new Error("Camera returned no image.");
      const res = await fetch(photo.webPath);
      const blob = await res.blob();
      onCapture(blob, "LIVE_CAMERA");
    } catch (e) {
      setError(
        `${e instanceof Error ? e.message : "Camera failed."} You can upload from gallery instead.`,
      );
    } finally {
      setBusy(false);
    }
  };

  const fromGallery = async () => {
    setBusy(true);
    setError(null);
    try {
      if (isNative) {
        const blob = await pickGalleryBlob();
        stopStream();
        onCapture(blob, "OWNER_GALLERY_UPLOAD");
        return;
      }
      fileRef.current?.click();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gallery pick failed.");
    } finally {
      setBusy(false);
    }
  };

  const onFileChosen = async () => {
    try {
      setError(null);
      const blob = await pickGalleryBlob(fileRef.current);
      stopStream();
      onCapture(blob, "OWNER_GALLERY_UPLOAD");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gallery pick failed.");
    } finally {
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  return (
    <div className="ve-cam">
      <header className="ve-cam-top">
        <button className="ve-cam-back" type="button" onClick={onCancel} aria-label="Cancel">
          ←
        </button>
        <div className="ve-cam-titles">
          <h1>{title}</h1>
          <CapturePhaseBar active="PHOTO" />
        </div>
      </header>

      {isNative ? (
        <div className="ve-cam-stage ve-cam-native">
          <p className="ve-cam-hint">{hint}</p>
          <p className="ve-cam-native-copy">Tap the shutter to open the device camera, or use Gallery.</p>
        </div>
      ) : (
        <div className="ve-cam-stage">
          <video ref={videoRef} playsInline muted autoPlay />
          <div className="ve-cam-frame" aria-hidden />
          <p className="ve-cam-hint">{hint}</p>
        </div>
      )}

      {error && <div className="ve-cam-err">{error}</div>}

      <footer className="ve-cam-dock">
        {allowGallery ? (
          <>
            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              capture={undefined}
              style={{ display: "none" }}
              onChange={() => void onFileChosen()}
            />
            <button className="ve-cam-secondary" type="button" disabled={busy} onClick={() => void fromGallery()}>
              Gallery
            </button>
          </>
        ) : (
          <span className="ve-cam-spacer" />
        )}
        <button
          className="ve-cam-shutter"
          type="button"
          disabled={busy || (!isNative && !ready)}
          onClick={() => void (isNative ? shootNative() : shootBrowser())}
          aria-label="Take photo"
        >
          <span />
        </button>
        {!isNative ? (
          <button className="ve-cam-secondary" type="button" disabled={busy} onClick={() => void startBrowserPreview()}>
            Retry cam
          </button>
        ) : (
          <span className="ve-cam-spacer" />
        )}
      </footer>
    </div>
  );
}

/** Back-compat wrapper used by existing pages. */
export function LiveCamera({
  title,
  hint,
  onCapture,
  onCancel,
  allowGallery = true,
}: {
  title?: string;
  hint?: string;
  onCapture: (blob: Blob, source?: CaptureSource) => void;
  onCancel: () => void;
  allowGallery?: boolean;
}) {
  return (
    <EvidenceCapture
      title={title}
      hint={hint}
      allowGallery={allowGallery}
      onCancel={onCancel}
      onCapture={(blob, source) => onCapture(blob, source)}
    />
  );
}
