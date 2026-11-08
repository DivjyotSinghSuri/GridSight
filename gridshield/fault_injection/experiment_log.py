"""Structured, reproducible logging of every fault-injection decision.

Every experiment stores its random seed, fault type, fault probability, run
number, and timestamp per the GridShield methodology. This module captures
that at the finest granularity available: one record per intercepted HTTP
call, which the benchmark engine then aggregates per repetition.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class FaultCallRecord:
    """One intercepted ``requests.get`` call and the fault-injection decision made for it.

    Attributes:
        call_number: 1-based index of this call within the current run.
        timestamp: UTC ISO-8601 timestamp when the call was intercepted.
        source_hint: best-effort label of which GridSight data source the
            call belongs to (``weather``, ``irradiance``, ``daylight``,
            ``generation``, or ``unknown``).
        faulted: whether a fault was injected for this call.
        fault_type: the injected fault's value, or ``None`` if not faulted.
        random_draw: the uniform random draw compared against the
            configured probability to decide whether to fault this call.
    """

    call_number: int
    timestamp: str
    source_hint: str
    faulted: bool
    fault_type: Optional[str]
    random_draw: float


@dataclass
class ExperimentLog:
    """Accumulates :class:`FaultCallRecord` entries for a single scenario repetition.

    Attributes:
        scenario_id: identifier of the scenario this log belongs to.
        run_number: zero-based repetition index.
        seed: the per-repetition seed used to drive fault sampling.
        fault_type: configured fault type for this scenario (or ``None``).
        fault_probability: configured fault probability for this scenario.
        records: the ordered list of intercepted-call records.
    """

    scenario_id: str
    run_number: int
    seed: int
    fault_type: Optional[str]
    fault_probability: float
    records: list = field(default_factory=list)

    def record_call(
        self,
        source_hint: str,
        faulted: bool,
        fault_type: Optional[str],
        random_draw: float,
    ) -> None:
        """Append a new :class:`FaultCallRecord` for the next intercepted call.

        Args:
            source_hint: which GridSight data source this call belongs to.
            faulted: whether a fault was injected.
            fault_type: the fault's value if faulted, else ``None``.
            random_draw: the random draw used for the fault decision.
        """
        self.records.append(
            FaultCallRecord(
                call_number=len(self.records) + 1,
                timestamp=datetime.now(timezone.utc).isoformat(),
                source_hint=source_hint,
                faulted=faulted,
                fault_type=fault_type,
                random_draw=random_draw,
            )
        )

    def to_dict(self) -> dict:
        """Serialize this log, including its header fields and all call records, to a dict."""
        return {
            "scenario_id": self.scenario_id,
            "run_number": self.run_number,
            "seed": self.seed,
            "fault_type": self.fault_type,
            "fault_probability": self.fault_probability,
            "total_calls": len(self.records),
            "faulted_calls": sum(1 for r in self.records if r.faulted),
            "records": [asdict(r) for r in self.records],
        }

    def write_json(self, path: Path) -> None:
        """Write this log as pretty-printed JSON to ``path``, creating parent directories as needed.

        Args:
            path: destination file path.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
