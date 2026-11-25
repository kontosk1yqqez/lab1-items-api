"""Unit-тести побудови CronJob контролером DatabaseBackup (без кластера)."""
import copy
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backup-controller"))

from cronjob_spec import adoptable, desired_cronjob, diff, owned_by  # noqa: E402

DB = {
    "apiVersion": "backup.example.com/v1alpha1",
    "kind": "DatabaseBackup",
    "metadata": {"name": "users-db-backup", "namespace": "demo", "uid": "uid-1"},
    "spec": {"schedule": "0 2 * * *", "timeZone": "Etc/UTC",
             "connectionSecretName": "users-db-connection", "backupPVCName": "postgres-backups"},
}


def test_desired_cronjob_fields():
    cj = desired_cronjob(DB, "postgres:16-alpine")
    assert cj["metadata"]["name"] == "users-db-backup"
    assert cj["metadata"]["ownerReferences"][0]["uid"] == "uid-1"
    assert cj["metadata"]["ownerReferences"][0]["controller"] is True
    spec = cj["spec"]
    assert spec["schedule"] == "0 2 * * *"
    assert spec["timeZone"] == "Etc/UTC"
    assert spec["concurrencyPolicy"] == "Forbid"
    pod = spec["jobTemplate"]["spec"]["template"]["spec"]
    c = pod["containers"][0]
    assert c["envFrom"] == [{"secretRef": {"name": "users-db-connection"}}]
    assert c["volumeMounts"][0]["mountPath"] == "/backups"
    assert pod["volumes"][0]["persistentVolumeClaim"]["claimName"] == "postgres-backups"
    script = c["command"][2]
    assert "pg_dump -Fc" in script and ".partial" in script and 'mv "$tmp" "$final"' in script


def test_default_timezone():
    db = copy.deepcopy(DB)
    del db["spec"]["timeZone"]
    assert desired_cronjob(db, "img")["spec"]["timeZone"] == "Etc/UTC"


def test_diff_detects_schedule_change_only():
    actual = desired_cronjob(DB, "postgres:16-alpine")
    assert diff(actual, actual) == []
    db2 = copy.deepcopy(DB)
    db2["spec"]["schedule"] = "*/30 * * * *"
    assert diff(actual, desired_cronjob(db2, "postgres:16-alpine")) == ["schedule"]


def test_ownership():
    cj = desired_cronjob(DB, "img")
    assert owned_by(cj, DB)
    foreign = copy.deepcopy(cj)
    foreign["metadata"]["ownerReferences"][0]["uid"] = "other"
    foreign["metadata"]["labels"] = {}
    assert not owned_by(foreign, DB) and not adoptable(foreign)
    orphan = copy.deepcopy(cj)
    orphan["metadata"]["ownerReferences"] = []
    assert adoptable(orphan)
