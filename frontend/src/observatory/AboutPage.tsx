import { Layers } from "lucide-react";
import { Link } from "react-router-dom";

/**
 * Who is behind the observatory and what the team will not claim.
 * Static like the methodology: no queries, no scores, no dates.
 */

/** Reemplaza estas cuatro filas por el equipo real: nombre, rol y una línea de enfoque. */
const TEAM = [
  {
    name: "Joaquín Figueroa",
    role: "Desarrollador fullstack",
    icon: Layers,
  },
  {
    name: "Jorge Peralta",
    role: "Desarrollador fullstack",
    icon: Layers,
  },
  {
    name: "Jeremy Arévalo",
    role: "Desarrollador fullstack",
    icon: Layers,
  },
  {
    name: "Cristian Lima",
    role: "Desarrollador fullstack",
    icon: Layers,
  },
];

export function AboutPage() {
  return (
    <div className="page">
      <div className="inner prose">
        <p className="label">Quiénes somos</p>
        <h1 className="title">El equipo que traduce el radar a una lectura común</h1>
        <p className="quiet" style={{ marginTop: 12 }}>
          Voraxis nació en el NASA Space Apps Challenge con una idea sencilla: los datos de NISAR son públicos, pero no
          por eso son fáciles de leer. Somos el equipo que construye la capa que falta entre la señal del satélite y la
          pregunta de alguien que nunca ha abierto un archivo HDF5.
        </p>

        <section className="block" aria-labelledby="equipo">
          <h2 id="equipo">El equipo</h2>
          <p>
            Cuatro perfiles y una misma pregunta: cómo hacer visible un cambio que el ojo no siempre alcanza a ver. Cada
            persona responde por una parte del pipeline y por las limitaciones de esa parte.
          </p>
          <div className="sources">
            {TEAM.map((person) => (
              <div className="source" key={person.role}>
                <span className="glyph" aria-hidden="true">
                  <person.icon size={16} />
                </span>
                <div>
                  <p style={{ color: "var(--color-ink)", fontWeight: 500 }}>{person.name}</p>
                  <p className="label" style={{ marginTop: 2 }}>
                    {person.role}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="block" aria-labelledby="motivo">
          <h2 id="motivo">Por qué lo construimos</h2>
          <p>
            La superficie terrestre cambia todo el tiempo: se inunda, se quema, pierde vegetación o se deforma. Buena
            parte de esos cambios ocurre bajo nubes, de noche o en lugares donde nadie está mirando.
          </p>
          <p style={{ marginTop: 12 }}>
            NISAR observa esas condiciones porque usa radar en banda L, que atraviesa nubes y humo. El problema no es la
            falta de datos, sino el idioma: un producto <strong>GCOV</strong> se lee en decibelios y geometrías, no en
            titulares. Nuestro trabajo es hacer la traducción sin perder lo que la medición realmente dice.
          </p>
          <blockquote className="verdict">
            <p className="label">La idea en una frase</p>
            <p
              style={{
                marginTop: 8,
                color: "var(--color-ink)",
                fontSize: 20,
                letterSpacing: "-0.02em",
                lineHeight: 1.4,
              }}
            >
              «No queremos simplemente mostrar imágenes satelitales. Queremos convertir los datos de la Tierra en
              historias de cambio que todos podamos comprender.»
            </p>
          </blockquote>
        </section>

        <section className="block" aria-labelledby="principios">
          <h2 id="principios">Cómo trabajamos</h2>
          <ol className="steps-list">
            <li>
              <strong>La detección no es la causa.</strong> Mostramos qué cambió y qué evidencia lo acompaña; no
              afirmamos un diagnóstico que los datos no sostienen.
            </li>
            <li>
              <strong>La incertidumbre se ve.</strong> Calidad, cobertura y limitaciones van en pantalla, no en una nota
              al pie que nadie lee.
            </li>
            <li>
              <strong>Datos abiertos y reproducibles.</strong> Todo sale de NISAR y de catálogos públicos. El mismo par
              de fechas debería producir el mismo resultado.
            </li>
            <li>
              <strong>Lenguaje claro sin perder rigor.</strong> Si una cifra no se puede explicar, no se muestra. Si una
              regla no encaja, el cambio queda <span className="num">UNCLASSIFIED</span>.
            </li>
          </ol>
        </section>

        <section className="block" aria-labelledby="proyecto">
          <h2 id="proyecto">El proyecto, en datos</h2>
          <dl className="facts wide" style={{ marginTop: 16 }}>
            <div>
              <dt>Reto</dt>
              <dd>NASA Space Apps Challenge</dd>
            </div>
            <div>
              <dt>Misión</dt>
              <dd>NISAR · NASA e ISRO</dd>
            </div>
            <div>
              <dt>Producto</dt>
              <dd>GCOV L2 · banda L</dd>
            </div>
            <div>
              <dt>Datos</dt>
              <dd>ASF DAAC, NASA POWER, FIRMS, USGS</dd>
            </div>
            <div>
              <dt>Stack</dt>
              <dd>React, FastAPI, PostGIS</dd>
            </div>
            <div>
              <dt>Alcance</dt>
              <dd>Un análisis bien fundamentado antes que muchos casos</dd>
            </div>
          </dl>
        </section>

        <section className="block" aria-labelledby="creditos">
          <h2 id="creditos">Créditos y transparencia</h2>
          <p>
            NISAR es una misión conjunta de la NASA y la Organización de Investigación Espacial de la India (ISRO). Los
            productos se distribuyen a través de ASF DAAC. Las fuentes auxiliares son NASA POWER (lluvia), NASA FIRMS
            (focos de calor), USGS (sismos) y el mapa base de Esri, HERE, Garmin y OpenStreetMap.
          </p>
          <p className="quiet" style={{ marginTop: 12 }}>
            Voraxis es un proyecto independiente presentado en el NASA Space Apps Challenge. No es un producto oficial
            de la NASA ni de ISRO, y las etiquetas que genera son hipótesis, no confirmaciones.
          </p>
        </section>

        <p style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 32 }}>
          <Link className="btn tonal" to="/metodologia">
            Ver la metodología
          </Link>
          <Link className="btn tonal" to="/explorar">
            Volver al mapa
          </Link>
        </p>
      </div>
    </div>
  );
}