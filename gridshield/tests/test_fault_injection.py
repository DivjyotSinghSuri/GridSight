"""Tests for FaultInjector: determinism, restoration, and each fault type's behaviour."""

import requests
import pytest

from gridshield.fault_injection.faults import Fault
from gridshield.fault_injection.injector import FaultInjector


def test_fault_injector_makes_no_real_network_calls(monkeypatch):
    call_count = {"n": 0}

    def fake_real_get(*args, **kwargs):
        call_count["n"] += 1
        raise AssertionError("real requests.get should never be called while FaultInjector is active")

    monkeypatch.setattr(requests, "get", fake_real_get)

    with FaultInjector(Fault.HTTP_500, probability=1.0, seed=1):
        requests.get("https://example.test", params={"hourly": "temperature_2m"}, timeout=5)

    assert call_count["n"] == 0
    assert requests.get is fake_real_get  # restored to the pre-injector state, not left routed


def test_fault_injector_restores_requests_get_even_on_exception():
    original = requests.get
    with pytest.raises(RuntimeError):
        with FaultInjector(Fault.TIMEOUT, probability=1.0, seed=1):
            raise RuntimeError("boom")
    assert requests.get is original


def test_fault_injector_is_deterministic_for_a_given_seed():
    def run():
        with FaultInjector(Fault.HTTP_500, probability=0.5, seed=99) as injector:
            for _ in range(20):
                requests.get("https://example.test", params={"hourly": "temperature_2m"}, timeout=5)
        return [record.faulted for record in injector.log.records]

    assert run() == run()


def test_http_429_fault_returns_429_status():
    with FaultInjector(Fault.HTTP_429, probability=1.0, seed=1):
        response = requests.get("https://example.test", params={}, timeout=5)
    assert response.status_code == 429


def test_http_500_fault_raises_on_raise_for_status():
    with FaultInjector(Fault.HTTP_500, probability=1.0, seed=1):
        response = requests.get("https://example.test", params={}, timeout=5)
    with pytest.raises(requests.exceptions.HTTPError):
        response.raise_for_status()


def test_timeout_fault_raises_timeout_directly():
    with FaultInjector(Fault.TIMEOUT, probability=1.0, seed=1):
        with pytest.raises(requests.exceptions.Timeout):
            requests.get("https://example.test", params={}, timeout=5)


def test_malformed_json_fault_breaks_json_parsing_but_not_status():
    with FaultInjector(Fault.MALFORMED_JSON, probability=1.0, seed=1):
        response = requests.get("https://example.test", params={"hourly": "temperature_2m"}, timeout=5)
    assert response.status_code == 200
    with pytest.raises(requests.exceptions.JSONDecodeError):
        response.json()


def test_zero_probability_never_injects_a_fault():
    with FaultInjector(Fault.HTTP_500, probability=0.0, seed=1) as injector:
        for _ in range(10):
            requests.get("https://example.test", params={}, timeout=5)
    assert all(not record.faulted for record in injector.log.records)


def test_experiment_log_records_scenario_metadata():
    with FaultInjector(
        Fault.HTTP_429, probability=1.0, seed=5, scenario_id="my_scenario", run_number=3
    ) as injector:
        requests.get("https://example.test", params={}, timeout=5)

    log_dict = injector.log.to_dict()
    assert log_dict["scenario_id"] == "my_scenario"
    assert log_dict["run_number"] == 3
    assert log_dict["seed"] == 5
    assert log_dict["fault_type"] == "http_429"
    assert log_dict["total_calls"] == 1
    assert log_dict["faulted_calls"] == 1
