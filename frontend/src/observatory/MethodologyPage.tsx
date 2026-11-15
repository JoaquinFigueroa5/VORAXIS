import { Link } from "react-router-dom";

import { useInterface } from "@/stores/interface";

/**
 * Everything a reader needs to judge the numbers, in the order the pipeline runs.
 * Static on purpose: the methodology must not change between two visits.
 */
export function MethodologyPage() {
  const scientific = useInterface((state) => state.scientific);
  return (
    <div className="page">
      <div className="inner prose">
        <p className="label">Data &amp; methodology</p>
        <h1 className="title">Qué mide este observatorio y qué no puede afirmar</h1>
        <p className="quiet" style={{ marginTop: 12 }}>
          Todo lo que aparece en la aplicación sale de dos fechas de radar y de cuatro catálogos públicos. Esta página
          explica de dónde viene cada número y dónde termina lo que se puede concluir.
        </p>

        <section className="block" aria-labelledby="nisar">
          <h2 id="nisar">NISAR</h2>
          <p>
            NISAR es un radar de apertura sintética en banda L (23 cm) construido por NASA e ISRO. La banda L atraviesa
            nubes y vegetación, así que observa de noche y con mal tiempo, algo que un sensor óptico no hace.
          </p>
          <p style={{ marginTop: 12 }}>
            Aquí solo se usa <strong>GCOV</strong>: el producto de retrodispersión de amplitud, geocodificado, con una
            resolución de unos 10 m. Cada píxel dice cuánta energía devolvió el suelo al radar. Un GCOV no es una foto:
            es una medida física, y se lee en decibelios (dB), no en colores.
          </p>
          <dl className="facts" style={{ marginTop: 16 }}>
            <div>
              <dt>Producto</dt>
              <dd>GCOV (L2, provisional)</dd>
            </div>
            <div>
              <dt>Banda</dt>
              <dd className="num">L · 24 cm</dd>
            </div>
            <div>
              <dt>Polarizaciones</dt>
              <dd>HH y HV, según la escena</dd>
            </div>
            <div>
              <dt>Resolución</dt>
              <dd className="num">~10 m por píxel</dd>
            </div>
            <div>
              <dt>Origen</dt>
              <dd>ASF DAAC</dd>
            </div>
          </dl>
          <p className="label" style={{ marginTop: 14 }}>
            Los productos marcados como <span className="num">PROVISIONAL</span> pueden reprocesarse en origen. Las dos
            fechas de un análisis se exigen con la misma madurez y la misma versión de proceso cuando es posible.
          </p>
        </section>

        <section className="block" aria-labelledby="fuentes">
          <h2 id="fuentes">Fuentes auxiliares</h2>
          <p>
            Ninguna de estas fuentes detecta cambios: aportan contexto. Que un incendio ocurriera al lado no prueba que
            causara el cambio en la señal.
          </p>
          <dl className="facts" style={{ marginTop: 16 }}>
            <div>
              <dt>NASA POWER</dt>
              <dd>Lluvia diaria por celda de 0,5° × 0,625° y su anomalía frente a la climatología</dd>
            </div>
            <div>
              <dt>NASA FIRMS</dt>
              <dd>Focos de calor VIIRS de 375 m, con potencia radiativa (MW) y confianza</dd>
            </div>
            <div>
              <dt>USGS FDSN</dt>
              <dd>Sismos de magnitud 3 o más, con profundidad y distancia al área</dd>
            </div>
            <div>
              <dt>ASF DAAC</dt>
              <dd>Catálogo de productos NISAR: huellas, órbita, polarización y madurez</dd>
            </div>
          </dl>
        </section>

        <section className="block" aria-labelledby="metodo">
          <h2 id="metodo">Cómo se calcula un cambio</h2>
          <ol className="steps-list">
            <li>
              <strong>Se eligen dos fechas comparables.</strong> Misma pista, mismo cuadro, misma dirección de órbita y
              misma polarización. Así el terreno se mira desde el mismo ángulo y lo que cambia es la superficie, no la
              geometría.
            </li>
            <li>
              <strong>Se promedia y se pasa a dB.</strong> El píxel se reduce a 40 m (multilook 4×4) para bajar el ruido
              de moteado, y la amplitud se convierte a decibelios: <span className="num">10 · log10</span>.
            </li>
            <li>
              <strong>Se resta la fecha posterior a la anterior.</strong> El resultado es un ráster firmado: negativo
              significa que la superficie devolvió menos señal (más oscura), positivo que devolvió más.
            </li>
            <li>
              <strong>Se marca lo que supera el umbral.</strong> Un píxel cuenta como cambio si se aleja del
              comportamiento típico de la escena más de{" "}
              <span className="num">{scientific ? "2 σ por defecto" : "un margen de seguridad"}</span>, y se descarta el
              borde del producto, donde la geometría se degrada.
            </li>
            <li>
              <strong>Se unen los píxeles en polígonos.</strong> Las manchas contiguas se agrupan, se descartan las
              menores de <span className="num">0,05 km²</span> y se calcula área, cambio medio en dB y score.
            </li>
            <li>
              <strong>Se busca evidencia en el intervalo.</strong> Para cada polígono se consultan sismos, incendios y
              lluvia entre las dos fechas y en un margen alrededor del área; se guarda la distancia, la diferencia
              temporal y la explicación de cada coincidencia.
            </li>
            <li>
              <strong>Se propone una etiqueta, si hay reglas que encajen.</strong> La firma en dB y la evidencia cercana
              deciden entre <span className="num">POSSIBLE_*</span>. Si ninguna regla encaja, el cambio queda{" "}
              <span className="num">UNCLASSIFIED</span> en lugar de forzarse.
            </li>
          </ol>
        </section>

        <section className="block" aria-labelledby="limites">
          <h2 id="limites">Limitaciones</h2>
          <ul className="steps-list">
            <li>
              <strong>La etiqueta es una hipótesis.</strong> <span className="num">POSSIBLE_FLOODING</span> significa
              «compatible con inundación», no «inundación confirmada». Confirmarla requiere datos hidrológicos o de
              campo.
            </li>
            <li>
              <strong>El score no es una probabilidad.</strong> Mide intensidad relativa del cambio en la señal, en una
              escala de 0 a 1 que no está calibrada contra verdad de terreno.
            </li>
            <li>
              <strong>Coincidencia no es causa.</strong> La ventana temporal entre dos pasadas es de días o semanas: un
              evento puede haber ocurrido después del cambio o no tener relación.
            </li>
            <li>
              <strong>El radar tiene un ángulo ciego.</strong> El agua en calma y las superficies muy lisas devuelven
              poca señal; la vegetación densa, mucha. Un mismo cambio físico puede verse distinto según la humedad del
              suelo.
            </li>
            <li>
              <strong>La cobertura no es total.</strong> La franja del producto puede no cubrir toda el área de interés;
              cuando la cobertura baja del 60 % la interfaz lo advierte.
            </li>
            <li>
              <strong>GCOV no mide deformación.</strong> Para movimiento del terreno hace falta interferometría (GUNW),
              que este observatorio todavía no procesa.
            </li>
            <li>
              <strong>Sin FIRMS no hay capa de incendios.</strong> Si falta la clave de acceso, la interfaz dice «no
              configurado» en vez de «sin incendios».
            </li>
          </ul>
        </section>

        <p style={{ marginTop: 32 }}>
          <Link className="btn tonal" to="/explorar">
            Volver al mapa
          </Link>
        </p>
      </div>
    </div>
  );
}
