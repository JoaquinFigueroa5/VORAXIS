import { Link, NavLink, Outlet, useLocation } from "react-router-dom";

import { DownloadsMenu } from "@/observatory/DownloadsMenu";
import { useT } from "@/i18n";
import { useInterface } from "@/stores/interface";
import { useLocale, type Locale } from "@/stores/locale";

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

/** Same screens at two levels of detail: the numbers are a toggle, not a separate app. */
function ModeSwitch() {
  const scientific = useInterface((state) => state.scientific);
  const toggle = useInterface((state) => state.toggleScientific);
  const t = useT();
  return (
    <button
      className="btn tonal small mode"
      aria-pressed={scientific}
      onClick={toggle}
      title={t(scientific ? "shell.mode.scientific.title" : "shell.mode.explore.title")}
    >
      {t(scientific ? "shell.mode.scientific" : "shell.mode.explore")}
    </button>
  );
}

const LANGUAGES: { locale: Locale; short: string; name: string }[] = [
  { locale: "es", short: "ES", name: "Español" },
  { locale: "en", short: "EN", name: "English" },
];

/** Spanish or English; remembered in the browser, never in the URL. */
function LanguageSwitch() {
  const locale = useLocale((state) => state.locale);
  const setLocale = useLocale((state) => state.setLocale);
  const t = useT();
  const index = LANGUAGES.findIndex((language) => language.locale === locale);
  return (
    <div
      className="segmented lang"
      role="group"
      aria-label={t("shell.language")}
      style={{ "--n": LANGUAGES.length, "--i": Math.max(index, 0) } as React.CSSProperties}
    >
      {LANGUAGES.map((language) => (
        <button
          key={language.locale}
          type="button"
          lang={language.locale}
          aria-pressed={language.locale === locale}
          aria-label={language.name}
          title={language.name}
          onClick={() => setLocale(language.locale)}
        >
          {language.short}
        </button>
      ))}
    </div>
  );
}

/**
 * Two layouts share one header: the landing scrolls like a page (sections on
 * whole screens, a footer), the tools fill the window and scroll inside panels.
 */
export function Shell() {
  const site = useLocation().pathname === "/";
  const t = useT();
  const link = ({ isActive }: { isActive: boolean }) => `navlink${isActive ? " active" : ""}`;
  return (
    <div className={`shell${site ? " site" : ""}`}>
      <a className="skip" href="#contenido">
        {t("shell.skip")}
      </a>
      <header className="nav">
        <div className="nav-in">
          <Link to="/" className="mark" aria-label={t("shell.brand_home")}>
            <Mark />
            <span className="word">Voraxis</span>
          </Link>
          <nav className="links" aria-label={t("shell.sections")}>
            <NavLink to="/" end className={link}>
              {t("shell.nav.analysis")}
            </NavLink>
            <NavLink to="/explorar" className={link}>
              {t("shell.nav.explore")}
            </NavLink>
            <NavLink to="/insights" className={link}>
              {t("shell.nav.insights")}
            </NavLink>
            <NavLink to="/metodologia" className={link}>
              {t("shell.nav.methodology")}
            </NavLink>
            <NavLink to="/quienes-somos" className={link}>
              {t("shell.nav.about")}
            </NavLink>
          </nav>
          <ModeSwitch />
          <LanguageSwitch />
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
              <h2 id="close-h">{t("shell.footer.title")}</h2>
              <p>{t("shell.footer.subtitle")}</p>
              <Link className="btn btn--xl" to="/nuevo">
                {t("shell.footer.cta")}
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
                    <a href="#analisis">{t("shell.footer.saved")}</a>
                  </li>
                  <li>
                    <Link to="/nuevo">{t("shell.footer.new")}</Link>
                  </li>
                  <li>
                    <Link to="/metodologia">{t("shell.footer.methodology")}</Link>
                  </li>
                  <li>
                    <Link to="/quienes-somos">{t("shell.nav.about")}</Link>
                  </li>
                </ul>
              </div>
              <p className="legal" aria-label={t("shell.footer.legal_aria")}>
                {t("shell.footer.legal")}
              </p>
            </div>
          </div>
        </footer>
      ) : null}
    </div>
  );
}
