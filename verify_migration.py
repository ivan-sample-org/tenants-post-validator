#!/usr/bin/env python3
import argparse
import csv
import sys
from typing import Dict, List, Optional, Tuple

from pymongo import MongoClient

def parse_args():
    p = argparse.ArgumentParser(description="Verifica migración entity -> provision-state-machine por ambiente y cluster.")
    p.add_argument("--mongo-uri", required=True, help="URI de MongoDB")
    p.add_argument("--db-name", required=True, help="Nombre de la base de datos")
    p.add_argument("--environment", required=True, help="Ambiente (e.g., dev, qa2, prod)")
    p.add_argument("--cluster-index", required=True, help="Cluster index (e.g., 013)")
    p.add_argument("--entity-collection", default="entity", help="Colección origen (default: entity)")
    p.add_argument("--psm-collection", default="provision-state-machine", help="Colección destino (default: provision-state-machine)")
    p.add_argument("--require-user-cluster-match", default="false",
                   help="Si 'true', los users en entity deben tener record.cluster_index == --cluster-index además de environment y tenant")
    p.add_argument("--csv-out", default=None, help="Ruta para CSV de resumen por tenant")
    p.add_argument("--missing-out", default=None, help="Ruta para CSV de users faltantes")
    return p.parse_args()

def bool_arg(val: str) -> bool:
    return str(val).strip().lower() in ("true", "1", "yes", "y")

def main():
    args = parse_args()
    require_user_cluster = bool_arg(args.require_user_cluster_match)

    client = MongoClient(args.mongo_uri)
    db = client[args.db_name]
    entity = db[args.entity_collection]
    psm = db[args.psm_collection]

    env = args.environment
    cluster = args.cluster_index

    # 1) Tenants a migrar desde entity (estado provisioned), por env y cluster
    tenant_q = {
        "record.entity": "tenant",
        "record.environment": env,
        "record.cluster_index": cluster,
        "record.status": "provisioned"
    }
    source_tenants = list(entity.find(tenant_q, {"record.tenant": 1, "record": 1}))
    tenant_ids = [t["record"].get("tenant") for t in source_tenants if t.get("record", {}).get("tenant")]
    tenant_ids = list(dict.fromkeys(tenant_ids))  # unique, preserve order

    if not tenant_ids:
        print(f"[INFO] No hay tenants 'provisioned' en entity para env={env} cluster={cluster}. Nada que verificar.")
        return 0

    print(f"[INFO] Tenants detectados en entity (provisioned) -> {len(tenant_ids)}")

    # 2) Preparar reportes
    summary_rows: List[Dict[str, str]] = []
    missing_rows: List[Dict[str, str]] = []
    errors = 0

    # 3) Por cada tenant, validar existencia en PSM + comparar users
    for tenant_id in tenant_ids:
        # 3a) Verificar tenant en destino (PSM)
        #     Coincidencia primaria por tenant_id; permitimos también ftra_tenant_id como match alterno.
        psm_tenant_q = {
            "entity_type": "tenant",
            "environment": env,
            "cluster_index": cluster,
            "$or": [
                {"tenant_id": tenant_id},
                {"ftra_tenant_id": tenant_id}
            ]
        }
        psm_tenant_doc = psm.find_one(psm_tenant_q, {"_id": 1, "status": 1, "last_activity": 1, "previous_activity": 1})
        tenant_found = psm_tenant_doc is not None

        # 3b) Contar users en entity (sin filtrar por estado)
        user_q = {
            "record.entity": "user",
            "record.environment": env,
            "record.tenant": tenant_id
        }
        if require_user_cluster:
            user_q["record.cluster_index"] = cluster

        source_users = list(entity.find(
            user_q,
            {"record.user": 1, "record.useremail": 1, "record.username": 1, "record": 1}
        ))
        source_user_keys = set()
        for u in source_users:
            rec = u.get("record", {})
            uid = rec.get("user") or rec.get("username")
            uemail = rec.get("useremail")
            # Construimos una clave de emparejamiento preferentemente por user_id, si no por email.
            key = ("id", str(uid)) if uid else ("useremail", str(uemail))
            source_user_keys.add(key)

        # 3c) Contar users en PSM para ese tenant
        psm_user_q = {
            "entity_type": "user",
            "environment": env,
            "tenant_id": tenant_id
        }
        dest_users = list(psm.find(psm_user_q, {"user_id": 1, "user_email": 1}))
        dest_user_keys = set()
        for u in dest_users:
            uid = u.get("user_id")
            uemail = u.get("user_email")
            key = ("id", str(uid)) if uid else ("user_email", str(uemail))
            dest_user_keys.add(key)

        # 3d) Comparaciones
        source_user_count = len(source_user_keys)
        dest_user_count = len(dest_user_keys)
        users_match = (source_user_count == dest_user_count)

        # Users faltantes en destino (presentes en entity y ausentes en PSM)
        missing_in_dest = sorted(list(source_user_keys - dest_user_keys))

        # 3e) Llenar resumen por tenant
        summary_rows.append({
            "environment": env,
            "cluster_index": cluster,
            "tenant_id": tenant_id,
            "tenant_in_psm": "YES" if tenant_found else "NO",
            "entity_users": str(source_user_count),
            "psm_users": str(dest_user_count),
            "users_match": "YES" if users_match else "NO",
        })

        # 3f) Registrar faltantes
        for kind, val in missing_in_dest:
            missing_rows.append({
                "environment": env,
                "cluster_index": cluster,
                "tenant_id": tenant_id,
                "missing_user_key_type": kind,   # 'id' o 'email'
                "missing_user_key_value": val
            })

        # 3g) Errores (para exit code)
        if not tenant_found or not users_match or missing_in_dest:
            errors += 1

        # 3h) Log por tenant
        print(f"\n=== Tenant: {tenant_id} (env={env}, cluster={cluster}) ===")
        print(f"Tenant en PSM: {'OK' if tenant_found else 'FALTA'}")
        print(f"Users -> entity: {source_user_count}  |  psm: {dest_user_count}  |  {'OK' if users_match else 'MISMATCH'}")
        if missing_in_dest:
            print(" - Users faltantes en PSM:")
            for kind, val in missing_in_dest:
                print(f"   * {kind}: {val}")

    # 4) CSVs opcionales
    if args.csv_out:
        with open(args.csv_out, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
            writer.writeheader()
            writer.writerows(summary_rows)
        print(f"\n[INFO] Resumen guardado en: {args.csv_out}")

    if args.missing_out:
        if missing_rows:
            with open(args.missing_out, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(missing_rows[0].keys()))
                writer.writeheader()
                writer.writerows(missing_rows)
            print(f"[INFO] Users faltantes guardados en: {args.missing_out}")
        else:
            # Crear archivo vacío con encabezados por consistencia
            with open(args.missing_out, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["environment","cluster_index","tenant_id","missing_user_key_type","missing_user_key_value"])
                writer.writeheader()
            print(f"[INFO] No hubo faltantes. Archivo creado: {args.missing_out}")

    # 5) Exit code
    if errors:
        print(f"\n[RESULT] Verificación COMPLETADA con discrepancias en {errors} tenant(s). Revisa los detalles arriba.")
        return 2
    else:
        print("\n[RESULT] Verificación OK. Todos los tenants y users migrados coinciden.")
        return 0

if __name__ == "__main__":
    sys.exit(main())
