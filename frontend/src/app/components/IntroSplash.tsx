"use client";

import {
  useEffect,
  useState,
} from "react";

import Image from "next/image";

const STORAGE_KEY =
  "psmunnin-intro-shown";

const VISIBLE_DURATION_MS = 1_600;
const FADE_OUT_MS = 280;

type SplashPhase =
  | "hidden"
  | "visible"
  | "leaving";

export function IntroSplash() {
  const [
    phase,
    setPhase,
  ] = useState<SplashPhase>(
    "hidden"
  );

  useEffect(() => {
    let leaveTimer:
      | ReturnType<typeof setTimeout>
      | undefined;

    let removeTimer:
      | ReturnType<typeof setTimeout>
      | undefined;

    try {
      const alreadyShown =
        window.sessionStorage.getItem(
          STORAGE_KEY
        );

      const prefersReducedMotion =
        window.matchMedia?.(
          "(prefers-reduced-motion: reduce)"
        ).matches ?? false;

      window.sessionStorage.setItem(
        STORAGE_KEY,
        "1"
      );

      if (
        alreadyShown
        || prefersReducedMotion
      ) {
        return;
      }

      setPhase("visible");

      leaveTimer = setTimeout(() => {
        setPhase("leaving");
      }, VISIBLE_DURATION_MS);

      removeTimer = setTimeout(() => {
        setPhase("hidden");
      }, VISIBLE_DURATION_MS + FADE_OUT_MS);
    } catch {
      // sessionStorage indisponível ou bloqueado:
      // a aplicação não deve ser afetada.
      setPhase("hidden");
    }

    return () => {
      if (leaveTimer) {
        clearTimeout(leaveTimer);
      }

      if (removeTimer) {
        clearTimeout(removeTimer);
      }
    };
  }, []);

  if (phase === "hidden") {
    return null;
  }

  const basePath =
    process.env
      .NEXT_PUBLIC_BASE_PATH
    ?? "";

  return (
    <div
      className={
        phase === "leaving"
          ? "intro-splash intro-splash-leaving"
          : "intro-splash"
      }
      aria-hidden="true"
    >
      <Image
        src={
          `${basePath}`
          + "/psmunnin-logo.svg"
        }
        alt=""
        className="intro-splash-logo"
        width={88}
        height={88}
        priority
      />
    </div>
  );
}
