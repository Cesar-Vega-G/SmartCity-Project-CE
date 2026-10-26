"""Valida los SQL del sprint contra la carga real sin conservar cambios de estado.

Uso desde la raíz: python postgres/consultas/validar_consultas.py
La conexión reutiliza comun.py y .env; nunca exporta credenciales.
No crea datos, vistas o índices. El refresco se hace por separado, si hace falta.
"""
import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time


def encode(value):
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    raise TypeError(type(value).__name__)


def statements(path):
    # Solo los archivos de ejemplos SELECT; no se usa para DDL ni cuerpos PL/pgSQL.
    sql = re.sub(r'--[^\n]*', '', path.read_text(encoding='utf-8-sig'))
    return [s.strip() for s in sql.split(';') if s.strip()]


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--salida', type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    output = args.salida or repo / 'postgres/consultas/evidencia'
    output.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(repo / 'data/generators'))
    from comun import conectar_pg
    import psycopg

    report = {'fecha_costa_rica': datetime.now(timezone(timedelta(hours=-6))).isoformat(),
              'commit_sql': subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip(),
              'validador_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'archivos_sha256': {}, 'consultas': {}, 'comprobaciones': []}
    results = {}

    def check(name, condition, detail=''):
        report['comprobaciones'].append({'nombre': name, 'ok': bool(condition), 'detalle': detail})
        print(('OK ' if condition else 'FALLO ') + name, flush=True)

    def query(c, sql, params=None):
        return c.execute(sql, params).fetchall()

    def run(c, key, path, sql):
        if not re.match(r'(?i)^(SELECT|WITH)\b', sql):
            raise ValueError('Se esperaba solo lectura: ' + key)
        start = time.perf_counter()
        cur = c.execute(sql)
        rows = cur.fetchall()
        elapsed = round((time.perf_counter() - start) * 1000, 3)
        names = [col.name for col in cur.description]
        results[key] = rows
        report['archivos_sha256'][path.relative_to(repo).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        report['consultas'][key] = {'archivo': path.relative_to(repo).as_posix(), 'filas': len(rows),
                                  'columnas': names, 'muestra': rows[:5], 'ms_observados': elapsed}
        print(f'{key}: {len(rows)} filas', flush=True)

    try:
        with conectar_pg() as c:
            c.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
            c.execute("SET LOCAL statement_timeout = '180s'")
            report['servidor'] = query(c, 'select version(), current_database(), current_setting(\'server_version_num\')')[0]
            report['carga'] = dict(zip(['mediciones', 'primera', 'ultima'], query(c, 'select count(*), min(fecha_hora), max(fecha_hora) from medicion')[0]))
            sensors = query(c, '''select s.id_sensor,s.nombre,t.nombre,s.estado,s.id_ubicacion,
                u.nombre_zona,u.id_distrito,d.nombre,s.id_organismo,s.fecha_instalacion
                from sensor s join tipo_sensor t using(id_tipo) join ubicacion u using(id_ubicacion)
                join distrito d using(id_distrito) order by s.id_sensor''')
            districts = dict(query(c, 'select id_distrito,nombre from distrito'))
            organisms = query(c, 'select id_organismo,nombre,responsable from organismo')
            report['carga']['sensores'] = len(sensors)
            report['carga']['distritos'] = len(districts)
            report['indices_medicion'] = query(c, "select tablename,indexname,indexdef from pg_indexes where tablename like 'medicion%' order by tablename,indexname")
            report['estadisticas_medicion'] = query(c, "select relname,n_live_tup,last_analyze,last_autoanalyze from pg_stat_user_tables where relname like 'medicion%' order by relname")
            check('Motor PostgreSQL 16', 160000 <= int(report['servidor'][2]) < 170000)
            check('Carga de referencia completa', len(sensors) == 324 and report['carga']['mediciones'] == 4664093,
                  'Referencia del repositorio: 324 sensores y 4.664.093 mediciones; diferencias requieren explicación.')
            for path in sorted((repo / 'postgres/consultas').glob('[0-9][0-9]_*.sql')):
                key = path.name[:2]
                if key in {'09', '10'}:
                    continue
                parts = statements(path)
                if len(parts) != 1:
                    raise ValueError(f'{path.name}: se esperaba una sentencia')
                run(c, key, path, parts[0])
            for num in ['09', '10']:
                path = next((repo / 'postgres/vistas_funciones').glob(num + '_*.sql'))
                parts = statements(path)
                if len(parts) != (3 if num == '09' else 9):
                    raise ValueError(f'{path.name}: cambió la estructura; revisar separación de efectos')
                for suffix, sql in zip('abc', parts[:3]):
                    run(c, num + suffix, path, sql)

            expected = [(s[0],s[1],s[2],s[3]) for s in sensors]
            check('01: detalle y unicidad de sensores', Counter(results['01']) == Counter(expected))
            expected = [(s[0],s[1],s[3],s[4],s[5],s[7]) for s in sensors]
            check('02: ubicación y unicidad', Counter(results['02']) == Counter(expected))
            states = Counter(s[3] for s in sensors)
            check('03: tres estados y total', results['03'] == [(x,states[x]) for x in ['activo','inactivo','mantenimiento']])
            org_counts = Counter(s[8] for s in sensors)
            check('04: organismos incluidos con cero', Counter(results['04']) == Counter((*o,org_counts[o[0]]) for o in organisms))
            loc_counts = Counter((s[4],s[5],s[6],s[7]) for s in sensors)
            check('05: ubicaciones por identificador', Counter(results['05']) == Counter((*k,v) for k,v in loc_counts.items()))
            check('06: año de instalación', dict(results['06']) == Counter(s[9].year for s in sensors))
            history = dict(query(c, 'select id_sensor,max(fecha_hora) from medicion group by id_sensor'))
            check('07: ausencia de historia y exhaustividad', {r[0] for r in results['07']} == {s[0] for s in sensors if s[0] not in history})
            district_counts = Counter(s[6] for s in sensors)
            active_counts = Counter(s[6] for s in sensors if s[3] == 'activo')
            levels = sorted({district_counts[d] for d in districts}, reverse=True)
            ranking = [(levels.index(district_counts[d])+1,d,name,district_counts[d],active_counts[d]) for d,name in districts.items()]
            check('08: conteos, ceros y ranking denso', Counter(results['08']) == Counter(ranking))
            mv = query(c, 'select posicion_sensores,id_distrito,distrito,total_sensores,sensores_activos from mv_ranking_zonas')
            check('09a: ranking materializado coincide con 08', Counter(mv) == Counter(ranking))
            check('09a: volumen materializado', sum(r[4] for r in results['09a']) == report['carga']['mediciones'] and len(results['09a']) == len(districts))
            aggregates = query(c, '''select u.id_distrito,count(*),count(*) filter(where v.limite_alerta is not null),
                count(*) filter(where m.valor>v.limite_alerta), round(avg(m.valor) filter(where v.nombre='no2'),2),
                round(avg(m.valor) filter(where v.nombre='pm25'),2)
                from medicion m join sensor s using(id_sensor) join ubicacion u using(id_ubicacion)
                join variable v using(id_variable) group by u.id_distrito''')
            agg = {r[0]: r[1:] for r in aggregates}
            expected_mv = []
            for d in districts:
                n,limited,over,no2,pm25 = agg.get(d,(0,0,0,None,None))
                pct = (Decimal(100)*over/limited).quantize(Decimal('.001'),rounding=ROUND_HALF_UP) if limited else Decimal(0)
                expected_mv.append((d,n,over,pct,no2,pm25))
            actual_mv = query(c, 'select id_distrito,total_mediciones,mediciones_sobre_limite,pct_sobre_limite,promedio_no2,promedio_pm25 from mv_ranking_zonas')
            check('09a: agregados de criticidad y contaminación', Counter(actual_mv) == Counter(expected_mv))
            pct_levels = sorted({r[3] for r in expected_mv}, reverse=True)
            activity_levels = sorted({r[1] for r in expected_mv}, reverse=True)
            expected_positions = {(r[0],pct_levels.index(r[3])+1,activity_levels.index(r[1])+1) for r in expected_mv}
            check('09a: posiciones por criticidad y actividad', set(query(c,'select id_distrito,posicion_criticidad,posicion_actividad from mv_ranking_zonas')) == expected_positions)
            base = query(c, '''select d.nombre,count(*),round(avg(m.valor),2),max(m.valor),count(*) filter(where m.valor>v.limite_alerta)
                from medicion m join variable v using(id_variable) join sensor s using(id_sensor)
                join ubicacion u using(id_ubicacion) join distrito d using(id_distrito)
                where v.nombre='no2' and fecha_hora>='2025-01-01' and fecha_hora<'2025-02-01' group by d.nombre''')
            check('09b: vista frente a tablas originales', Counter(results['09b']) == Counter(base))
            base = query(c, '''select o.nombre,c.nombre_categoria,count(*),count(*) filter(where estado='activo'),
                count(*) filter(where estado='inactivo'),count(*) filter(where estado='mantenimiento')
                from sensor s join organismo o using(id_organismo) join tipo_sensor t using(id_tipo)
                join categoria_sensor c using(id_categoria) group by o.nombre,c.nombre_categoria''')
            check('09c: organismo, categoría y estados', Counter(results['09c']) == Counter(base))
            detail = results['17']
            variables = {r[4] for r in detail}
            check('10a: variables y cantidades frente a 17', {r[0] for r in results['10a']} == variables and sum(r[3] for r in results['10a']) == len(detail))
            for row in results['10a']:
                vals = [r[6] for r in detail if r[4] == row[0]]
                dates = [r[2] for r in detail if r[4] == row[0]]
                avg = (sum(vals)/len(vals)).quantize(Decimal('.001'),rounding=ROUND_HALF_UP)
                over = sum(v > row[2] for v in vals) if row[2] is not None else 0
                check('10a: resumen de '+row[0], (row[3],row[4],row[5],row[6],row[7],row[9],row[10]) == (len(vals),avg,min(vals),max(vals),over,min(dates),max(dates)))
            expected = [(s[0],s[1],s[2],s[3],s[5],s[9]) for s in sensors if s[7]=='Centro']
            check('10b: sensores del distrito', Counter(results['10b']) == Counter(expected))
            check('10b: mayúsculas/minúsculas', query(c,"select * from fn_sensores_por_distrito('centro')") == results['10b'])
            base = query(c, '''select m.fecha_hora,m.id_sensor,d.nombre,m.valor,v.limite_alerta,
                case when v.limite_alerta is null then 'sin_limite' when m.valor>1.5*v.limite_alerta then 'critica'
                when m.valor>v.limite_alerta then 'advertencia' else 'normal' end
                from medicion m join variable v using(id_variable) join sensor s using(id_sensor)
                join ubicacion u using(id_ubicacion) join distrito d using(id_distrito)
                where v.nombre='pm25' and fecha_hora>='2026-07-01' and fecha_hora<'2026-08-01'
                order by m.valor desc,m.fecha_hora,m.id_sensor limit 20''')
            check('10c: niveles y las 20 mediciones mayores', results['10c'] == base)
            check('10: fronteras de alertas', query(c, 'select fn_nivel_alerta(10,10),fn_nivel_alerta(15,10),fn_nivel_alerta(15.001,10),fn_nivel_alerta(1,null)')[0] == ('normal','advertencia','critica','sin_limite'))

            # Referencia por sensor: agrega en Python para comprobar promedio ponderado.
            by_sensor = query(c, '''select u.id_distrito,v.unidad,count(*),sum(m.valor),min(m.valor),max(m.valor)
                from medicion m join variable v using(id_variable) join sensor s using(id_sensor)
                join ubicacion u using(id_ubicacion) where v.nombre='temperatura'
                and fecha_hora>='2026-07-01' and fecha_hora<'2026-08-01' group by u.id_distrito,v.unidad,m.id_sensor''')
            temp = {}
            for d,unit,n,total,low,high in by_sensor:
                old = temp.get(d,(unit,0,Decimal(0),low,high))
                temp[d]=(unit,old[1]+n,old[2]+total,min(old[3],low),max(old[4],high))
            ok = len(temp)==len(results['11'])
            for d,name,unit,n,avg,low,high in results['11']:
                ref=temp[d]
                ok &= (unit,n,low,high)==(ref[0],ref[1],ref[3],ref[4]) and abs(avg-ref[2]/ref[1]) < Decimal('1e-12') and low<=avg<=high
            check('11: temperatura y promedio ponderado', ok)
            mean=Decimal(len(sensors))/len(districts)
            expected_ids={d for d in districts if district_counts[d]>mean}
            check('12: selección y total anterior al filtro', {r[0] for r in results['12']}==expected_ids and all(r[2]==district_counts[r[0]] and abs(r[3]-mean)<Decimal('1e-12') and r[4]==len(sensors) and r[5]==(Decimal(100)*r[2]/len(sensors)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP) for r in results['12']))
            check('13: umbral estricto', {r[0]:r[2] for r in results['13']} == {d:n for d,n in district_counts.items() if n>15})
            expected_ids={r[0] for r in query(c, "select id_sensor from medicion where fecha_hora<'2026-07-15' except select id_sensor from medicion where fecha_hora>='2026-07-15' and fecha_hora<'2026-09-01'")}
            check('14: historia previa y ausencia en ventana', {r[0] for r in results['14']}==expected_ids and all(r[6]<datetime(2026,7,15) for r in results['14']))
            base=query(c, '''select extract(hour from fecha_hora)::int,v.unidad,count(*),sum(valor)
                from medicion join variable v using(id_variable) where v.nombre='carga'
                and fecha_hora>='2026-07-01' and fecha_hora<'2026-08-01'
                group by extract(hour from fecha_hora),v.unidad''')
            hourly={r[0]:r[1:] for r in base}
            check('15: horas, variable y promedio', len(results['15'])==len(hourly)<=24 and all(0<=r[0]<=23 and r[1]==hourly[r[0]][0] and r[3]==hourly[r[0]][1] and abs(r[2]-hourly[r[0]][2]/hourly[r[0]][1])<Decimal('1e-12') for r in results['15']))
            expected_types={s[2] for s in sensors if s[7]=='Centro'}
            check('16: tipos sin duplicados', {r[3] for r in results['16']}==expected_types and len(results['16'])==len(expected_types))
            direct=query(c, "select id_medicion,id_sensor,fecha_hora,id_variable,valor from medicion where id_sensor='S-00002' and fecha_hora>='2025-03-01' and fecha_hora<'2025-04-01'")
            check('17: mediciones completas y límites del mes', Counter((r[0],r[1],r[2],r[3],r[6]) for r in detail)==Counter(direct) and all(datetime(2025,3,1)<=r[2]<datetime(2025,4,1) for r in detail))
            path=next((repo/'postgres/consultas').glob('17_*.sql'))
            plan=query(c,'EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) '+statements(path)[0])[0][0]
            report['plan_17']=plan
            def nodes(node):
                yield node
                for child in node.get('Plans',[]):
                    yield from nodes(child)
            plan_nodes=list(nodes(plan[0]['Plan']))
            partitions={n['Relation Name'] for n in plan_nodes if n.get('Relation Name','').startswith('medicion')}
            partition_indexes={r[1] for r in report['indices_medicion'] if r[0]=='medicion_2025'}
            indexes=[n['Index Name'] for n in plan_nodes if n.get('Index Name') in partition_indexes]
            check('17: poda a partición 2025', partitions=={'medicion_2025'})
            check('17: acceso mediante índice', bool(indexes), ', '.join(indexes) or 'No se observó acceso por índice; revisar indices_medicion y plan_17, sin forzar el optimizador.')
            c.rollback()

        # Cada error esperado usa una conexión independiente: no aborta otras pruebas.
        errors=[("sensor inexistente","select * from fn_resumen_sensor('__NO_EXISTE__','2025-01-01'::timestamp,'2025-02-01'::timestamp)",'No existe el sensor'),
                ("distrito inexistente","select * from fn_sensores_por_distrito('__NO_EXISTE__')",'No existe el distrito'),
                ("fechas invertidas","select * from fn_resumen_sensor('S-00002','2025-02-01'::timestamp,'2025-01-01'::timestamp)",'Rango de fechas'),
                ("fechas iguales","select * from fn_resumen_sensor('S-00002','2025-01-01'::timestamp,'2025-01-01'::timestamp)",'Rango de fechas'),
                ("fecha nula","select * from fn_resumen_sensor('S-00002',null,'2025-01-01'::timestamp)",'Rango de fechas')]
        for name,sql,message in errors:
            with conectar_pg() as c:
                c.read_only=True
                try:
                    c.execute(sql)
                except psycopg.Error as exc:
                    check('10: error esperado '+name, exc.sqlstate=='P0001' and message in str(exc))
                else:
                    check('10: error esperado '+name,False)
                finally:
                    c.rollback()

        # El único UPDATE queda dentro de una transacción explícita con rollback garantizado.
        with conectar_pg() as c:
            try:
                c.execute('BEGIN ISOLATION LEVEL REPEATABLE READ')
                c.execute("SET LOCAL statement_timeout = '180s'")
                c.execute("SET LOCAL lock_timeout = '5s'")
                before=dict(query(c,'select id_sensor,estado from sensor order by id_sensor'))
                recent={r[0] for r in query(c,"select distinct id_sensor from medicion where fecha_hora>='2026-08-29' and fecha_hora<'2026-09-01'")}
                expected={k:('mantenimiento' if v=='mantenimiento' else 'activo' if k in recent else 'inactivo') for k,v in before.items()}
                c.execute("CALL sp_actualizar_estado_sensores(TIMESTAMP '2026-09-01',72)")
                during=dict(query(c,'select id_sensor,estado from sensor order by id_sensor'))
                check('10d: estados calculados y mantenimiento preservado',during==expected)
                report['estados']={'antes':dict(Counter(before.values())),'durante':dict(Counter(during.values())),'sensores_cambiados':sum(before[k]!=during[k] for k in before)}
            finally:
                c.rollback()
            c.read_only=True
            after=dict(query(c,'select id_sensor,estado from sensor order by id_sensor'))
            check('10d: rollback restaura cada sensor',after==before)
            report['estados']['despues']=dict(Counter(after.values()))
            c.rollback()
    except Exception as exc:
        # Evitar incluir cadenas de conexión en el informe.
        report['error_fatal']=type(exc).__name__ + ': ' + str(exc).split('\n')[0]
        print(report['error_fatal'],flush=True)
    finally:
        report['aprobado']=not report.get('error_fatal') and all(t['ok'] for t in report['comprobaciones']) and len(report['consultas'])==21
        (output/'validacion.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=encode)+'\n',encoding='utf-8')
        if 'plan_17' in report:
            (output/'consulta_17_explain.json').write_text(json.dumps(report['plan_17'],indent=2,default=encode)+'\n',encoding='utf-8')
        print('APROBADO' if report['aprobado'] else 'REVISAR FALLOS',flush=True)
    return 0 if report['aprobado'] else 1


if __name__=='__main__':
    raise SystemExit(main())
