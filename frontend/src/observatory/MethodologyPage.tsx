import { Link } from "react-router-dom";

import { useT } from "@/i18n";
import { Rich } from "@/i18n/Rich";
import { useInterface } from "@/stores/interface";

const NISAR_FACTS = ["product", "band", "polarizations", "resolution", "origin"];
const SOURCES = ["power", "firms", "usgs", "asf"];
const STEPS = [1, 2, 3, 4, 5, 6, 7];
const LIMITS = [1, 2, 3, 4, 5, 6, 7];

/**
 * Everything a reader needs to judge the numbers, in the order the pipeline runs.
 * Static on purpose: the methodology must not change between two visits.
 */
export function MethodologyPage() {
  const scientific = useInterface((state) => state.scientific);
  const t = useT();
  return (
    <div className="page">
      <div className="inner prose">
        <p className="label">{t("method.kicker")}</p>
        <h1 className="title">{t("method.title")}</h1>
        <p className="quiet" style={{ marginTop: 12 }}>
          {t("method.lead")}
        </p>

        <section className="block" aria-labelledby="nisar">
          <h2 id="nisar">NISAR</h2>
          <p>{t("method.nisar.body1")}</p>
          <p style={{ marginTop: 12 }}>
            <Rich text={t("method.nisar.body2")} />
          </p>
          <dl className="facts" style={{ marginTop: 16 }}>
            {NISAR_FACTS.map((fact) => (
              <div key={fact}>
                <dt>{t(`method.nisar.${fact}.label`)}</dt>
                <dd className={fact === "band" || fact === "resolution" ? "num" : undefined}>
                  {t(`method.nisar.${fact}.value`)}
                </dd>
              </div>
            ))}
          </dl>
          <p className="label" style={{ marginTop: 14 }}>
            <Rich text={t("method.nisar.provisional")} />
          </p>
        </section>

        <section className="block" aria-labelledby="fuentes">
          <h2 id="fuentes">{t("method.sources.title")}</h2>
          <p>{t("method.sources.body")}</p>
          <dl className="facts" style={{ marginTop: 16 }}>
            {SOURCES.map((source) => (
              <div key={source}>
                <dt>{t(`method.sources.${source}.label`)}</dt>
                <dd>{t(`method.sources.${source}.value`)}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section className="block" aria-labelledby="metodo">
          <h2 id="metodo">{t("method.steps.title")}</h2>
          <ol className="steps-list">
            {STEPS.map((step) => (
              <li key={step}>
                <Rich
                  text={t(`method.step.${step}`, {
                    margin: t(scientific ? "method.step.margin_scientific" : "method.step.margin_plain"),
                  })}
                />
              </li>
            ))}
          </ol>
        </section>

        <section className="block" aria-labelledby="limites">
          <h2 id="limites">{t("method.limits.title")}</h2>
          <ul className="steps-list">
            {LIMITS.map((limit) => (
              <li key={limit}>
                <Rich text={t(`method.limit.${limit}`)} />
              </li>
            ))}
          </ul>
        </section>

        <p style={{ marginTop: 32 }}>
          <Link className="btn tonal" to="/explorar">
            {t("about.cta.map")}
          </Link>
        </p>
      </div>
    </div>
  );
}
