"use client";

import { useEffect, useState } from "react";
import { Box, RotateCw } from "lucide-react";

const MODEL_VIEWER_SCRIPT_ID = "lockerpulse-model-viewer-runtime";
const MODEL_VIEWER_SCRIPT_SRC = "/vendor/model-viewer.min.js";

const MODEL_MARKUP = `
  <model-viewer
    src="/models/inpost-locker.glb"
    alt="Interaktywny model 3D Paczkomatu używany w prezentacji LockerPulse"
    camera-controls
    auto-rotate
    rotation-per-second="18deg"
    shadow-intensity="1"
    exposure="1.15"
    environment-image="neutral"
    camera-orbit="42deg 68deg 5m"
    field-of-view="38deg"
    min-camera-orbit="auto auto 2.2m"
    max-camera-orbit="auto auto 9m"
    interaction-prompt="none"
    touch-action="pan-y"
    style="display:block;width:100%;height:100%;background:transparent;--poster-color:transparent;"
  ></model-viewer>
`;

export function LandingModelViewer() {
  const [isViewerReady, setIsViewerReady] = useState(false);
  const [loadFailed, setLoadFailed] = useState(false);

  useEffect(() => {
    let isMounted = true;

    async function loadViewer() {
      try {
        if (!customElements.get("model-viewer")) {
          await loadModelViewerScript();
        }
        if (isMounted) {
          setIsViewerReady(true);
        }
      } catch {
        if (isMounted) {
          setLoadFailed(true);
        }
      }
    }

    void loadViewer();

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="relative overflow-hidden rounded-xl border border-black/10 bg-[#11110f] shadow-[0_24px_70px_rgba(29,29,27,0.28)]">
      <div className="absolute inset-0 landing-hero-pattern opacity-[0.08]" aria-hidden="true" />
      <div className="pointer-events-none absolute -left-20 top-8 h-48 w-48 rounded-full bg-[#ffd200]/25 blur-3xl" />
      <div className="pointer-events-none absolute -right-16 bottom-0 h-40 w-40 rounded-full bg-white/10 blur-3xl" />

      <div className="relative flex flex-col">
        <div className="flex items-center justify-between gap-3 border-b border-white/10 px-4 py-3">
          <div className="inline-flex items-center gap-2 rounded-full bg-[#ffd200] px-3 py-1.5 text-xs font-black uppercase text-[#1d1d1b]">
            <Box className="h-4 w-4" />
            Interaktywny model Paczkomatu
          </div>
          <div className="hidden items-center gap-2 text-xs font-black uppercase text-white/65 sm:flex">
            <RotateCw className="h-4 w-4 text-[#ffd200]" />
            Przeciągnij, żeby obrócić
          </div>
        </div>

        <div className="relative h-[300px] sm:h-[350px] lg:h-[410px]">
          {isViewerReady ? (
            <div className="h-full w-full" dangerouslySetInnerHTML={{ __html: MODEL_MARKUP }} />
          ) : (
            <div className="flex h-full min-h-[260px] flex-col items-center justify-center gap-3 px-6 text-center">
              <div className="h-12 w-12 animate-spin rounded-full border-4 border-[#ffd200]/25 border-t-[#ffd200]" />
              <p className="text-sm font-black uppercase text-[#ffd200]">
                {loadFailed ? "Nie udało się załadować modelu" : "Ładowanie modelu Paczkomatu"}
              </p>
              <p className="max-w-sm text-xs font-semibold leading-5 text-white/55">
                {loadFailed
                  ? "Sprawdź plik /public/models/inpost-locker.glb i zależność @google/model-viewer."
                  : "Za chwilę pojawi się interaktywny podgląd 3D."}
              </p>
            </div>
          )}
        </div>

        <div className="pointer-events-none absolute bottom-4 left-4 right-4 flex items-end justify-between gap-3">
          <div className="rounded-lg border border-[#ffd200]/30 bg-black/50 px-3 py-2 text-xs font-black uppercase text-[#ffd200] backdrop-blur">
            GLB asset
          </div>
          <div className="rounded-lg border border-white/10 bg-black/50 px-3 py-2 text-xs font-black uppercase text-white/70 backdrop-blur">
            auto rotate on
          </div>
        </div>
      </div>
    </div>
  );
}

function loadModelViewerScript() {
  if (customElements.get("model-viewer")) {
    return Promise.resolve();
  }

  return new Promise<void>((resolve, reject) => {
    const timeoutId = window.setTimeout(() => {
      reject(new Error("model-viewer load timeout"));
    }, 10000);

    customElements
      .whenDefined("model-viewer")
      .then(() => {
        window.clearTimeout(timeoutId);
        resolve();
      })
      .catch((error: unknown) => {
        window.clearTimeout(timeoutId);
        reject(error);
      });

    const existingScript = document.getElementById(MODEL_VIEWER_SCRIPT_ID) as HTMLScriptElement | null;
    if (existingScript) {
      return;
    }

    const script = document.createElement("script");
    script.id = MODEL_VIEWER_SCRIPT_ID;
    script.type = "module";
    script.async = true;
    script.src = MODEL_VIEWER_SCRIPT_SRC;
    script.onerror = () => {
      window.clearTimeout(timeoutId);
      reject(new Error("model-viewer script failed"));
    };
    document.head.appendChild(script);
  });
}
