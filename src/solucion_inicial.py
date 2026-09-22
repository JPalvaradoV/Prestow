"""
Construye una solucion inicial factible para el modelo de prestow, usada como
punto de partida (warm start) del solver en la pasada 1.

POR QUE HACE FALTA: se verifico empiricamente (sesion del 22 de septiembre de
2026, caso base Kiwi Arrow) que HiGHS, buscando desde cero, puede tardar mas
de 120 segundos en encontrar SIQUIERA UNA solucion entera factible para la
pasada 1 (makespan) -- no es un problema de calidad de la solucion, es que la
combinatoria de contiguidad + no-overstowage + llenado minimo hace dificil
para las heuristicas del solver encontrar el primer punto factible. Con un
limite de tiempo bajo (30-90 s, configurable en la pagina web), la pasada 1
no alcanza a devolver NADA y la corrida entera falla.

Esta funcion arma una asignacion factible con un heuristico simple (no busca
ser buena, solo factible) que sirve como MIP start: el solver arranca de ahi
y solo tiene que MEJORAR, no descubrir la factibilidad desde cero. Reutiliza
el mismo mecanismo de warm start que ya se usaba para la pasada 3 (balance de
peso, ver api._resolver_con_warm_start) -- api.py lo aplica ahora tambien en
la pasada 1.

ALGORITMO (greedy "llenado por niveles"):
  Se ordenan las combinaciones (producto, destino) por ROT descendente -- lo
  que se descarga AL FINAL se coloca primero, lo que se descarga PRIMERO
  queda arriba. Para cada combinacion se reparte su demanda entre las
  bodegas eligiendo siempre la de cursor (plan) mas bajo, con desempate por
  un orden fijo que prioriza la bodega "h1" de cada par de cuadrilla (ver
  restriccion 9 de modelo_prestow, ruptura de simetria: exige que h1 cargue
  al menos tanto como su bodega gemela h2 -- el desempate alinea el
  heuristico con esa restriccion en vez de violarla por construccion).

  Cada capa se llena hasta fraccion 1.0 (dentro de la tolerancia numerica)
  antes de avanzar el cursor de esa bodega. Eso cumple automaticamente:
    - contiguidad (5): nunca se abre un plan sin haber llenado el de abajo.
    - llenado minimo (5d, FRACCION_MINIMA_CAPA): la unica capa que puede
      quedar parcial es la ultima usada de cada bodega -- que es justamente
      la que el modelo exime de esa restriccion.
    - no-overstowage (4): como se procesa SIEMPRE en orden de ROT
      descendente y el cursor de cada bodega nunca retrocede, cada bodega
      termina con sus capas ordenadas de mayor a menor ROT de abajo hacia
      arriba.

GARANTIA: la funcion publica (construir_solucion_inicial) NUNCA devuelve una
asignacion sin verificar. Antes de devolverla, fija los valores construidos
en las variables del problema real (`prob`) y evalua TODAS sus restricciones
-- no solo las 4 que cubren verificar_cobertura/capacidad/contiguidad/
no_overstowage, sino tambien las que esas 4 no revisan (por ejemplo la (5b),
"ocupacion_max": se detecto el 22-sep-2026 que el heuristico podia pasar esas
4 y aun asi violar (5b), que en varias bodegas/planes es MAS ESTRICTA que la
capacidad real por producto porque usa una cota cruda de area/huella-minima
que el packer real supera). Si CUALQUIER restriccion falla -- o si el
heuristico se queda sin capacidad antes de colocar toda la demanda, algo que
no deberia pasar porque verificar_datos() ya valido que el area alcanza -- se
devuelve None: quien llama debe entonces resolver sin warm start (el
heuristico es un best-effort, nunca un riesgo de inyectarle al solver una
solucion invalida).
"""

from __future__ import annotations

import math

try:
    from . import modelo_prestow as _mp
except ImportError:
    import modelo_prestow as _mp  # type: ignore[import]

_EPS = 1e-6
# Tope de cuanto de una capa se llena por vuelta de ronda, como fraccion de
# la capacidad de esa capa para el producto en cuestion. Chico a proposito:
# permite que varios productos del mismo destino se mezclen dentro de una
# misma capa (ver el comentario largo en construir_asignacion_heuristica).
_FRACCION_CHUNK = 0.15


def _orden_bodegas_para_desempate() -> list[int]:
    """
    Orden de preferencia al desempatar bodegas con el mismo cursor. Prioriza
    la bodega "h1" de cada par en CUADRILLAS (la que la restriccion 9 exige
    que cargue al menos tanto como su gemela h2), y agrega el resto de
    BODEGAS al final por si hubiera bodegas fuera de las cuadrillas (no
    deberia pasar, verificar_datos() ya lo exige, pero no se asume).
    """
    orden: list[int] = []
    for bodegas_g in _mp.CUADRILLAS.values():
        for h in bodegas_g:
            if h not in orden:
                orden.append(h)
    for h in _mp.BODEGAS:
        if h not in orden:
            orden.append(h)
    return orden


def construir_asignacion_heuristica() -> dict[tuple[int, int, str, str], float] | None:
    """
    Devuelve x[(h,t,p,d)] -> unidades (solo entradas positivas) de una
    asignacion factible, o None si el heuristico no logro colocar toda la
    demanda dentro de la capacidad disponible.
    """
    if not _mp.DEMANDA or not _mp.BODEGAS or not _mp.PLANES:
        return None

    combos = list(_mp.DEMANDA.keys())
    orden_bodegas = [h for h in _orden_bodegas_para_desempate() if h in _mp.BODEGAS]
    prioridad = {h: i for i, h in enumerate(orden_bodegas)}
    max_plan = max(_mp.PLANES)
    min_plan = min(_mp.PLANES)

    # Cota cruda de la restriccion (5b) de modelo_prestow (enlace de w, no la
    # capacidad real): AREA[h,t] / la huella MAS CHICA entre todos los
    # productos, usada ahi solo para encender/apagar w. Es mas floja que la
    # capacidad real por producto (2) en general, PERO no siempre: se
    # verifico que para varias combinaciones bodega/plan la capacidad real
    # del packer (capacidad_unidades) supera a esta cota cruda -- el packer
    # logra mejor densidad que el area/huella-minima que asume (5b). Sin
    # este tope aparte, el heuristico arma capas que violan (5b) aunque
    # respeten (2) (detectado el 22-sep-2026: HiGHS rechazaba el warm start
    # por infeasibilidad ahi). No es un bug del modelo: (5b) es una cota mas
    # floja a proposito para no complicar el enlace con w; el heuristico
    # tiene que respetar ambas, igual que cualquier solucion valida.
    min_huella = min(_mp.HUELLA.values()) if _mp.HUELLA else None

    cursor = {h: min_plan for h in _mp.BODEGAS}
    fraccion_usada: dict[tuple[int, int], float] = {}
    carga_bruta: dict[tuple[int, int], float] = {}
    total_bodega: dict[int, float] = {h: 0.0 for h in _mp.BODEGAS}
    x: dict[tuple[int, int, str, str], float] = {}
    # Bodegas donde la capa actual se quedo sin espacio (por (2) o por la
    # cota cruda de (5b)) SIN llegar al llenado minimo de (5d). No se puede
    # abrir el plan de encima sin violar (5d) -- se deja esa bodega quieta
    # ahi: la capa actual queda como la ULTIMA ocupada de esa bodega, que
    # (5d) exime del llenado minimo por definicion.
    bodegas_agotadas: set[int] = set()

    def _cerrar_capa(h: int, t: int) -> None:
        fr = fraccion_usada.get((h, t), 0.0)
        if _mp.FRACCION_MINIMA_CAPA <= 0 or fr >= _mp.FRACCION_MINIMA_CAPA - _EPS:
            cursor[h] += 1
        else:
            bodegas_agotadas.add(h)

    # Se agrupan las combinaciones por destino (mismo ROT) y se procesan
    # tier por tier, de mayor a menor ROT -- eso solo, ya garantiza el
    # no-overstowage (4) por construccion (ver docstring del modulo).
    # DENTRO de un tier, en vez de agotar una combinacion entera antes de
    # pasar a la siguiente, se reparten en RONDAS de a lo sumo una fraccion
    # chica (_FRACCION_CHUNK) de una capa por vuelta. Hace falta para que
    # las capas queden MEZCLADAS entre productos del mismo destino: un
    # producto con capacidad_unidades grande (huella chica, ej. ARAUCO_BKP)
    # puede agotar la cota cruda de (5b) de una capa sin llegar al llenado
    # minimo de (5d) si se lo deja solo (detectado el 22-sep-2026, ver
    # _cerrar_capa). Mezclando con un producto de capacidad menor (mas
    # fraccion por unidad) se alcanza el 90% dentro del mismo tope crudo.
    # Mezclar es seguro entre combinaciones del MISMO tier: la restriccion
    # (4) no distingue productos dentro de una misma capa, solo compara
    # capas adyacentes.
    tiers: dict[int, list[tuple[str, str]]] = {}
    for (p, d) in combos:
        tiers.setdefault(_mp.ROT.get(d, 0), []).append((p, d))

    for rot in sorted(tiers, reverse=True):
        restante = {pd: float(_mp.DEMANDA[pd]) for pd in tiers[rot]}
        activos = [pd for pd in tiers[rot] if restante[pd] > _EPS]

        while activos:
            for (p, d) in list(activos):
                # El turno de esta combinacion en la ronda: puede necesitar
                # pasar por varias capas casi llenas (cerrarlas sin colocar
                # nada, solo avanzando el cursor) antes de encontrar una con
                # espacio real -- eso NO es "sin avance", es parte normal de
                # cerrar capas de a poco entre varias combinaciones del mismo
                # tier. Solo se rinde si se queda sin bodegas candidatas.
                while True:
                    candidatos = [
                        h for h in orden_bodegas
                        if cursor[h] <= max_plan and h not in bodegas_agotadas
                    ]
                    if not candidatos:
                        return None  # sin capacidad suficiente: no se usa warm start
                    # Desempate: cursor mas bajo primero (llenado por
                    # niveles), despues la bodega con MENOS unidades
                    # acumuladas hasta ahora (mantiene balanceadas las
                    # bodegas gemelas de (9) a medida que se avanza, no solo
                    # al final), y por ultimo el orden fijo que prioriza h1
                    # sobre h2 en caso de empate exacto.
                    h = min(
                        candidatos,
                        key=lambda h: (cursor[h], total_bodega[h], prioridad[h]),
                    )
                    t = cursor[h]
                    cap_pt = _mp.capacidad_unidades(h, p, t)
                    if cap_pt <= _EPS:
                        _cerrar_capa(h, t)
                        continue
                    frac_libre = 1.0 - fraccion_usada.get((h, t), 0.0)
                    if frac_libre <= _EPS:
                        _cerrar_capa(h, t)
                        continue
                    espacio = frac_libre * cap_pt
                    if min_huella:
                        cap_bruta_ht = _mp.AREA.get((h, t), 0.0) / min_huella
                        espacio_bruto = cap_bruta_ht - carga_bruta.get((h, t), 0.0)
                        espacio = min(espacio, espacio_bruto)
                    tope_ronda = max(cap_pt * _FRACCION_CHUNK, 1.0)
                    # x es entera en el modelo: se redondea hacia abajo,
                    # nunca hacia arriba, para no pasarse de la capacidad
                    # real por un error de punto flotante al reconstruir la
                    # fraccion desde unidades enteras (ver
                    # verificar_capacidad, que opera sobre unidades ya
                    # redondeadas).
                    amount = math.floor(min(restante[(p, d)], espacio, tope_ronda) + 1e-9)
                    if amount <= 0:
                        _cerrar_capa(h, t)
                        continue
                    clave = (h, t, p, d)
                    x[clave] = x.get(clave, 0.0) + amount
                    fraccion_usada[(h, t)] = fraccion_usada.get((h, t), 0.0) + amount / cap_pt
                    carga_bruta[(h, t)] = carga_bruta.get((h, t), 0.0) + amount
                    total_bodega[h] += amount
                    restante[(p, d)] -= amount
                    if fraccion_usada[(h, t)] >= 1.0 - _EPS or amount >= espacio - _EPS:
                        _cerrar_capa(h, t)
                    break  # turno de esta combinacion terminado por esta ronda

            activos = [pd for pd in activos if restante[pd] > _EPS]

    _reparar_simetria(x, total_bodega)

    return x


def _reparar_simetria(
    x: dict[tuple[int, int, str, str], float], total_bodega: dict[int, float]
) -> None:
    """
    Ultimo ajuste, best-effort: el desempate por total acumulado dentro del
    algoritmo principal deja la restriccion (9) (h1 >= h2 en unidades
    totales, bodegas gemelas) MUY cerca de cumplirse pero a veces no exacto
    -- se vio una diferencia de a lo sumo un par de unidades. Mueve ese
    resto de una celda de h2 a una celda YA EXISTENTE del mismo producto y
    destino en h1 que tenga espacio (no crea celdas nuevas ni reabre capas,
    asi que no puede romper contiguidad ni el enlace de w) -- verifica el
    espacio disponible en esa celda receptora contra las DOS cotas de
    capacidad ((2) real por producto y la cruda de (5b)) antes de mover,
    para no crear una violacion nueva ahi. Si no encuentra donde mover con
    espacio real -- por ejemplo si h1 no tiene ninguna celda con ese mismo
    producto+destino, o las que tiene ya estan llenas -- lo deja como esta:
    construir_solucion_inicial() vuelve a evaluar TODAS las restricciones
    despues igual, asi que un intento de reparo fallido nunca termina
    inyectandole a HiGHS una solucion invalida, en el peor caso simplemente
    no se usa warm start.
    """
    min_huella = min(_mp.HUELLA.values()) if _mp.HUELLA else None
    max_plan = max(_mp.PLANES)
    min_plan = min(_mp.PLANES)

    def _espacio_en_celda(h: int, t: int, p: str) -> float:
        cap_pt = _mp.capacidad_unidades(h, p, t)
        if cap_pt <= _EPS:
            return 0.0
        carga_fraccion = sum(
            u / _mp.capacidad_unidades(h, pp, t)
            for (hh, tt, pp, dd), u in x.items()
            if hh == h and tt == t
        )
        espacio_fraccion = (1.0 - carga_fraccion) * cap_pt
        if not min_huella:
            return max(espacio_fraccion, 0.0)
        carga_bruta_actual = sum(u for (hh, tt, pp, dd), u in x.items() if hh == h and tt == t)
        cap_bruta = _mp.AREA.get((h, t), 0.0) / min_huella
        espacio_bruto = cap_bruta - carga_bruta_actual
        return max(min(espacio_fraccion, espacio_bruto), 0.0)

    for bodegas_g in _mp.CUADRILLAS.values():
        for i in range(len(bodegas_g) - 1):
            h1, h2 = bodegas_g[i], bodegas_g[i + 1]
            if _mp.PISO.get(h1) != _mp.PISO.get(h2):
                continue
            deficit = total_bodega.get(h2, 0.0) - total_bodega.get(h1, 0.0)
            if deficit <= _EPS:
                continue
            deficit = math.ceil(deficit - _EPS)

            donantes = sorted(
                (clave for clave, u in x.items() if clave[0] == h2 and u >= deficit - _EPS),
                key=lambda clave: x[clave],
            )
            # planes de h1 ya ocupados (con carga real, no una capa vacia):
            # agregar `p_don` ahi -- exista o no ya ese mismo producto -- NO
            # viola no-overstowage (4) por si solo (esa restriccion solo
            # compara capas ADYACENTES, nunca dentro de una misma capa), pero
            # SI puede violarla contra las capas justo debajo y justo encima
            # de la receptora -- _es_compatible_overstow lo chequea. Ademas
            # hace falta espacio real, que _espacio_en_celda verifica contra
            # las dos cotas de capacidad.
            planes_h1 = sorted({clave[1] for clave in x if clave[0] == h1})
            tope_h1 = max(planes_h1) if planes_h1 else min_plan - 1
            candidatos_t = planes_h1 + (
                [tope_h1 + 1] if tope_h1 + 1 <= max_plan else []
            )

            def _es_compatible_overstow(t: int, d: str) -> bool:
                rot_d = _mp.ROT.get(d, 0)
                destinos_abajo = {
                    clave[3] for clave in x if clave[0] == h1 and clave[1] == t - 1
                }
                if destinos_abajo and rot_d > min(_mp.ROT.get(dd, 0) for dd in destinos_abajo):
                    return False
                destinos_arriba = {
                    clave[3] for clave in x if clave[0] == h1 and clave[1] == t + 1
                }
                if destinos_arriba and rot_d < max(_mp.ROT.get(dd, 0) for dd in destinos_arriba):
                    return False
                return True

            def _extraccion_es_segura(donante_clave, cantidad: float) -> bool:
                # Sacar unidades de la capa donante no puede dejarla por
                # debajo del llenado minimo (5d) SI tiene una capa encima
                # (si es la ultima de h2, esta exenta y no importa).
                _, t_don, p_don, _ = donante_clave
                if _mp.FRACCION_MINIMA_CAPA <= 0:
                    return True
                hay_encima = any(
                    clave[0] == h2 and clave[1] == t_don + 1 for clave in x
                )
                if not hay_encima:
                    return True
                fraccion_actual = sum(
                    u / _mp.capacidad_unidades(h2, pp, t_don)
                    for (hh, tt, pp, dd), u in x.items()
                    if hh == h2 and tt == t_don
                )
                cap_don = _mp.capacidad_unidades(h2, p_don, t_don)
                nueva_fraccion = fraccion_actual - cantidad / cap_don
                return nueva_fraccion >= _mp.FRACCION_MINIMA_CAPA - _EPS

            for donante in donantes:
                if not _extraccion_es_segura(donante, deficit):
                    continue
                _, _, p_don, d_don = donante
                t_receptor = next(
                    (
                        t for t in candidatos_t
                        if _espacio_en_celda(h1, t, p_don) >= deficit - _EPS
                        and _es_compatible_overstow(t, d_don)
                    ),
                    None,
                )
                if t_receptor is None:
                    continue
                receptor = (h1, t_receptor, p_don, d_don)

                x[donante] -= deficit
                if x[donante] <= _EPS:
                    del x[donante]
                x[receptor] = x.get(receptor, 0.0) + deficit
                total_bodega[h1] += deficit
                total_bodega[h2] -= deficit
                break
            # si ningun donante tenia un receptor con espacio, se deja como
            # esta -- la verificacion final en construir_solucion_inicial()
            # decide si el resultado sigue siendo utilizable como warm start.


def _filas_desde_asignacion(x: dict[tuple[int, int, str, str], float]) -> list[dict]:
    return [
        {"bodega": h, "plan": t, "producto": p, "destino": d, "unidades": int(round(u))}
        for (h, t, p, d), u in x.items()
        if u > 0.5
    ]


def _verificar_contra_restricciones(prob, valores: dict[str, float]) -> bool:
    """
    Verificacion final, exhaustiva: fija `valores` en las variables del
    problema y evalua TODAS las restricciones de `prob` (las 2 y pico mil del
    modelo real), no solo las 4 que cubren verificar_cobertura/capacidad/
    contiguidad/no_overstowage.

    POR QUE HACE FALTA ADEMAS DE ESAS 4: se detecto en la practica (22-sep-
    2026) que el heuristico podia pasar esas 4 verificaciones y aun asi ser
    rechazado por HiGHS al intentar usarlo como warm start, porque violaba la
    restriccion (5b) ("ocupacion_max", el enlace de w) -- una cota MAS FLOJA
    en general que la capacidad real por producto (2), pero no siempre: para
    varias combinaciones bodega/plan la capacidad real del packer supera esa
    cota cruda basada en la huella minima entre todos los productos. Evaluar
    TODAS las restricciones del propio `prob` es la unica forma de estar
    seguros de que HiGHS no va a rechazar la solucion por una restriccion que
    no se penso verificar aparte.

    No modifica x_vars/etc. de forma permanente: solo lee valores() para
    evaluar cada restriccion, no hace falta revertir nada porque quien llama
    (api.resolver_prestow) igual va a fijar estos mismos valores para el
    warm start real.
    """
    return not _violaciones(prob, valores)


def _violaciones(prob, valores: dict[str, float], tolerancia: float = 1e-4) -> list[tuple[str, float]]:
    """Como _verificar_contra_restricciones, pero devuelve el detalle (nombre
    de la restriccion, magnitud de la violacion) en vez de un bool -- pensado
    para diagnostico (tests, debugging), no para el camino normal."""
    for var in prob.variables():
        var.varValue = valores.get(var.name, 0.0)

    encontradas = []
    for name, c in prob.constraints.items():
        val = c.value()
        if val is None:
            encontradas.append((name, float("nan")))
            continue
        if c.sense == -1 and val > tolerancia:
            encontradas.append((name, val))
        elif c.sense == 1 and val < -tolerancia:
            encontradas.append((name, -val))
        elif c.sense == 0 and abs(val) > tolerancia:
            encontradas.append((name, abs(val)))
    return encontradas


def _construir_valores(
    asignacion, x_vars, y_vars, w_vars, z_vars, v_vars, T_max_var, peso_max_vars, peso_min_vars
) -> dict[str, float]:
    """Traduce una asignacion x[(h,t,p,d)]->unidades al diccionario
    nombre_variable->valor para TODAS las variables del modelo (x, y, w, z,
    v, T_max y, si corresponde, peso_max/peso_min). No verifica nada -- ver
    construir_solucion_inicial, que es quien debe usarse desde afuera."""
    valores: dict[str, float] = {}

    for clave, var in x_vars.items():
        valores[var.name] = asignacion.get(clave, 0.0)

    ocupado_ht: set[tuple[int, int]] = set()
    destino_ht: dict[tuple[int, int], set[str]] = {}
    carga_ht: dict[tuple[int, int], float] = {}
    for (h, t, p, d), u in asignacion.items():
        if u <= 0.5:
            continue
        ocupado_ht.add((h, t))
        destino_ht.setdefault((h, t), set()).add(d)
        carga_ht[(h, t)] = carga_ht.get((h, t), 0.0) + u

    for (h, t, d), var in y_vars.items():
        valores[var.name] = 1.0 if d in destino_ht.get((h, t), set()) else 0.0

    for (h, t), var in w_vars.items():
        valores[var.name] = 1.0 if (h, t) in ocupado_ht else 0.0

    for (h, t), var in z_vars.items():
        carga = carga_ht.get((h, t), 0.0)
        valores[var.name] = (
            float(math.ceil(carga / _mp.UNIDADES_POR_IZADA - _EPS)) if carga > _EPS else 0.0
        )

    destinos_h: dict[int, set[str]] = {}
    for (h, t), ds in destino_ht.items():
        destinos_h.setdefault(h, set()).update(ds)

    for (h, d), var in v_vars.items():
        valores[var.name] = 1.0 if d in destinos_h.get(h, set()) else 0.0

    horas_g = {}
    for g, bodegas_g in _mp.CUADRILLAS.items():
        horas_g[g] = sum(
            valores.get(z_vars[(h, t)].name, 0.0) * _mp.tiempo_ciclo(h)
            for h in bodegas_g
            for t in _mp.PLANES
        )
    valores[T_max_var.name] = max(horas_g.values()) if horas_g else 0.0

    if peso_max_vars:
        for k in peso_max_vars:
            restante_por_bodega: dict[int, float] = {h: 0.0 for h in _mp.BODEGAS}
            for (h, t, p, d), u in asignacion.items():
                if _mp.ROT.get(d, 0) > k:
                    restante_por_bodega[h] = restante_por_bodega.get(h, 0.0) + (
                        u * _mp.PESO.get(p, _mp.PESO_UNIDAD_RESPALDO)
                    )
            valores[peso_max_vars[k].name] = max(restante_por_bodega.values())
            valores[peso_min_vars[k].name] = min(restante_por_bodega.values())

    return valores


def construir_solucion_inicial(
    prob, x_vars, y_vars, w_vars, z_vars, v_vars, T_max_var, peso_max_vars, peso_min_vars, combos
) -> dict[str, float] | None:
    """
    Arma el diccionario nombre_variable -> valor listo para pasarle a
    api._resolver_con_warm_start (mismo formato que modelo_prestow.
    capturar_solucion), a partir de una asignacion heuristica.

    Devuelve None si el heuristico no encontro asignacion, o si la solucion
    construida no pasa la verificacion final contra TODAS las restricciones
    de `prob` -- en ambos casos, quien llama debe resolver sin warm start.
    """
    asignacion = construir_asignacion_heuristica()
    if asignacion is None:
        return None

    valores = _construir_valores(
        asignacion, x_vars, y_vars, w_vars, z_vars, v_vars, T_max_var, peso_max_vars, peso_min_vars
    )

    if not _verificar_contra_restricciones(prob, valores):
        return None

    return valores
