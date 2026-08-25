"""Harder bundled case: overlapping production-incident runbooks.

This is still a closed fixture, but it is constructed so that symptom language
is shared across hypotheses and relevant documents avoid copying the query.
It is the v0.2 *scientific* bundled set.  The astronomy/AI corpus remains the
sanity / CI mechanism test.

It is not a substitute for an external IR collection (BEIR, MS MARCO, etc.).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quasar2.retrieval.base import Document


HYPOTHESES: tuple[dict[str, Any], ...] = (
    {
        "id": "ops.secret_rotation_mismatch",
        "domain": "ops",
        "label": "Secret rotation version skew",
        "description": "Workloads still mount the previous credential generation after a vault or KMS rotation.",
        "anchors": ["vault lease generation", "csi secret volume", "credential version skew"],
        "discriminators": ["old lease", "new secret engine version", "volume generation"],
        "aliases": ["rotated keys", "stale secret", "credential mismatch"],
    },
    {
        "id": "ops.tls_cert_expired",
        "domain": "ops",
        "label": "Expired ingress TLS certificate",
        "description": "The edge certificate expired so clients fail handshake while the service itself is healthy.",
        "anchors": ["certificate notAfter", "ingress tls secret", "handshake failure"],
        "discriminators": ["notAfter in the past", "wrong sans", "cert-manager order"],
        "aliases": ["expired cert", "tls handshake", "browser padlock"],
    },
    {
        "id": "ops.dns_cache_stale",
        "domain": "ops",
        "label": "Stale DNS cache after failover",
        "description": "Clients keep resolving the drained endpoint because TTL or nscd still holds the old A record.",
        "anchors": ["stale a record", "nscd ttl", "coredns cache"],
        "discriminators": ["old cluster ip", "negative cache", "split horizon"],
        "aliases": ["dns after failover", "wrong ip", "stale resolver"],
    },
    {
        "id": "ops.db_connection_pool",
        "domain": "ops",
        "label": "Database connection pool exhaustion",
        "description": "The application waits on a saturated pool so requests time out even though the database is up.",
        "anchors": ["hikari pool", "max connections", "wait timeout"],
        "discriminators": ["active equals max", "idle zero", "pg_stat_activity"],
        "aliases": ["pool exhausted", "cannot get connection", "too many clients"],
    },
    {
        "id": "ops.deploy_bad_canary",
        "domain": "ops",
        "label": "Bad canary taking mixed traffic",
        "description": "A broken replica set is receiving a fraction of live traffic so errors look intermittent.",
        "anchors": ["canary weight", "mesh subset", "partial rollout"],
        "discriminators": ["two versions in endpoints", "header routing", "surge"],
        "aliases": ["bad deploy", "some pods wrong", "intermittent after release"],
    },
    {
        "id": "ops.rate_limit_cascade",
        "domain": "ops",
        "label": "Upstream rate-limit cascade",
        "description": "A shared gateway 429s one caller which retries and saturates remaining callers.",
        "anchors": ["429 too many requests", "retry storm", "shared quota"],
        "discriminators": ["burst multiplier", "token bucket", "retry-after"],
        "aliases": ["throttled api", "rate limited", "retry cascade"],
    },
    {
        "id": "ops.queue_backlog",
        "domain": "ops",
        "label": "Consumer lag on a work queue",
        "description": "Producers succeed but downstream latency grows because consumers cannot drain the queue.",
        "anchors": ["consumer lag", "redis list length", "kafka offset"],
        "discriminators": ["lag increasing", "dlq growth", "consumer cpu"],
        "aliases": ["queue backing up", "messages piling", "worker lag"],
    },
    {
        "id": "ops.oom_restart_loop",
        "domain": "ops",
        "label": "OOMKill restart loop",
        "description": "The process is killed for memory and Kubernetes restarts it, causing periodic 502s.",
        "anchors": ["oomkilled", "lastState terminated", "memory limit"],
        "discriminators": ["restart count", "rss at limit", "evicted"],
        "aliases": ["killed for memory", "crash loop", "pod restarting"],
    },
    {
        "id": "ops.clock_skew_auth",
        "domain": "ops",
        "label": "Clock skew breaking signed auth",
        "description": "Tokens or SigV4 fail because the node clock drifted outside the allowed skew window.",
        "anchors": ["ntp offset", "token nbf", "signature expired"],
        "discriminators": ["chrony offset", "skew seconds", "request time too skewed"],
        "aliases": ["clock drift", "token not yet valid", "time skewed"],
    },
    {
        "id": "ops.feature_flag_split",
        "domain": "ops",
        "label": "Feature flag split-brain",
        "description": "Two flag evaluations disagree across services so only some requests hit the new path.",
        "anchors": ["flag assignment", "bucketing key", "stale sdk cache"],
        "discriminators": ["percentage rollout", "sticky bucketing", "offline eval"],
        "aliases": ["flag inconsistency", "some users new path", "toggle cache"],
    },
    {
        "id": "ops.cdn_cache_poison",
        "domain": "ops",
        "label": "CDN serving a stale error page",
        "description": "The edge cached a 5xx or empty body and keeps serving it after origin recovered.",
        "anchors": ["cache-control s-maxage", "stale-if-error", "surrogate key"],
        "discriminators": ["age header large", "origin 200", "purge required"],
        "aliases": ["cached error", "cdn stale", "edge still failing"],
    },
    {
        "id": "ops.region_failover_lag",
        "domain": "ops",
        "label": "Cross-region replica lag after failover",
        "description": "Reads in the new primary region see outdated rows because replication had not caught up.",
        "anchors": ["replica lag seconds", "gtid executed", "async replication"],
        "discriminators": ["seconds behind source", "read-your-writes fail", "promote too early"],
        "aliases": ["stale reads after failover", "replication delay", "wrong region data"],
    },
)


INTENTS: tuple[dict[str, str], ...] = (
    {
        "id": "ops-01",
        "domain": "ops",
        "q0": "prod started returning 401 after we rotated keys and only some pods fail",
        "correct_hypothesis": "ops.secret_rotation_mismatch",
    },
    {
        "id": "ops-02",
        "domain": "ops",
        "q0": "browsers show a certificate warning and mobile clients cannot handshake",
        "correct_hypothesis": "ops.tls_cert_expired",
    },
    {
        "id": "ops-03",
        "domain": "ops",
        "q0": "after failover some offices still hit the drained cluster ip",
        "correct_hypothesis": "ops.dns_cache_stale",
    },
    {
        "id": "ops-04",
        "domain": "ops",
        "q0": "checkout times out even though the database cpu is idle",
        "correct_hypothesis": "ops.db_connection_pool",
    },
    {
        "id": "ops-05",
        "domain": "ops",
        "q0": "only a fraction of users error after the release and versions look mixed",
        "correct_hypothesis": "ops.deploy_bad_canary",
    },
    {
        "id": "ops-06",
        "domain": "ops",
        "q0": "partner api started throttling us and our retries made it worse",
        "correct_hypothesis": "ops.rate_limit_cascade",
    },
    {
        "id": "ops-07",
        "domain": "ops",
        "q0": "enqueue succeeds but customer emails go out hours late",
        "correct_hypothesis": "ops.queue_backlog",
    },
    {
        "id": "ops-08",
        "domain": "ops",
        "q0": "the api blips 502 every few minutes and the pod keeps restarting",
        "correct_hypothesis": "ops.oom_restart_loop",
    },
    {
        "id": "ops-09",
        "domain": "ops",
        "q0": "signed uploads fail with token not valid yet on one node",
        "correct_hypothesis": "ops.clock_skew_auth",
    },
    {
        "id": "ops-10",
        "domain": "ops",
        "q0": "half the sessions hit the new checkout path and half do not",
        "correct_hypothesis": "ops.feature_flag_split",
    },
    {
        "id": "ops-11",
        "domain": "ops",
        "q0": "origin is healthy now but the public url still serves yesterday's error page",
        "correct_hypothesis": "ops.cdn_cache_poison",
    },
    {
        "id": "ops-12",
        "domain": "ops",
        "q0": "after we promoted the other region users see yesterday's balances",
        "correct_hypothesis": "ops.region_failover_lag",
    },
)


def _doc(
    document_id: str,
    title: str,
    text: str,
    hypothesis_id: str,
    kind: str,
    tags: tuple[str, ...],
) -> Document:
    return Document(
        document_id=document_id,
        domain="ops",
        title=title,
        text=text,
        hypothesis_ids=(hypothesis_id,),
        tags=tags,
        metadata={"kind": kind},
    )


def documents() -> tuple[Document, ...]:
    relevant = (
        _doc(
            "ops-sec-core",
            "CSI volume generation after KMS rotation",
            "The workload identity annotation still pins vault lease generation N. "
            "A new secret engine version is invisible until the replica set rolls and remounts the CSI volume.",
            "ops.secret_rotation_mismatch",
            "core",
            ("lease generation", "csi remount"),
        ),
        _doc(
            "ops-sec-disc",
            "Diagnosing credential version skew",
            "Compare the secret checksum inside the container with the current KMS alias. "
            "HTTP 401 on a subset of pods after rotation is typical of mixed generations, not of an expired edge certificate.",
            "ops.secret_rotation_mismatch",
            "discriminative",
            ("checksum mismatch", "mixed generations"),
        ),
        _doc(
            "ops-tls-core",
            "Ingress notAfter in the past",
            "cert-manager never completed the order. The tls secret notAfter is yesterday. "
            "The deployment itself answers 200 on the pod IP.",
            "ops.tls_cert_expired",
            "core",
            ("notAfter", "cert-manager order"),
        ),
        _doc(
            "ops-tls-disc",
            "Handshake versus application 401",
            "A TLS alert happens before HTTP. Application 401 after a successful handshake is a different class. "
            "Check SAN coverage and the ingress secret, not vault leases.",
            "ops.tls_cert_expired",
            "discriminative",
            ("tls alert", "before http"),
        ),
        _doc(
            "ops-dns-core",
            "nscd and CoreDNS still hold the drained A record",
            "Failover updated the public zone but office resolvers and node nscd honor a long TTL. "
            "Traffic continues to the drained cluster IP.",
            "ops.dns_cache_stale",
            "core",
            ("ttl", "drained cluster ip"),
        ),
        _doc(
            "ops-dns-disc",
            "Split-horizon after promote",
            "dig @8.8.8.8 already shows the new address while workstation nslookup does not. "
            "Flush nscd; do not rotate application secrets.",
            "ops.dns_cache_stale",
            "discriminative",
            ("nslookup mismatch", "flush nscd"),
        ),
        _doc(
            "ops-pool-core",
            "Hikari active equals max while Postgres is idle",
            "Threads block on getConnection. pg_stat_activity shows few backends. "
            "The bottleneck is the application pool, not database CPU.",
            "ops.db_connection_pool",
            "core",
            ("getConnection", "idle postgres"),
        ),
        _doc(
            "ops-pool-disc",
            "Timeouts with idle CPU",
            "Checkout latency tracks pool wait, not query time. Increase maxLifetime leak detection before adding replicas.",
            "ops.db_connection_pool",
            "discriminative",
            ("pool wait", "leak detection"),
        ),
        _doc(
            "ops-canary-core",
            "Mesh subset still sending weight to revision B",
            "Endpoints list two revisions. Canary weight is nonzero. Error rate matches the fraction of traffic on B.",
            "ops.deploy_bad_canary",
            "core",
            ("two revisions", "canary weight"),
        ),
        _doc(
            "ops-canary-disc",
            "Intermittent errors after release",
            "Header-based routing plus a default subset explains why only some users fail. "
            "This is not a secret checksum split across pods.",
            "ops.deploy_bad_canary",
            "discriminative",
            ("header routing", "default subset"),
        ),
        _doc(
            "ops-rl-core",
            "Shared token bucket and retry storm",
            "The partner gateway returns 429 with Retry-After. The client multiplies retries and burns the shared quota for every caller.",
            "ops.rate_limit_cascade",
            "core",
            ("429", "retry-after"),
        ),
        _doc(
            "ops-rl-disc",
            "Throttling versus pool wait",
            "Upstream 429s include a token-bucket header. Database pool wait does not. Back off before scaling consumers.",
            "ops.rate_limit_cascade",
            "discriminative",
            ("token bucket header", "backoff"),
        ),
        _doc(
            "ops-q-core",
            "Kafka consumer lag climbing while produce succeeds",
            "Producer ACKs are fine. Consumer group lag and DLQ depth grow. Email send is gated on the consumer.",
            "ops.queue_backlog",
            "core",
            ("consumer lag", "dlq"),
        ),
        _doc(
            "ops-q-disc",
            "Late side effects with successful enqueue",
            "API latency is normal because enqueue is local. Hours-late mail is drain lag, not CDN cache.",
            "ops.queue_backlog",
            "discriminative",
            ("enqueue local", "drain lag"),
        ),
        _doc(
            "ops-oom-core",
            "OOMKilled and lastState terminated",
            "The container lastState is OOMKilled. restartCount climbs. 502s align with the restart gap.",
            "ops.oom_restart_loop",
            "core",
            ("OOMKilled", "restartCount"),
        ),
        _doc(
            "ops-oom-disc",
            "Periodic 502 with memory limit",
            "RSS sits at the limit then drops to zero. This is not replica lag and not a cached error page.",
            "ops.oom_restart_loop",
            "discriminative",
            ("rss at limit", "restart gap"),
        ),
        _doc(
            "ops-clk-core",
            "chrony offset outside the signing window",
            "Node time is ninety seconds fast. SigV4 and JWT nbf fail only on that node.",
            "ops.clock_skew_auth",
            "core",
            ("chrony offset", "nbf"),
        ),
        _doc(
            "ops-clk-disc",
            "Token not valid yet on one node",
            "The same key works on peers. NTP offset explains not-yet-valid tokens; do not rotate the KMS alias.",
            "ops.clock_skew_auth",
            "discriminative",
            ("one node", "ntp"),
        ),
        _doc(
            "ops-ff-core",
            "Sticky bucketing disagrees across services",
            "Checkout-web and payments-api hash different keys so assignment splits. SDK cache is stale on one side.",
            "ops.feature_flag_split",
            "core",
            ("bucketing key", "sdk cache"),
        ),
        _doc(
            "ops-ff-disc",
            "Half of sessions on the new path",
            "Percentage rollout plus mismatched context keys yields a 50/50 split that is not a canary mesh weight.",
            "ops.feature_flag_split",
            "discriminative",
            ("context key", "percentage rollout"),
        ),
        _doc(
            "ops-cdn-core",
            "Edge Age header still serving a 503 body",
            "Origin now returns 200. The CDN object has a large Age and stale-if-error leftover. Purge the surrogate key.",
            "ops.cdn_cache_poison",
            "core",
            ("Age header", "surrogate key"),
        ),
        _doc(
            "ops-cdn-disc",
            "Public URL stale after origin recovery",
            "curl to origin is fine; curl through the zone is not. This is edge cache, not consumer lag.",
            "ops.cdn_cache_poison",
            "discriminative",
            ("origin 200", "zone 503"),
        ),
        _doc(
            "ops-reg-core",
            "Seconds behind source after promote",
            "The promoted replica had not applied the last GTID. Reads in the new region return yesterday's rows.",
            "ops.region_failover_lag",
            "core",
            ("seconds behind source", "gtid"),
        ),
        _doc(
            "ops-reg-disc",
            "Stale balances after region promote",
            "Write path is on the new primary; read replicas were promoted too early. Flushing DNS will not fix row versions.",
            "ops.region_failover_lag",
            "discriminative",
            ("promote too early", "row versions"),
        ),
    )
    distractors = []
    for index, hypothesis in enumerate(HYPOTHESES):
        hid = str(hypothesis["id"])
        distractors.append(
            _doc(
                f"ops-dist-{index:02d}",
                f"Shared symptom note {index}",
                "Timeouts, 401, 502, deploy, failover, and retries appear in many incidents. "
                "This note lists generic checks: recent release, certificate expiry, DNS ttl, pool size, "
                "rate limits, queue depth, restarts, ntp, flags, cdn purge, and replica lag. "
                f"It is tagged to {hid} only as a weak distractor, not a diagnosis.",
                hid,
                "distractor",
                ("timeout", "401", "502", "deploy", "failover"),
            )
        )
    return relevant + tuple(distractors)


def catalog_payload() -> dict[str, Any]:
    return {"schema_version": "1.0", "hypotheses": list(HYPOTHESES)}


def intents_payload() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "description": "Twelve overlapping on-call intents. q1/q2 are unused; v0.2 applies factorial regimes to q0.",
        "intents": [
            {**item, "q1": item["q0"], "q2": item["q0"]}
            for item in INTENTS
        ],
    }


def write_fixture(root: str | Path) -> None:
    """Materialize inspectable JSON/JSONL under data/ops, isolated from the sanity corpus."""

    base = Path(root) / "data" / "ops"
    catalog_dir = base / "hypotheses_catalog"
    catalog_dir.mkdir(parents=True, exist_ok=True)
    (catalog_dir / "ops.json").write_text(
        json.dumps(catalog_payload(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (base / "intents.json").write_text(
        json.dumps(intents_payload(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    corpus_dir = base / "corpus"
    corpus_dir.mkdir(parents=True, exist_ok=True)
    lines = []
    for document in documents():
        lines.append(
            json.dumps(
                {
                    "id": document.document_id,
                    "domain": document.domain,
                    "title": document.title,
                    "text": document.text,
                    "hypothesis_ids": list(document.hypothesis_ids),
                    "tags": list(document.tags),
                    "metadata": dict(document.metadata),
                },
                ensure_ascii=False,
            )
        )
    (corpus_dir / "ops.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
