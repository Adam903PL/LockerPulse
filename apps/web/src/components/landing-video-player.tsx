"use client";

import { useEffect, useRef, useState } from "react";
import { Maximize2, Pause, Play, Volume2, VolumeX } from "lucide-react";
import { cn } from "@/lib/utils";

const VIDEO_SRC = "/videos/lockerpulse-demo.mp4";

export function LandingVideoPlayer() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [volume, setVolume] = useState(0.82);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [hasVideo, setHasVideo] = useState(true);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) {
      return;
    }
    video.volume = volume;
    video.muted = isMuted;
  }, [volume, isMuted]);

  async function togglePlayback() {
    const video = videoRef.current;
    if (!video || !hasVideo) {
      return;
    }

    if (video.paused) {
      await video.play();
      setIsPlaying(true);
      return;
    }
    video.pause();
    setIsPlaying(false);
  }

  function changeProgress(value: string) {
    const video = videoRef.current;
    const nextTime = Number(value);
    setCurrentTime(nextTime);
    if (video && Number.isFinite(nextTime)) {
      video.currentTime = nextTime;
    }
  }

  function changeVolume(value: string) {
    const nextVolume = Number(value);
    if (!Number.isFinite(nextVolume)) {
      return;
    }
    setVolume(nextVolume);
    setIsMuted(nextVolume === 0);
  }

  async function openFullscreen() {
    const wrapper = videoRef.current?.parentElement;
    if (wrapper?.requestFullscreen) {
      await wrapper.requestFullscreen();
    }
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-black/10 bg-[#11110f] shadow-2xl">
      <div className="relative aspect-video bg-[#11110f]">
        {hasVideo ? (
          <video
            ref={videoRef}
            src={VIDEO_SRC}
            className="h-full w-full object-cover"
            preload="metadata"
            crossOrigin="anonymous"
            playsInline
            onLoadedMetadata={(event) => setDuration(event.currentTarget.duration || 0)}
            onTimeUpdate={(event) => setCurrentTime(event.currentTarget.currentTime)}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            onEnded={() => setIsPlaying(false)}
            onError={() => {
              setHasVideo(false);
              setIsPlaying(false);
            }}
          />
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-4 bg-[radial-gradient(circle_at_50%_20%,rgba(255,210,0,0.24),transparent_38%),linear-gradient(135deg,#11110f,#25251f)] p-6 text-center">
            <div className="rounded-full border border-[#ffd200]/40 bg-[#ffd200] px-4 py-2 text-xs font-black uppercase text-[#1d1d1b]">
              miejsce na film
            </div>
            <div>
              <p className="text-2xl font-black text-white">Dodaj film do playera</p>
              <p className="mt-2 max-w-md text-sm font-semibold leading-6 text-white/72">
                Wgraj plik jako <span className="font-mono text-[#ffd200]">/public/videos/lockerpulse-demo.mp4</span>,
                a ten customowy odtwarzacz automatycznie go pokaże.
              </p>
            </div>
          </div>
        )}

        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/85 via-black/45 to-transparent p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <button
              type="button"
              onClick={togglePlayback}
              disabled={!hasVideo}
              className={cn(
                "inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[#ffd200] text-[#1d1d1b] transition hover:scale-105",
                !hasVideo ? "cursor-not-allowed opacity-50" : "",
              )}
              aria-label={isPlaying ? "Pauza" : "Odtwórz"}
            >
              {isPlaying ? <Pause className="h-5 w-5 fill-current" /> : <Play className="ml-0.5 h-5 w-5 fill-current" />}
            </button>

            <div className="grid min-w-0 flex-1 gap-1">
              <input
                type="range"
                min={0}
                max={duration || 0}
                step={0.1}
                value={Math.min(currentTime, duration || currentTime)}
                onChange={(event) => changeProgress(event.target.value)}
                disabled={!hasVideo || duration === 0}
                className="landing-range"
                aria-label="Postęp filmu"
              />
              <div className="flex justify-between font-mono text-xs font-bold text-white/78">
                <span>{formatTime(currentTime)}</span>
                <span>{duration > 0 ? formatTime(duration) : "--:--"}</span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setIsMuted((current) => !current)}
                className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/15 bg-white/10 text-white transition hover:bg-white/20"
                aria-label={isMuted ? "Włącz dźwięk" : "Wycisz"}
              >
                {isMuted || volume === 0 ? <VolumeX className="h-5 w-5" /> : <Volume2 className="h-5 w-5" />}
              </button>
              <input
                type="range"
                min={0}
                max={1}
                step={0.01}
                value={isMuted ? 0 : volume}
                onChange={(event) => changeVolume(event.target.value)}
                className="landing-range w-24"
                aria-label="Głośność"
              />
              <button
                type="button"
                onClick={openFullscreen}
                className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/15 bg-white/10 text-white transition hover:bg-white/20"
                aria-label="Pełny ekran"
              >
                <Maximize2 className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function formatTime(value: number) {
  if (!Number.isFinite(value) || value <= 0) {
    return "00:00";
  }
  const minutes = Math.floor(value / 60);
  const seconds = Math.floor(value % 60);
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}
