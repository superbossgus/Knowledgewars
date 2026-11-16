"""
Textos legales publicados, congelados por version (BOS-351 / BOS-346 §5.2).

La regla que esto implementa: *un renglon de consentimiento que apunta a un
texto que ya cambio no prueba nada*. Por eso cada version publicada del aviso y
de los terminos vive como un archivo inmutable del repositorio
(`backend/legal/<documento>-<version>.md`) y el hash SHA-256 se calcula del
contenido real del archivo al arrancar, no se escribe a mano. Si alguien edita
`aviso-privacidad-1.0.md` en vez de crear `1.1`, el hash cambia sin que cambie
la version y la prueba `test_consentimiento.py` falla: ahi esta la red.

Publicar una version nueva son dos pasos y ninguno toca el codigo de arriba:

  1. agregar `backend/legal/aviso-privacidad-1.1.md` (el 1.0 **no se toca**),
  2. subir `VERSION_AVISO` a `"1.1"`.

A partir de ese momento cada usuario cuyo ultimo consentimiento apunte a 1.0
entra por la pantalla de reaceptacion (§5.4) la siguiente vez que ingresa.
"""

import hashlib
import os
from typing import Dict

DIRECTORIO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "legal")

# Versiones vigentes. Subir estos numeros es lo que dispara la reaceptacion.
VERSION_AVISO = "1.0"
VERSION_TERMINOS = "1.0"

AVISO = "aviso"
TERMINOS = "terminos"

_ARCHIVOS = {
    AVISO: "aviso-privacidad-{version}.md",
    TERMINOS: "terminos-{version}.md",
}

_VERSIONES = {
    AVISO: VERSION_AVISO,
    TERMINOS: VERSION_TERMINOS,
}

_TITULOS = {
    AVISO: "Aviso de privacidad",
    TERMINOS: "Terminos de uso",
}


def _ruta(documento: str, version: str) -> str:
    return os.path.join(DIRECTORIO, _ARCHIVOS[documento].format(version=version))


def _leer(documento: str, version: str) -> str:
    ruta = _ruta(documento, version)
    if not os.path.exists(ruta):
        # Falla al arrancar, no al servir. Desplegar con `VERSION_AVISO` apuntando
        # a un archivo que no se subio dejaria `/privacidad` en 500 y el alta
        # abierta sin aviso, que es exactamente el hueco que cierra esta tarjeta.
        raise FileNotFoundError(
            f"Falta el texto legal congelado {ruta!r}. Al subir una version hay "
            f"que agregar el archivo; el anterior no se borra ni se edita."
        )
    with open(ruta, "r", encoding="utf-8") as fh:
        return fh.read()


def _hash(texto: str) -> str:
    """SHA-256 del texto exacto publicado (BOS-346 §5.1).

    Del contenido tal cual, en UTF-8 y sin normalizar: lo que se acredita es el
    byte exacto que se le mostro al usuario.
    """
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


# Se cargan una vez, al importar. Son archivos inmutables del repositorio.
_TEXTOS: Dict[str, str] = {d: _leer(d, v) for d, v in _VERSIONES.items()}
_HASHES: Dict[str, str] = {d: _hash(t) for d, t in _TEXTOS.items()}

HASH_AVISO = _HASHES[AVISO]
HASH_TERMINOS = _HASHES[TERMINOS]


def documento(nombre: str) -> dict:
    """El documento vigente, listo para servir en `/api/legal/{nombre}`."""
    if nombre not in _TEXTOS:
        raise KeyError(nombre)
    return {
        "documento": nombre,
        "titulo": _TITULOS[nombre],
        "version": _VERSIONES[nombre],
        "hash": _HASHES[nombre],
        "formato": "markdown",
        "texto": _TEXTOS[nombre],
    }


def versiones_vigentes() -> dict:
    """Lo que un renglon de consentimiento nuevo tiene que apuntar."""
    return {
        "version_aviso": VERSION_AVISO,
        "version_terminos": VERSION_TERMINOS,
        "hash_aviso": HASH_AVISO,
        "hash_terminos": HASH_TERMINOS,
    }


def esta_al_corriente(consentimiento: dict) -> bool:
    """`True` si ese consentimiento apunta a los textos vigentes.

    Compara version **y** hash. La version sola no alcanza: si alguien corrige
    una coma en el 1.0 ya publicado, el texto que el usuario acepto dejo de
    existir y hay que volver a preguntar.
    """
    if not consentimiento or not consentimiento.get("aceptado"):
        return False
    return (
        consentimiento.get("version_aviso") == VERSION_AVISO
        and consentimiento.get("version_terminos") == VERSION_TERMINOS
        and consentimiento.get("hash_aviso") == HASH_AVISO
        and consentimiento.get("hash_terminos") == HASH_TERMINOS
    )
