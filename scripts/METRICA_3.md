# Métrica 3 — jugadores activados

> Usuarios registrados que **completaron al menos una partida** (registrarse sin
> jugar no cuenta), medidos por consulta a MongoDB Atlas sobre partidas
> terminadas.
>
> — §5 del brief de Knowledge Wars (BOS-122). La definición no cambió al mover
> la métrica a Q1 2027 (BOS-348).

Esa frase tiene siete huecos que alguien tiene que rellenar. Si se rellenan el
día del corte, se rellenan discutiendo. Aquí están rellenados de antemano, con
el porqué y con el renglón de `backend/server.py` que lo justifica.

- Implementación: [`metrica_jugadores_activados.py`](metrica_jugadores_activados.py)
- Pruebas contra Mongo real: [`test_metrica_jugadores_activados.py`](test_metrica_jugadores_activados.py)

## Cómo se corre el día del corte

```bash
pip install pymongo
MONGO_URL="mongodb+srv://..." DB_NAME="knowledge_wars" \
  METRICA_EXCLUIR_DOMINIOS="viter.com.mx" \
  METRICA_EXCLUIR_CORREOS="gustavojimenezcerda@gmail.com,admin@cafecontrol.com" \
  METRICA_EXCLUIR_PATRONES="+kw" \
  python scripts/metrica_jugadores_activados.py --desde 2027-01-01 --hasta 2027-04-01
```

Esas tres listas son las cuentas internas ya decididas; el porqué de cada una
está en la decisión 4.

Sale así — esta salida es real, del escenario sembrado en
`test_escenario_del_corte` corriendo contra un Mongo local:

```
jugadores_activados    4       <- LA MÉTRICA 3
usuarios_registrados   7       <- denominador, sin cuentas internas
tasa_activacion        0.5714
partidas_terminadas    5
excluidas_autopartida  1
excluidos_internos     1
ids_huerfanos          1
cuentas_internas       1
ventana                ended_at >= 2027-01-01 00:00:00+00:00 y < 2027-04-01 00:00:00+00:00
```

El número que se reporta es `jugadores_activados`. Los demás renglones están
para que, cuando alguien diga «ese número está mal», se pueda ver *por dónde*
se fue la diferencia sin volver a correr nada.

## Las siete decisiones

### 1. ¿Qué campo marca una partida terminada? → `matches.status == "finished"`

No hay bandera `completed`, ni `is_finished`, ni un conteo de preguntas
respondidas que haya que comparar contra el total. Hay un solo campo de estado y
un solo valor que significa terminada. El backend escribe `"finished"` en
exactamente dos lugares:

- `finish_match()` — `backend/server.py:2206`, la partida llegó al final.
- `surrender_match()` — `backend/server.py:1660`, alguien se rindió.

Los seis valores posibles de `status`, todos verificados en el código:
`pending`, `active`, `finished`, `expired`, `cancelled`, `rejected`.

**No** se usa `ended_at IS NOT NULL` como marcador de terminada, aunque sería lo
intuitivo: el backend también escribe `ended_at` al rechazar
(`server.py:1578`) y al cancelar (`server.py:1608`) una invitación. Una
invitación rechazada tiene `ended_at` y nadie jugó nada. `status` es el campo
correcto; `ended_at` sirve solo para cortar por fecha.

### 2. ¿Cuenta una partida abandonada a medias? → No. Rendirse sí cuenta.

- **Abandonada** significa que quedó en `active` y nadie la cerró: el jugador
  cerró la pestaña, se le fue el internet, se aburrió. El estado se queda en
  `active` para siempre. No cuenta, y no se cuenta a propósito: la métrica
  pregunta quién *completó* una partida, y ahí nadie completó nada.
- **Rendirse** sí cuenta. `surrender_match()` deja la partida en `"finished"` y
  escribe `win_reason: "surrender"`. Quien se rindió entró a una partida real,
  contra un rival real, y la llevó hasta un resultado. Es una partida jugada con
  un final feo, no una partida sin jugar. El script no distingue por
  `win_reason`.
- `expired` (la invitación venció sin respuesta, `server.py:1503` y `:1726`),
  `cancelled` y `rejected` no cuentan: nunca hubo partida.

**Si se discrepa:** contar solo las que terminaron por puntaje es un
`{"win_reason": {"$ne": "surrender"}}` en `finished_filter()`. Mi opinión es que
bajaría el número sin medir mejor nada: para alguien que entra a probar el
juego, rendirse en la primera partida *es* haber jugado.

### 3. ¿Cuenta un jugador contra sí mismo? → No.

Si `player_a_id == player_b_id`, la partida no entra al conteo. El backend no lo
impide hoy: `create_match()` (`server.py:1435`) acepta cualquier `opponent_id`,
incluido el propio. Es el camino obvio para inflar la métrica sin querer —
probando el juego en dos pestañas — y para inflarla queriendo.

Dos matices que importan:

- Una autopartida **no borra** a quien además jugó contra alguien más: si Ana
  jugó contra sí misma y contra Beto, Ana está activada por la de Beto.
- Las autopartidas excluidas se reportan en `excluidas_autopartida`, para que el
  número excluido sea visible y no silencioso. Si resultan muchas, eso es la
  señal de que hay que arreglarlo en el backend, no en la consulta.

Se puede incluirlas con `--incluir-autopartidas` para comparar los dos números
en la misma sesión.

### 4. ¿Se excluyen cuentas internas? → Sí, del numerador **y** del denominador.

Cuatro mecanismos, en orden de preferencia:

1. `users.is_internal: true`. **El backend no escribe este campo todavía**: hay
   que ponerlo a mano (ver el comando de abajo) o agregarlo al registro. Es el
   mecanismo bueno porque queda escrito en la base y no depende de que alguien
   recuerde una variable de entorno.
2. `METRICA_EXCLUIR_CORREOS="a@x.com,b@y.com"` — lista exacta.
3. `METRICA_EXCLUIR_DOMINIOS="grupoviter.com"` — todo el dominio, con o sin
   arroba. Útil para sacar al equipo de un golpe.
4. `METRICA_EXCLUIR_PATRONES="+kw"` — subcadena en cualquier parte del correo.
   Es la red para las cuentas etiquetadas; se explica abajo, en «Las cuentas de
   prueba etiquetadas».

Las tres listas se comparan **sin distinguir mayúsculas**, y eso no es un detalle
cosmético: `register()` guarda el correo tal como lo escribió quien se registró,
sin normalizarlo (`server.py:288`), así que en la base puede haber
`QA@GrupoViter.com`. Quien escribe la lista de exclusión no tiene manera de
adivinar la capitalización. (De paso: que el backend no normalice el correo
significa que `ana@x.com` y `Ana@x.com` son dos cuentas distintas y que el login
de la segunda falla si la escribe diferente. Eso es un defecto del producto, no
de la métrica; va aparte.)

Salen del denominador también, no solo del numerador. Si no, la tasa de
activación castiga al producto por las cuentas del equipo que se registraron
para mirar y nunca jugaron. Cuántas se excluyeron sale en `excluidos_internos`
y `cuentas_internas`.

#### Quiénes son internos — decidido el 24 de octubre de 2026

Lo decidió Gustavo en [BOS-356](/BOS/issues/BOS-356). Está escrito aquí, y no
solo en el tablero, para que quien corra la consulta el día del corte no tenga
que ir a buscarlo. Si la lista cambia, se cambia aquí en el mismo commit.

- **Dominio permanente:** `viter.com.mx`.
- **Correos exactos:** `gustavojimenezcerda@gmail.com` (Gustavo) y
  `admin@cafecontrol.com` — este último es el admin que sembraba el
  `POST /api/seed` que se borró en [BOS-206](/BOS/issues/BOS-206); va en la
  lista por si sobrevive en algún entorno.
- **Convención para cuentas de prueba:** toda cuenta creada para probar,
  demostrar o sembrar Knowledge Wars se registra con etiqueta
  `gustavojimenezcerda+kw<algo>@gmail.com`, y se marca `is_internal: true` **en
  el mismo paso en que se crea**, no después.

El día del corte, eso son estos dos comandos:

```js
// 1. marcar las cuentas de la lista (el mecanismo bueno, queda en la base)
db.users.updateMany(
  {email: {$regex: "^(gustavojimenezcerda@gmail\\.com|admin@cafecontrol\\.com)$",
           $options: "i"}},
  {$set: {is_internal: true}}
)

// 2. y las etiquetadas, si alguna se creó sin marcar
db.users.updateMany(
  {email: {$regex: "\\+kw", $options: "i"}},
  {$set: {is_internal: true}}
)
```

**Va con `$regex`/`$options: "i"` y no con `updateOne({email: "..."})` a
propósito.** La coincidencia exacta es sensible a mayúsculas y `register()`
guarda el correo sin normalizar (`server.py:288`): si la cuenta quedó como
`Gustavojimenezcerda@gmail.com`, el `updateOne` no la encuentra, no falla, no
avisa, y la cuenta cuenta como jugador. Es el mismo motivo por el que las listas
por variable de entorno son insensibles a mayúsculas; el comando de la base
tiene que ser consistente con ellas. Y `updateMany`, no `updateOne`, porque
justamente puede haber más de una cuenta que coincida sin distinguir
capitalización.

El dominio `viter.com.mx` sale por la variable de entorno
(`METRICA_EXCLUIR_DOMINIOS="viter.com.mx"`) y no por un `updateMany`, porque es
permanente: no hay que volver a marcar a cada persona que entre al grupo.

#### Las cuentas de prueba etiquetadas

La convención de arriba —`gustavojimenezcerda+kw1@gmail.com`— tiene un hueco que
hay que nombrar: **ninguno de los otros dos mecanismos de lista la atrapa.**
`METRICA_EXCLUIR_CORREOS` es coincidencia exacta y habría que enumerar cada
etiqueta una por una; `METRICA_EXCLUIR_DOMINIOS` es por sufijo y el sufijo es
`@gmail.com`, donde viven los jugadores de verdad. Sin un tercer mecanismo, la
única defensa es que alguien se acuerde de poner `is_internal` al crear la
cuenta — disciplina, no mecanismo, y es lo primero que falla cuando hay prisa.

De ahí la lista 4:

```bash
METRICA_EXCLUIR_PATRONES="+kw" python scripts/metrica_jugadores_activados.py
```

Busca la subcadena en cualquier parte del correo, sin anclas, sin distinguir
mayúsculas, y las cuentas que caen se reportan en `cuentas_internas` y
`excluidos_internos` igual que las otras.

Dos cosas que importan de cómo está hecho:

- El patrón es **texto literal, no una regex**: pasa por `re.escape` antes de
  llegar a Mongo. `"+kw"` busca un `+` seguido de `kw`, no «una o más» de nada,
  y un patrón con `.*` o un paréntesis suelto no tumba la consulta ni barre con
  media base.
- Es **deliberadamente grueso**: cualquier correo que contenga el patrón queda
  fuera, incluido el de un jugador real que por casualidad lo tenga. Por eso el
  patrón debe ser específico (`+kw`, no `kw`), y por eso sigue siendo el tercer
  mecanismo en orden de preferencia y no el primero: lo que de verdad hay que
  hacer es marcar `is_internal` al crear la cuenta. Esto es la red por si no se
  hizo.

### 5. ¿Y un id de jugador que ya no tiene cuenta? → No cuenta.

`matches` guarda `player_a_id` / `player_b_id` como `ObjectId`, sin llave
foránea: Mongo no la tiene. Si una cuenta se borra, su id se queda en los
documentos de `matches` para siempre. Contar esos ids inflaría la métrica con
gente que ya no existe, así que el script cruza los candidatos contra `users` y
reporta los sobrantes en `ids_huerfanos`.

Hoy ese número debería ser 0 — el backend no borra usuarios. Si sale distinto de
0 el día del corte, significa que alguien borró cuentas a mano y vale la pena
preguntar por qué antes de reportar el número.

Un `player_b_id: null` (partida a medio crear) también se ignora.

### 6. ¿Qué pasa con las partidas de prueba? → No hay marca; se cubren por las decisiones 3 y 4.

No existe un campo `is_test` ni un `environment` en `matches`. Las partidas de
prueba se reconocen por quién las jugó, no por cómo están marcadas, y por eso la
defensa real es la decisión 4: marcar las cuentas internas. Si en enero hace
falta sembrar partidas de prueba con cuentas que *no* son internas, hay que
agregar una bandera a `matches` y filtrarla aquí — es un cambio de diez
renglones, pero hay que pedirlo antes, no el día del corte.

### 7. ¿Qué fecha corta el trimestre? → `ended_at`, en UTC, con `--hasta` exclusivo.

- Se corta por **`ended_at`** (cuándo terminó la partida), no por `created_at`
  de la partida ni por `created_at` del usuario. Lo que la métrica cuenta es el
  acto de completar, y el acto de completar ocurre en `ended_at`.
- Una consecuencia buena: alguien que se registró en diciembre y jugó en enero
  **sí** cuenta para Q1. Eso es lo correcto — el trimestre mide activación, no
  adquisición.
- `--desde` es inclusivo, `--hasta` es **exclusivo**. Q1 2027 completo es
  `--desde 2027-01-01 --hasta 2027-04-01`. Con `--hasta 2027-03-31` se pierde el
  31 de marzo entero, que es el error clásico.
- Todo en **UTC**, porque así lo escribe el backend. Ojo: escribe `ended_at` con
  `datetime.utcnow()` en `finish_match()` (`server.py:2207`, ingenuo) y con
  `datetime.now(timezone.utc)` en `surrender_match()` (`server.py:1661`, con
  zona). PyMongo guarda los dos como fecha UTC de BSON, así que la consulta no
  nota la diferencia; pero el corte es a medianoche UTC, no a medianoche de
  Ciudad de México. Para un corte trimestral la diferencia son seis horas en la
  frontera y no la peleo; si alguien quiere el corte en hora local, se le pasan
  las fechas ya desplazadas (`--desde 2027-01-01T06:00`).
- Sin `--desde` ni `--hasta` el número es **acumulado** (toda la historia). Es el
  que sirve para «cuántos jugadores activados tenemos», no para «cuántos en el
  trimestre».

## La misma consulta en una sola agregación

Para pegar en `mongosh` o en la pestaña Aggregation de Atlas, cuando no se
quiera correr Python. Da el mismo número que el script — hay una prueba
(`test_equivale_al_pipeline_de_una_sola_consulta`) que falla si alguien cambia
uno y no el otro.

```js
db.matches.aggregate([
  { $match: {
      status: "finished",
      $expr: { $ne: ["$player_a_id", "$player_b_id"] }
      // trimestre: , ended_at: { $gte: ISODate("2027-01-01"), $lt: ISODate("2027-04-01") }
  }},
  { $project: { jugadores: ["$player_a_id", "$player_b_id"] } },
  { $unwind: "$jugadores" },
  { $match: { jugadores: { $ne: null } } },
  { $group: { _id: "$jugadores" } },
  { $lookup: { from: "users", localField: "_id", foreignField: "_id", as: "cuenta" } },
  { $match: { "cuenta.0": { $exists: true }, "cuenta.0.is_internal": { $ne: true } } },
  { $count: "jugadores_activados" }
])
```

Esta versión solo respeta las exclusiones internas marcadas con `is_internal`;
las tres listas (correo, dominio, patrón) son del script. Si hace falta, se
agregan al `$match` final — o, más simple, se corren los dos `updateMany` de la
decisión 4 antes de pegar el pipeline, y entonces `is_internal` ya las cubre.

Los índices que ya existen la cubren: `backend/server.py:90-92` crea
`(player_a_id, status)`, `(player_b_id, status)` y `(status, ended_at)`. El
`$match` inicial usa el tercero.

## Cómo se probó

Contra MongoDB **real**, local (8.3.11), con datos sembrados a mano: 20 pruebas,
una base nueva por prueba, borrada al terminar. Costo $0.

```bash
MONGO_TEST_URL=mongodb://127.0.0.1:27017 \
  python scripts/test_metrica_jugadores_activados.py
```

No se usa `mongomock`: no resuelve `$expr` ni un arreglo literal con rutas de
campo dentro de `$project` — devuelve la cadena `"$player_a_id"` tal cual. Una
prueba que pasa contra un doble que no entiende la consulta no prueba nada.

Lo que cubren las pruebas, una por decisión: base vacía, registrados sin jugar,
no contar dos veces al mismo jugador, ignorar `pending`/`active`/`cancelled`/
`expired`/`rejected`, contar la rendición, id huérfano, `player_id` nulo,
autopartida (excluida, incluida con la bandera, y que no borre una partida real),
cuenta interna por bandera / por correo / por dominio / por patrón (incluido que
el patrón sea literal y no una regex, y que sin la variable de entorno no
excluya a nadie), ventana por `ended_at` con `--hasta` exclusivo, y la
equivalencia con el pipeline de arriba.

`test_escenario_del_corte` es el ensayo general: ocho cuentas, nueve partidas con
de todo (repetidas, autopartida, cuenta interna, rival borrado, en curso,
expirada, rechazada) y los nueve renglones de la salida verificados uno por uno.
Es la prueba que hay que leer si alguien quiere entender el número sin leer el
código.
