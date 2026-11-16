import { Layers } from "lucide-react";
import { Link } from "react-router-dom";

import { useT } from "@/i18n";
import { Rich } from "@/i18n/Rich";

/**
 * Who is behind the observatory and what the team will not claim.
 * Static like the methodology: no queries, no scores, no dates.
 */

/** Reemplaza estas cuatro filas por el equipo real: nombre, rol (clave del diccionario) y una línea de enfoque. */
const TEAM = [
  { name: "Joaquín Figueroa", role: "about.role.fullstack", icon: Layers },
  { name: "Jorge Peralta", role: "about.role.fullstack", icon: Layers },
  { name: "Jeremy Arévalo", role: "about.role.fullstack", icon: Layers },
  { name: "Cristian Lima", role: "about.role.fullstack", icon: Layers },
];

const PRINCIPLES = ["about.principle.1", "about.principle.2", "about.principle.3", "about.principle.4"];

const FACTS = ["challenge", "mission", "product", "data", "stack", "scope"];

export function AboutPage() {
  const t = useT();
  return (
    <div className="page">
      <div className="inner prose">
        <p className="label">{t("shell.nav.about")}</p>
        <h1 className="title">{t("about.title")}</h1>
        <p className="quiet" style={{ marginTop: 12 }}>
          {t("about.intro")}
        </p>

        <section className="block" aria-labelledby="equipo">
          <h2 id="equipo">{t("about.team.title")}</h2>
          <p>{t("about.team.body")}</p>
          <div className="sources">
            {TEAM.map((person) => (
              <div className="source" key={person.name}>
                <span className="glyph" aria-hidden="true">
                  <person.icon size={16} />
                </span>
                <div>
                  <p style={{ color: "var(--color-ink)", fontWeight: 500 }}>{person.name}</p>
                  <p className="label" style={{ marginTop: 2 }}>
                    {t(person.role)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="block" aria-labelledby="motivo">
          <h2 id="motivo">{t("about.why.title")}</h2>
          <p>{t("about.why.body1")}</p>
          <p style={{ marginTop: 12 }}>
            <Rich text={t("about.why.body2")} />
          </p>
          <blockquote className="verdict">
            <p className="label">{t("about.quote.label")}</p>
            <p
              style={{
                marginTop: 8,
                color: "var(--color-ink)",
                fontSize: 20,
                letterSpacing: "-0.02em",
                lineHeight: 1.4,
              }}
            >
              {t("about.quote.text")}
            </p>
          </blockquote>
        </section>

        <section className="block" aria-labelledby="principios">
          <h2 id="principios">{t("about.principles.title")}</h2>
          <ol className="steps-list">
            {PRINCIPLES.map((key) => (
              <li key={key}>
                <Rich text={t(key)} />
              </li>
            ))}
          </ol>
        </section>

        <section className="block" aria-labelledby="proyecto">
          <h2 id="proyecto">{t("about.facts.title")}</h2>
          <dl className="facts wide" style={{ marginTop: 16 }}>
            {FACTS.map((fact) => (
              <div key={fact}>
                <dt>{t(`about.fact.${fact}.label`)}</dt>
                <dd>{t(`about.fact.${fact}.value`)}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section className="block" aria-labelledby="creditos">
          <h2 id="creditos">{t("about.credits.title")}</h2>
          <p>{t("about.credits.body")}</p>
          <p className="quiet" style={{ marginTop: 12 }}>
            {t("about.credits.disclaimer")}
          </p>
        </section>

        <p style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 32 }}>
          <Link className="btn tonal" to="/metodologia">
            {t("about.cta.methodology")}
          </Link>
          <Link className="btn tonal" to="/explorar">
            {t("about.cta.map")}
          </Link>
        </p>
      </div>
    </div>
  );
}
