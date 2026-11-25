"""Контролер DatabaseBackup: підтримує CronJob резервного копіювання PostgreSQL.

* LIST + WATCH ресурсів DatabaseBackup (з resourceVersion списку; після завершення потоку
  спостереження відновлюється, при 410 Gone виконується новий LIST);
* WATCH керованих CronJob (за міткою) — видалений CronJob відновлюється;
* періодична повна звірка (RESYNC_SECONDS);
* черга з дедуплікацією ключів і один обробник — кілька однакових подій не створюють дублікатів.
"""
import logging
import os
import queue
import threading
import time

from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException

from cronjob_spec import MANAGED_BY, adoptable, controller_uid, desired_cronjob, diff, owned_by

GROUP, VERSION, PLURAL = "backup.example.com", "v1alpha1", "databasebackups"
NAMESPACE = os.getenv("WATCH_NAMESPACE", "demo")
RESYNC_SECONDS = int(os.getenv("RESYNC_SECONDS", "60"))
BACKUP_IMAGE = os.getenv("BACKUP_IMAGE", "postgres:16-alpine")
WATCH_TIMEOUT = int(os.getenv("WATCH_TIMEOUT_SECONDS", "300"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s [%(threadName)s] %(message)s")
log = logging.getLogger("controller")


class WorkQueue:
    """Черга ключів namespace/name без повторів: ключ, що вже очікує, не додається вдруге."""

    def __init__(self):
        self._q = queue.Queue()
        self._pending = set()
        self._lock = threading.Lock()

    def add(self, key, reason):
        with self._lock:
            if key in self._pending:
                log.info("skip duplicate %s (%s): already queued", key, reason)
                return
            self._pending.add(key)
        log.info("enqueue %s (%s)", key, reason)
        self._q.put(key)

    def get(self):
        key = self._q.get()
        with self._lock:
            self._pending.discard(key)
        return key


def load_config():
    try:
        config.load_incluster_config()
        log.info("using in-cluster config (ServiceAccount token)")
    except config.ConfigException:
        config.load_kube_config()
        log.info("using local kubeconfig")


class Controller:
    def __init__(self):
        self.api = client.ApiClient()
        self.custom = client.CustomObjectsApi(self.api)
        self.batch = client.BatchV1Api(self.api)
        self.queue = WorkQueue()

    # ---------------------------------------------------------------- спостереження
    def watch_databasebackups(self):
        rv = None
        while True:
            try:
                if rv is None:
                    snapshot = self.custom.list_namespaced_custom_object(GROUP, VERSION, NAMESPACE, PLURAL)
                    rv = snapshot["metadata"]["resourceVersion"]
                    log.info("LIST databasebackups: %d item(s), resourceVersion=%s", len(snapshot["items"]), rv)
                    for item in snapshot["items"]:
                        self.queue.add(f"{NAMESPACE}/{item['metadata']['name']}", "INITIAL")
                stream = watch.Watch()
                for event in stream.stream(self.custom.list_namespaced_custom_object, GROUP, VERSION, NAMESPACE,
                                           PLURAL, resource_version=rv, timeout_seconds=WATCH_TIMEOUT,
                                           allow_watch_bookmarks=True):
                    etype, obj = event["type"], event["object"]
                    if etype == "ERROR":
                        if obj.get("code") == 410:
                            log.warning("WATCH databasebackups: 410 Gone, relist")
                            rv = None
                            break
                        raise RuntimeError(obj)
                    rv = obj["metadata"]["resourceVersion"]
                    if etype in ("ADDED", "MODIFIED", "DELETED"):
                        self.queue.add(f"{NAMESPACE}/{obj['metadata']['name']}", f"{etype} DatabaseBackup")
                if rv is not None:
                    log.info("WATCH databasebackups stream closed, resuming from resourceVersion=%s", rv)
            except ApiException as e:
                if e.status == 410:
                    log.warning("WATCH databasebackups: 410 Gone, relist")
                else:
                    log.error("watch databasebackups failed: %s %s", e.status, e.reason)
                    time.sleep(5)
                rv = None
            except Exception as e:  # noqa: BLE001
                log.error("watch databasebackups error: %s", e)
                rv = None
                time.sleep(5)

    def watch_cronjobs(self):
        selector = f"app.kubernetes.io/managed-by={MANAGED_BY}"
        rv = None
        while True:
            try:
                if rv is None:
                    rv = self.batch.list_namespaced_cron_job(NAMESPACE, label_selector=selector).metadata.resource_version
                stream = watch.Watch()
                for event in stream.stream(self.batch.list_namespaced_cron_job, NAMESPACE, label_selector=selector,
                                           resource_version=rv, timeout_seconds=WATCH_TIMEOUT):
                    etype, obj = event["type"], event["object"]
                    if etype == "ERROR":
                        rv = None
                        break
                    rv = obj.metadata.resource_version
                    if etype in ("MODIFIED", "DELETED"):
                        self.queue.add(f"{NAMESPACE}/{obj.metadata.name}", f"{etype} CronJob")
            except ApiException as e:
                if e.status != 410:
                    log.error("watch cronjobs failed: %s %s", e.status, e.reason)
                    time.sleep(5)
                rv = None
            except Exception as e:  # noqa: BLE001
                log.error("watch cronjobs error: %s", e)
                rv = None
                time.sleep(5)

    def resync(self):
        while True:
            time.sleep(RESYNC_SECONDS)
            try:
                items = self.custom.list_namespaced_custom_object(GROUP, VERSION, NAMESPACE, PLURAL)["items"]
                for item in items:
                    self.queue.add(f"{NAMESPACE}/{item['metadata']['name']}", "RESYNC")
            except Exception as e:  # noqa: BLE001
                log.error("resync failed: %s", e)

    # ---------------------------------------------------------------- звірка
    def reconcile(self, key):
        ns, name = key.split("/", 1)
        try:
            db = self.custom.get_namespaced_custom_object(GROUP, VERSION, ns, PLURAL, name)
        except ApiException as e:
            if e.status == 404:
                log.info("%s: DatabaseBackup not found; its CronJob is removed by the garbage collector "
                         "(ownerReferences)", key)
                return
            raise
        desired = desired_cronjob(db, BACKUP_IMAGE)
        try:
            current = self.batch.read_namespaced_cron_job(name, ns)
        except ApiException as e:
            if e.status != 404:
                raise
            try:
                self.batch.create_namespaced_cron_job(ns, desired)
                log.info("%s: CronJob CREATED (schedule=%r, timeZone=%r, owner uid=%s)", key,
                         desired["spec"]["schedule"], desired["spec"]["timeZone"], db["metadata"]["uid"])
            except ApiException as ce:
                if ce.status == 409:   # з'явився між read і create — звіримо ще раз
                    self.queue.add(key, "409 AlreadyExists")
                else:
                    raise
            return
        actual = self.api.sanitize_for_serialization(current)
        changed = diff(actual, desired)
        if not owned_by(actual, db):
            if adoptable(actual):
                changed.append("ownerReferences")
            else:
                log.warning("%s: CONFLICT - CronJob %s already exists and is not managed by this DatabaseBackup "
                            "(controller uid=%s); skipping", key, name, controller_uid(actual))
                return
        if not changed:
            log.info("%s: CronJob up to date (schedule=%r)", key, desired["spec"]["schedule"])
            return
        patch = {"metadata": {"labels": desired["metadata"]["labels"],
                              "ownerReferences": desired["metadata"]["ownerReferences"]},
                 "spec": desired["spec"]}
        self.batch.patch_namespaced_cron_job(name, ns, patch)
        log.info("%s: CronJob PATCHED, changed: %s (schedule=%r)", key, ", ".join(changed),
                 desired["spec"]["schedule"])

    def worker(self):
        while True:
            key = self.queue.get()
            try:
                self.reconcile(key)
            except Exception as e:  # noqa: BLE001
                log.error("%s: reconcile failed: %s - retry in 10s", key, e)
                threading.Timer(10, self.queue.add, args=(key, "RETRY")).start()

    def run(self):
        log.info("starting: namespace=%s resync=%ss backupImage=%s", NAMESPACE, RESYNC_SECONDS, BACKUP_IMAGE)
        for target, tname in ((self.watch_databasebackups, "watch-dbb"), (self.watch_cronjobs, "watch-cj"),
                              (self.resync, "resync")):
            threading.Thread(target=target, name=tname, daemon=True).start()
        self.worker()


if __name__ == "__main__":
    threading.current_thread().name = "worker"
    load_config()
    Controller().run()
