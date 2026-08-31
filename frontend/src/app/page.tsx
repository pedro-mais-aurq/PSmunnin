import Image from "next/image";

import {
  DashboardClient,
} from "./components/DashboardClient";

import {
  IntroSplash,
} from "./components/IntroSplash";

export default function Home() {
  const basePath =
    process.env
      .NEXT_PUBLIC_BASE_PATH
    ?? "";

  return (
    <main className="app-shell">
      <IntroSplash />

      <div
        className="sun-mark"
        aria-hidden="true"
      />

      <div
        className="grain"
        aria-hidden="true"
      />

      <aside
        className="sidebar"
        aria-label={
          "Navegação principal"
        }
      >
        <div
          className={
            "brand-block "
            + "intro-logo"
          }
        >
          <Image
            src={
              `${basePath}`
              + "/psmunnin-logo.svg"
            }
            alt="Logo PS Munnin"
            className="brand-logo"
            width={42}
            height={42}
            priority
          />

          <div>
            <strong>
              PS Munnin
            </strong>

            <span>
              Lead intelligence
            </span>
          </div>
        </div>

        <nav
          className="nav-list"
        >
          <a
            className="active"
            href="#dashboard"
          >
            Dashboard
          </a>

          <a href="#leads">
            Leads
          </a>

          <a href="#pipeline">
            Pipeline
          </a>
        </nav>

        <div
          className={
            "sidebar-card"
          }
        >
          <span
            className="seal"
          >
            侘
          </span>

          <p>
            Interface mínima
            para operar o MVP
            sem perder clareza.
          </p>
        </div>
      </aside>

      <DashboardClient />
    </main>
  );
}
