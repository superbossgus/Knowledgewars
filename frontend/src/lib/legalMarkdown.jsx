import React from 'react';

/**
 * Renderiza el subconjunto de Markdown con el que estan escritos el aviso de
 * privacidad y los terminos de uso (BOS-351).
 *
 * Por que a mano y no con `react-markdown`: el texto legal es un archivo
 * congelado del repositorio (`backend/legal/*.md`), no contenido que escriba un
 * usuario. El subconjunto que usa es corto y cerrado -- encabezados, parrafos,
 * listas, una tabla, negritas, cursivas, `codigo` y enlaces -- y meter una
 * dependencia nueva en el bundle para eso costaba mas que estas 90 lineas.
 *
 * **Nunca se usa `dangerouslySetInnerHTML`.** Todo sale como nodos de React, asi
 * que aunque el archivo viniera manipulado no puede inyectar HTML.
 */

// Marcas en linea: `codigo`, **negrita**, *cursiva* y [texto](destino).
// El orden importa: `codigo` primero, para que un asterisco dentro de un
// fragmento de codigo no se lea como negrita.
const EN_LINEA = /(`[^`]+`)|(\*\*[^*]+\*\*)|(\[[^\]]+\]\([^)]+\))|(\*[^*]+\*)/g;

function enLinea(texto, prefijo) {
  const partes = [];
  let ultimo = 0;
  let m;
  let i = 0;
  EN_LINEA.lastIndex = 0;
  while ((m = EN_LINEA.exec(texto)) !== null) {
    if (m.index > ultimo) partes.push(texto.slice(ultimo, m.index));
    const bruto = m[0];
    const clave = `${prefijo}-i${i++}`;
    if (bruto.startsWith('`')) {
      partes.push(
        <code key={clave} className="px-1 py-0.5 rounded bg-white/10 text-[hsl(25,100%,70%)] text-[0.9em]">
          {bruto.slice(1, -1)}
        </code>
      );
    } else if (bruto.startsWith('**')) {
      partes.push(<strong key={clave} className="font-bold text-white">{bruto.slice(2, -2)}</strong>);
    } else if (bruto.startsWith('[')) {
      const corte = bruto.indexOf('](');
      const etiqueta = bruto.slice(1, corte);
      const destino = bruto.slice(corte + 2, -1);
      const externo = /^https?:\/\//.test(destino);
      partes.push(
        <a
          key={clave}
          href={destino}
          target={externo ? '_blank' : undefined}
          rel={externo ? 'noopener noreferrer' : undefined}
          className="text-[hsl(220,100%,70%)] underline hover:text-white"
        >
          {etiqueta}
        </a>
      );
    } else {
      partes.push(<em key={clave} className="italic">{bruto.slice(1, -1)}</em>);
    }
    ultimo = m.index + bruto.length;
  }
  if (ultimo < texto.length) partes.push(texto.slice(ultimo));
  return partes.length ? partes : [texto];
}

const CLASES_TITULO = {
  1: 'text-3xl md:text-4xl font-extrabold font-brand text-white mt-2 mb-6',
  2: 'text-xl md:text-2xl font-bold text-[hsl(25,100%,60%)] mt-8 mb-3',
  3: 'text-lg font-bold text-white mt-6 mb-2',
};

function celdas(linea) {
  return linea.replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim());
}

const esSeparadorDeTabla = (linea) => /^\|[\s:|-]+\|$/.test(linea.trim());

export function renderLegal(markdown) {
  const lineas = String(markdown || '').replace(/\r\n/g, '\n').split('\n');
  const bloques = [];
  let i = 0;
  let k = 0;

  while (i < lineas.length) {
    const linea = lineas[i];
    const cruda = linea.trim();

    if (!cruda) { i += 1; continue; }

    const titulo = /^(#{1,6})\s+(.*)$/.exec(cruda);
    if (titulo) {
      const nivel = Math.min(titulo[1].length, 3);
      const Etiqueta = `h${nivel}`;
      bloques.push(
        <Etiqueta key={`h${k++}`} className={CLASES_TITULO[nivel]}>
          {enLinea(titulo[2], `h${k}`)}
        </Etiqueta>
      );
      i += 1;
      continue;
    }

    if (/^(-{3,}|\*{3,})$/.test(cruda)) {
      bloques.push(<hr key={`hr${k++}`} className="my-8 border-white/15" />);
      i += 1;
      continue;
    }

    // Tabla: encabezado + separador + renglones.
    if (cruda.startsWith('|') && i + 1 < lineas.length && esSeparadorDeTabla(lineas[i + 1])) {
      const encabezado = celdas(cruda);
      i += 2;
      const filas = [];
      while (i < lineas.length && lineas[i].trim().startsWith('|')) {
        filas.push(celdas(lineas[i].trim()));
        i += 1;
      }
      bloques.push(
        <div key={`t${k++}`} className="my-5 overflow-x-auto">
          <table className="w-full text-left text-sm border-collapse">
            <thead>
              <tr>
                {encabezado.map((c, n) => (
                  <th key={n} className="border-b-2 border-[hsl(220,100%,50%,0.4)] py-2 pr-4 font-bold text-white">
                    {enLinea(c, `th${n}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filas.map((fila, f) => (
                <tr key={f}>
                  {fila.map((c, n) => (
                    <td key={n} className="border-b border-white/10 py-2 pr-4 align-top text-white/80">
                      {enLinea(c, `td${f}-${n}`)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      continue;
    }

    // Cita en bloque: el aviso la usa para la nota de alcance.
    if (cruda.startsWith('>')) {
      const texto = [];
      while (i < lineas.length && lineas[i].trim().startsWith('>')) {
        texto.push(lineas[i].trim().replace(/^>\s?/, ''));
        i += 1;
      }
      bloques.push(
        <blockquote
          key={`q${k++}`}
          className="my-5 border-l-4 border-[hsl(25,100%,50%)] pl-4 text-white/75 italic"
        >
          {enLinea(texto.join(' '), `q${k}`)}
        </blockquote>
      );
      continue;
    }

    // Listas: con vineta o numeradas.
    const vineta = /^[-*]\s+/.test(cruda);
    const numerada = /^\d+\.\s+/.test(cruda);
    if (vineta || numerada) {
      const puntos = [];
      const patron = vineta ? /^[-*]\s+/ : /^\d+\.\s+/;
      while (i < lineas.length) {
        const actual = lineas[i];
        if (patron.test(actual.trim())) {
          puntos.push(actual.trim().replace(patron, ''));
          i += 1;
        } else if (actual.trim() && /^\s{2,}\S/.test(actual) && puntos.length) {
          // Continuacion indentada del punto anterior.
          puntos[puntos.length - 1] += ` ${actual.trim()}`;
          i += 1;
        } else {
          break;
        }
      }
      const Lista = vineta ? 'ul' : 'ol';
      bloques.push(
        <Lista
          key={`l${k++}`}
          className={`my-4 space-y-2 pl-6 text-white/80 ${vineta ? 'list-disc' : 'list-decimal'}`}
        >
          {puntos.map((p, n) => (
            <li key={n}>{enLinea(p, `li${k}-${n}`)}</li>
          ))}
        </Lista>
      );
      continue;
    }

    // Parrafo: se juntan las lineas hasta el siguiente bloque.
    const parrafo = [];
    while (i < lineas.length) {
      const actual = lineas[i].trim();
      if (
        !actual ||
        /^#{1,6}\s/.test(actual) ||
        actual.startsWith('|') ||
        actual.startsWith('>') ||
        /^[-*]\s+/.test(actual) ||
        /^\d+\.\s+/.test(actual) ||
        /^(-{3,}|\*{3,})$/.test(actual)
      ) {
        break;
      }
      parrafo.push(actual);
      i += 1;
    }
    bloques.push(
      <p key={`p${k++}`} className="my-4 leading-relaxed text-white/80">
        {enLinea(parrafo.join(' '), `p${k}`)}
      </p>
    );
  }

  return bloques;
}

export default renderLegal;
