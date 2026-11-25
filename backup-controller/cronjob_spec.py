"""Побудова бажаного CronJob для DatabaseBackup і порівняння керованих полів.

Модуль не залежить від клієнта Kubernetes (працює зі звичайними dict), тому його
можна перевіряти unit-тестами без кластера.
"""
from typing import Any

API_VERSION = "backup.example.com/v1alpha1"
KIND = "DatabaseBackup"
MANAGED_BY = "databasebackup-controller"
OWNER_LABEL = "backup.example.com/databasebackup"
DEFAULT_TZ = "Etc/UTC"
BACKUP_DIR = "/backups"

# Команда контейнера: pg_dump -Fc у тимчасовий файл, після успіху — перейменування
# в унікальний *.dump; у разі помилки тимчасовий файл видаляється і повертається код помилки.
BACKUP_SCRIPT = r"""set -eu
ts=$(date -u +%Y%m%dT%H%M%SZ)
final="/backups/${PGDATABASE}-${ts}-${HOSTNAME}.dump"
tmp="${final}.partial"
echo "[backup] pg_dump ${PGDATABASE}@${PGHOST}:${PGPORT} -> ${tmp}"
if pg_dump -Fc --no-password -f "$tmp"; then
  mv "$tmp" "$final"
  echo "[backup] OK: archive ${final} ($(wc -c < "$final") bytes)"
else
  rc=$?
  rm -f "$tmp"
  echo "[backup] FAILED: pg_dump exit code ${rc}" >&2
  exit "$rc"
fi
"""


def owner_reference(db: dict) -> dict:
    meta = db["metadata"]
    return {
        "apiVersion": API_VERSION,
        "kind": KIND,
        "name": meta["name"],
        "uid": meta["uid"],
        "controller": True,
    }


def desired_cronjob(db: dict, backup_image: str) -> dict:
    """Бажаний CronJob (з тим самим ім'ям і namespace, що й DatabaseBackup)."""
    meta, spec = db["metadata"], db["spec"]
    name = meta["name"]
    labels = {"app.kubernetes.io/managed-by": MANAGED_BY, OWNER_LABEL: name}
    return {
        "apiVersion": "batch/v1",
        "kind": "CronJob",
        "metadata": {
            "name": name,
            "namespace": meta["namespace"],
            "labels": labels,
            "ownerReferences": [owner_reference(db)],
        },
        "spec": {
            "schedule": spec["schedule"],
            "timeZone": spec.get("timeZone") or DEFAULT_TZ,
            "concurrencyPolicy": "Forbid",
            "successfulJobsHistoryLimit": 3,
            "failedJobsHistoryLimit": 3,
            "jobTemplate": {
                "metadata": {"labels": labels},
                "spec": {
                    "backoffLimit": 1,
                    "template": {
                        "metadata": {"labels": labels},
                        "spec": {
                            "restartPolicy": "Never",
                            "containers": [{
                                "name": "pg-dump",
                                "image": backup_image,
                                "command": ["/bin/sh", "-c", BACKUP_SCRIPT],
                                "envFrom": [{"secretRef": {"name": spec["connectionSecretName"]}}],
                                "volumeMounts": [{"name": "backups", "mountPath": BACKUP_DIR}],
                            }],
                            "volumes": [{
                                "name": "backups",
                                "persistentVolumeClaim": {"claimName": spec["backupPVCName"]},
                            }],
                        },
                    },
                },
            },
        },
    }


def _get(obj: Any, *path, default=None):
    for p in path:
        if isinstance(obj, dict):
            obj = obj.get(p)
        elif isinstance(obj, list) and isinstance(p, int) and p < len(obj):
            obj = obj[p]
        else:
            return default
        if obj is None:
            return default
    return obj


def managed_fields(cj: dict) -> dict:
    """Поля CronJob, якими керує контролер (для порівняння бажаного й фактичного стану)."""
    pod = _get(cj, "spec", "jobTemplate", "spec", "template", "spec", default={})
    c = _get(pod, "containers", 0, default={})
    return {
        "schedule": _get(cj, "spec", "schedule"),
        "timeZone": _get(cj, "spec", "timeZone"),
        "concurrencyPolicy": _get(cj, "spec", "concurrencyPolicy"),
        "image": c.get("image"),
        "command": c.get("command"),
        "secret": _get(c, "envFrom", 0, "secretRef", "name"),
        "mountPath": _get(c, "volumeMounts", 0, "mountPath"),
        "pvc": _get(pod, "volumes", 0, "persistentVolumeClaim", "claimName"),
        "labels": _get(cj, "metadata", "labels", default={}),
    }


def diff(actual: dict, desired: dict) -> list:
    """Список керованих полів, що відрізняються."""
    a, d = managed_fields(actual), managed_fields(desired)
    out = []
    for key, want in d.items():
        have = a.get(key)
        if key == "labels":
            if any((have or {}).get(k) != v for k, v in want.items()):
                out.append(key)
        elif have != want:
            out.append(key)
    return out


def controller_uid(cj: dict):
    for ref in _get(cj, "metadata", "ownerReferences", default=[]) or []:
        if ref.get("controller"):
            return ref.get("uid")
    return None


def owned_by(cj: dict, db: dict) -> bool:
    return controller_uid(cj) == db["metadata"]["uid"]


def adoptable(cj: dict) -> bool:
    """CronJob з міткою цього контролера, але без власника-контролера (можна прийняти під керування)."""
    return _get(cj, "metadata", "labels", "app.kubernetes.io/managed-by") == MANAGED_BY and controller_uid(cj) is None
