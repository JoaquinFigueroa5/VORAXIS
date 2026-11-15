import { Link, NavLink, Outlet, useLocation } from "react-router-dom";

import { DownloadsMenu } from "@/observatory/DownloadsMenu";

/** Two radar passes and the line you drag between them. */
function Mark() {
  return (
    <svg width="26" height="26" viewBox="0 0 26 26" aria-hidden="true">
      <rect width="26" height="26" rx="7" fill="#232323" />
      <rect x="5" y="6" width="7" height="14" rx="1.5" fill="#8a8a8a" />
      <rect x="14" y="6" width="7" height="14" rx="1.5" fill="#f3f3f3" />
      <rect x="12" y="3.5" width="2" height="19" rx="1" fill="#a1ffcb" />
    </svg>
  );
}

/**
 * Two layouts share one header: the landing scrolls like a page (sections on
 * whole screens, a footer), the tools fill the window and scroll inside panels.
 */
export function Shell() {
  const site = useLocation().pathname === "/";
  const link = ({ isActive }: { isActive: boolean }) => `navlink${isActive ? " active" : ""}`;
  return (
    <div className={`shell${site ? " site" : ""}`}>
      <a className="skip" href="#contenido">
        Saltar al contenido
      </a>
      <header className="nav">
        <div className="nav-in">
          <Link to="/" className="mark" aria-label="Voraxis, inicio">
            <Mark />
            <span className="word">Voraxis</span>
          </Link>
          <nav className="links" aria-label="Secciones">
            <NavLink to="/" end className={link}>
              Análisis
            </NavLink>
            <NavLink to="/explorar" className={link}>
              Explorar
            </NavLink>
            <NavLink to="/nuevo" className={link}>
              Nuevo análisis
            </NavLink>
          </nav>
          <DownloadsMenu />
        </div>
      </header>
      <main id="contenido" tabIndex={-1}>
        <Outlet />
      </main>
      {site ? (
        <footer className="closing" id="contacto" aria-labelledby="close-h">
          <div className="wrap">
            <div className="closing__cta">
              <h2 id="close-h">Crea un análisis de cambio para tu zona</h2>
              <p>Las imágenes de NISAR son públicas. Cada fecha tarda unos minutos en descargarse la primera vez.</p>
              <Link className="btn btn--xl" to="/nuevo">
                Crear un análisis
              </Link>
            </div>
            <div className="closing__links">
              <div className="closing__row">
                <Link to="/" className="mark">
                  <Mark />
                  <span>Voraxis</span>
                </Link>
                <ul>
                  <li>
                    <a href="#analisis">Análisis guardados</a>
                  </li>
                  <li>
                    <Link to="/nuevo">Nuevo análisis</Link>
                  </li>
                  <li>
                    <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer">
                      Documentación de la API
                    </a>
                  </li>
                </ul>
              </div>
              <p className="legal">
                Radar: NISAR (NASA e ISRO), distribuido por ASF DAAC. Lluvia: NASA POWER. Incendios: NASA FIRMS. Sismos:
                USGS. Mapa base: Esri, HERE, Garmin, © OpenStreetMap.
              </p>
            </div>
          </div>
        </footer>
      ) : null}
    </div>
  );
}
