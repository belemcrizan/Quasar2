import json
from dataclasses import replace
import pytest
from quasar2.v03.acquisition import BoundedClient, sync, validate_nasa, NASA_COLUMNS
from quasar2.v03.annotations import agreement
from quasar2.v03.contracts import Action, Costs, IntegrityError, Outcome, reject_hidden
from quasar2.v03.datasets import (
    synthetic_cases,
    save_cases,
    load_cases,
    BEIRDataset,
    build_ir_cases,
)
from quasar2.v03.gate import RStarEstimator
from quasar2.v03.leakage import audit, require_clean
from quasar2.v03.metrics import classification, paired_interval, risk_coverage
from quasar2.v03.registry import digest, register, validate_run, safe_path
from quasar2.v03.runner import evaluate
from quasar2.v03.utility import Utility, require_extra_budget


@pytest.fixture(scope="module")
def cases():
    return synthetic_cases(180)[0]


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf"), True, 1.5])
def test_invalid_count(value):
    with pytest.raises(IntegrityError):
        Costs(retrieval_calls=value)


def test_nested_hidden_and_cycles():
    cycle = []
    cycle.append(cycle)
    reject_hidden(cycle)
    with pytest.raises(IntegrityError):
        reject_hidden({"observations": ([{"gold": 1}],)})


def test_state_immutable(cases):
    with pytest.raises(TypeError):
        cases[0].state.features["entropy"] = 1


def test_analyze_total_costs(cases):
    case = cases[0]
    good = Outcome(Action.ANALYZE, True, case.stop.costs, case.state.evidence_ids)
    replace(case, additional=good)
    with pytest.raises(IntegrityError):
        replace(case, additional=replace(good, costs=Costs(retrieval_calls=2)))


def test_budget_is_total(cases):
    c = cases[0]
    require_extra_budget(c.stop, c.additional)
    with pytest.raises(ValueError):
        require_extra_budget(c.additional, c.stop)
    with pytest.raises(ValueError):
        require_extra_budget(replace(c.stop, costs=Costs(model_calls=1)), c.additional)


def test_leakage_groups_and_queries(cases):
    c = cases[0]
    report = audit(
        [c, replace(c, query_id="other", split="test" if c.split != "test" else "train")]
    )
    with pytest.raises(IntegrityError):
        require_clean(report)


def test_no_test_training(cases):
    with pytest.raises(IntegrityError):
        RStarEstimator().fit(cases, Utility())


def test_gate_roundtrip_and_tampering(cases):
    m = RStarEstimator().fit([c for c in cases if c.split == "train"], Utility())
    p = m.to_dict()
    assert RStarEstimator.from_dict(p).probability(cases[0].state) == m.probability(cases[0].state)
    p["weights"][0] += 1
    with pytest.raises(IntegrityError):
        RStarEstimator.from_dict(p)


def test_calibration_roles(cases):
    m = RStarEstimator().fit([c for c in cases if c.split == "train"], Utility())
    with pytest.raises(IntegrityError):
        m.calibrate([c for c in cases if c.split == "test"], Utility())
    with pytest.raises(IntegrityError):
        m.tune([c for c in cases if c.split == "test"], Utility())


def test_tied_classification_and_risk():
    m = classification([0.5, 0.5], [0, 1])
    assert m["auroc"] == 0.5 and m["auprc"] == 0.5
    assert risk_coverage([0.5, 0.5], [False, True]) == [{"n": 2, "coverage": 1, "risk": 0.5}]
    assert classification([0.5], [0])["auroc"] is None


def test_cluster_ci():
    r = paired_interval([2, 2], [1, 1], ["same", "same"], samples=20)
    assert r["ci_low"] == r["ci_high"] == 1 and r["n_clusters"] == 1
    with pytest.raises(IntegrityError):
        paired_interval([1], [], ["a"])


def test_registry_immutable_and_tamper(tmp_path):
    kwargs = dict(
        dataset_hash=digest("data"),
        config_hash=digest("config"),
        preregistration_hash=digest("protocol"),
        seed=42,
    )
    a = register(tmp_path, {"metrics.json": {"n": 1}}, **kwargs)
    b = register(tmp_path, {"metrics.json": {"n": 1}}, **kwargs)
    assert a != b and validate_run(a)["status"] == "COMPLETE"
    (a / "metrics.json").write_text("{}")
    with pytest.raises(IntegrityError):
        validate_run(a)


@pytest.mark.parametrize("name", ["../outside", "/absolute", "a/../../b"])
def test_safe_paths(tmp_path, name):
    with pytest.raises(IntegrityError):
        safe_path(tmp_path, name)


def test_dataset_hash(tmp_path, cases):
    p = tmp_path / "cases.json"
    save_cases(p, cases, {"provenance": "SYNTHETIC"})
    assert len(load_cases(p)[0]) == len(cases)
    row = json.loads(p.read_text())
    row["cases"][0]["query"] = "tampered"
    p.write_text(json.dumps(row))
    with pytest.raises(IntegrityError):
        load_cases(p)


def test_dry_run_no_network(tmp_path):
    class NoNetwork:
        def fetch(self, url):
            raise AssertionError("Unexpected network")

    p = tmp_path / "unused"
    assert sync("scifact", p, dry_run=True, client=NoNetwork())["status"] == "DRY_RUN"
    assert not p.exists()


def test_client_size_bound():
    import io

    client = BoundedClient(max_bytes=2, interval=0, opener=lambda *a, **k: io.BytesIO(b"abc"))
    with pytest.raises(IntegrityError):
        client.fetch("https://example.org")
    with pytest.raises(IntegrityError):
        client.fetch("http://example.org")


def test_nasa_schema():
    row = dict.fromkeys(NASA_COLUMNS, "")
    row.update(pl_name="planet", hostname="host", disc_year="2020")
    assert validate_nasa([row])["rows"] == 1
    with pytest.raises(IntegrityError):
        validate_nasa([row, row])
    with pytest.raises(IntegrityError):
        validate_nasa([{**row, "pl_rade": "nan"}])


def test_beir_fixture(tmp_path):
    (tmp_path / "corpus.jsonl").write_text(
        json.dumps({"_id": "d", "title": "planet", "text": "orbit"}) + "\n"
    )
    (tmp_path / "queries.jsonl").write_text(json.dumps({"_id": "q", "text": "planet"}) + "\n")
    (tmp_path / "qrels").mkdir()
    (tmp_path / "qrels/test.tsv").write_text("query-id\tcorpus-id\tscore\nq\td\t1\n")
    ds = BEIRDataset(tmp_path, verify=False)
    cases, meta = build_ir_cases(ds)
    assert cases[0].split == "test" and cases[0].stop.correct
    assert meta["query_provenance"] == "FIXTURE"


def test_budget_matched_and_no_test_fit(cases):
    report, models, predictions, leaks = evaluate(cases, samples=20)
    rows = {r["policy"]: r for r in report["policies"]}
    k = rows["rstar_full"]["additional_calls"]
    assert all(r["additional_calls"] == k for name, r in rows.items() if "matched" in name)
    test_ids = {c.query_id for c in cases if c.split == "test"}
    assert all(
        not test_ids.intersection(m["training_ids"] + m["calibration_ids"] + m["development_ids"])
        for m in models.values()
    )
    assert len(predictions) == len(test_ids)


def test_humans_not_fabricated():
    row = {
        "query_id": "q",
        "annotator_id": "a",
        "provenance": "FIXTURE",
        "acceptable_answers": ["x"],
        "abstain": False,
        "rationale": "fixture",
    }
    with pytest.raises(IntegrityError):
        agreement([row], [{**row, "annotator_id": "b"}])


def test_open_set_control(cases):
    assert all(not c.stop.correct and not c.additional.correct for c in cases if c.open_set)


def test_agent_reserves_before_call(tmp_path, cases):
    from quasar2.v03.agent import ModelOutput, execute

    class Fake:
        calls = 0

        def complete(self, request):
            self.calls += 1
            return ModelOutput("fixture", Costs(model_calls=1, input_tokens=3, output_tokens=1))

    fake = Fake()
    state = cases[0].state
    kwargs = dict(
        query="query",
        state=state,
        evidence={key: "evidence" for key in state.evidence_ids},
        provider="FIXTURE",
        model_id="fixture",
        revision="1",
        prompt="fixture",
        output=tmp_path,
    )
    execute(fake, **kwargs)
    with pytest.raises(FileExistsError):
        execute(fake, **kwargs)
    assert fake.calls == 1


def test_compressed_dataset(tmp_path, cases):
    import gzip

    p = tmp_path / "data.json"
    save_cases(p, cases, {})
    gz = tmp_path / "data.json.gz"
    gz.write_bytes(gzip.compress(p.read_bytes()))
    assert load_cases(gz)[2] == load_cases(p)[2]


@pytest.mark.parametrize(
    "kwargs",
    [{"timeout": float("nan")}, {"interval": float("inf")}, {"retries": 1.5}, {"max_bytes": True}],
)
def test_acquisition_invalid_bounds(kwargs):
    with pytest.raises(ValueError):
        BoundedClient(**kwargs)
