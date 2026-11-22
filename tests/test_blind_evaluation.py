from ziaxen_agent.blind_evaluation import _false_alert_rows


def test_false_alert_location_buckets_can_overlap():
    incident = {
        "start_sim_ns": 110_800_000_000,
        "end_sim_ns": 111_000_000_000,
        "suspected_category": "telemetry health",
        "evidence": [
            {"detector": "health", "rule_or_model": "timestamp_jitter"}
        ],
    }
    event = {
        "start_sim_ns": 100_000_000_000,
        "stop_sim_ns": 110_000_000_000,
    }

    rows, zones = _false_alert_rows(
        [incident], [event], [111_000_000_000], normal_seconds=3600.0
    )

    assert zones["false_incident_count"] == 1
    assert zones["within_1.5s_of_label_boundary"] == 1
    assert zones["at_join_point"] == 1
    assert {row["location"] for row in rows} == {
        "within_1.5s_of_label_boundary",
        "at_join_point",
    }
