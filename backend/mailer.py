"""
Knowledge Wars - envio de correo

Hoy manda una sola cosa: el codigo de recuperacion de contrasena. Antes de
BOS-353 ese codigo viajaba en la respuesta HTTP de
`POST /api/auth/forgot-password` (el campo `_dev_code`), asi que cualquiera que
llamara al endpoint con un correo ajeno recibia el codigo y se quedaba con la
cuenta. El codigo ya no sale por ahi: sale por aqui, o no sale.

**Se habla SMTP a proposito, no la API de un proveedor concreto.** Todos los
que estan sobre la mesa -- Brevo, Resend, Amazon SES, Google Workspace --
ofrecen SMTP, asi que elegir proveedor es poner cinco variables de entorno y no
tocar codigo. Es stdlib (`smtplib`), asi que no agrega una dependencia a
`requirements.txt` ni un servicio mas que pueda caerse en el build.

Variables (todas opcionales; sin `SMTP_HOST` y `SMTP_FROM` no se manda nada):

    SMTP_HOST       servidor de salida del proveedor
    SMTP_PORT       587 por omision (STARTTLS). 465 usa SMTPS directo
    SMTP_USER       usuario SMTP. Vacio = no se autentica (relay local)
    SMTP_PASSWORD   contrasena o API key del proveedor. NUNCA en el repo
    SMTP_FROM       remitente, p. ej. "Knowledge Wars <no-reply@dominio>"
    SMTP_STARTTLS   1 por omision; apagarla solo tiene sentido en un relay local
    SMTP_TIMEOUT    segundos, 10 por omision

**Sin configurar no se manda y `send_password_reset_code` devuelve False.** El
endpoint contesta exactamente lo mismo que si hubiera mandado -- el mismo
mensaje generico para un correo que existe y uno que no -- asi que un SMTP sin
configurar no filtra quien esta registrado. Lo que no funciona es el rescate: el
usuario no recibe nada. Eso es aceptable mientras no haya usuarios reales, y es
justo lo que queda pendiente de que se contrate una cuenta de envio (BOS-353).
"""

import os
import re
import smtplib
import ssl
from email.message import EmailMessage

VERDADEROS = {"1", "true", "yes", "on", "si", "sí"}

# Direccion de destino aceptable. No pretende validar correos (eso lo hace
# `email-validator` en el alta): pretende que nada con un salto de linea o un
# espacio llegue a una cabecera del mensaje. Una cabecera partida es inyeccion
# de correo, y este es un camino de autenticacion.
DIRECCION_SANA = re.compile(r"^[^\s@,;:<>\"\\]+@[^\s@,;:<>\"\\]+$")

ASUNTO = "Tu codigo para recuperar la contrasena - Knowledge Wars"

CUERPO = """Alguien pidio recuperar la contrasena de esta cuenta en Knowledge Wars.

Tu codigo es: {codigo}

Vence en 15 minutos, sirve una sola vez y tienes 5 intentos para escribirlo.

Si no fuiste tu, ignora este correo. Sin el codigo nadie puede cambiar la
contrasena de la cuenta.
"""


def bandera(valor, por_omision=False):
    """Lee una variable de entorno booleana."""
    if valor is None or str(valor).strip() == "":
        return por_omision
    return str(valor).strip().lower() in VERDADEROS


def resolve_log_code_flag(flag_raw, environment):
    """Resuelve `PASSWORD_RESET_LOG_CODE` y rechaza encenderla fuera de desarrollo.

    Esa bandera escribe el codigo de recuperacion en el log del servidor cuando
    no hay SMTP configurado. Es el unico camino de desarrollo que queda, y no
    pasa por la respuesta HTTP.

    `environment` se lee con `"production"` por omision **a proposito**: si
    nadie pone `ENVIRONMENT`, se asume produccion y el arranque falla con la
    bandera encendida. Al contrario -- asumir desarrollo -- un olvido de
    configuracion se convertiria en codigos de recuperacion en el log de
    produccion, que es justo lo que BOS-353 vino a cerrar.
    """
    encendida = bandera(flag_raw, por_omision=False)
    entorno = (environment or "production").strip().lower()
    if encendida and entorno != "development":
        raise ValueError(
            "PASSWORD_RESET_LOG_CODE solo puede estar encendida con "
            "ENVIRONMENT=development: escribe el codigo de recuperacion en el "
            f"log del servidor (ENVIRONMENT={entorno!r})"
        )
    return encendida


def smtp_config():
    """La configuracion SMTP del entorno, o None si no esta completa.

    Se lee en cada llamada, no al importar: asi un cambio de variables en el
    panel del hosting aplica con un reinicio y no con un redeploy, y las
    pruebas pueden montar y desmontar la configuracion.
    """
    host = os.getenv("SMTP_HOST", "").strip()
    remitente = os.getenv("SMTP_FROM", "").strip()
    if not host or not remitente:
        return None

    try:
        puerto = int(os.getenv("SMTP_PORT", "587"))
        espera = float(os.getenv("SMTP_TIMEOUT", "10"))
    except ValueError:
        print("mailer: SMTP_PORT o SMTP_TIMEOUT no son numeros; no se mandara correo")
        return None

    return {
        "host": host,
        "port": puerto,
        "user": os.getenv("SMTP_USER", "").strip(),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "sender": remitente,
        "starttls": bandera(os.getenv("SMTP_STARTTLS"), por_omision=True),
        "timeout": espera,
    }


def is_configured():
    """True si hay por donde mandar correo."""
    return smtp_config() is not None


def build_password_reset_message(email, codigo, remitente):
    mensaje = EmailMessage()
    mensaje["Subject"] = ASUNTO
    mensaje["From"] = remitente
    mensaje["To"] = email
    mensaje.set_content(CUERPO.format(codigo=codigo))
    return mensaje


def _entregar(smtp, cfg, mensaje):
    if cfg["user"]:
        smtp.login(cfg["user"], cfg["password"])
    smtp.send_message(mensaje)


def send_password_reset_code(email, codigo):
    """Manda el codigo de 6 digitos por correo. True si salio.

    Es sincrona a proposito (`smtplib` lo es): el endpoint la llama con
    `asyncio.to_thread` para no bloquear el loop mientras el proveedor contesta.

    Nunca escribe el codigo en el log, ni al fallar. Un log con el codigo es la
    misma fuga que `_dev_code`, solo con un paso mas.
    """
    cfg = smtp_config()
    if cfg is None:
        return False

    if not DIRECCION_SANA.match(str(email or "")):
        print("mailer: direccion de destino rechazada (caracteres no validos para una cabecera)")
        return False

    mensaje = build_password_reset_message(email, codigo, cfg["sender"])
    contexto = ssl.create_default_context()
    try:
        if cfg["port"] == 465:
            with smtplib.SMTP_SSL(
                cfg["host"], cfg["port"], timeout=cfg["timeout"], context=contexto
            ) as smtp:
                _entregar(smtp, cfg, mensaje)
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=cfg["timeout"]) as smtp:
                if cfg["starttls"]:
                    smtp.starttls(context=contexto)
                _entregar(smtp, cfg, mensaje)
    except (smtplib.SMTPException, OSError, ssl.SSLError) as exc:
        print(
            "mailer: no se pudo enviar el codigo de recuperacion: "
            f"{type(exc).__name__}: {exc}"
        )
        return False
    return True
