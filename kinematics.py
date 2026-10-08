from dataclasses import dataclass
from typing import Dict, Any, Optional
import math


@dataclass
class TrackConfig:
    d1: float = 0.00
    d2: float = 0.50
    d3: float = 1.00

    @property
    def delta_s12(self) -> float:
        return max(0.0, self.d2 - self.d1)

    @property
    def delta_s23(self) -> float:
        return max(0.0, self.d3 - self.d2)

    @property
    def delta_s_total(self) -> float:
        return max(0.0, self.d3 - self.d1)


@dataclass
class KinematicResult:
    run_id: int
    d1: float
    d2: float
    d3: float
    t1: float
    t2: float
    t3: float
    dt12: float
    dt23: float
    dt_total: float
    v12: float
    v23: float
    v_med: float
    acceleration: float
    speed_delta_pct: float
    motion_type: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "Ensaio": self.run_id,
            "S1 (m)": round(self.d1, 3),
            "S2 (m)": round(self.d2, 3),
            "S3 (m)": round(self.d3, 3),
            "T1 (s)": round(self.t1, 4),
            "T2 (s)": round(self.t2, 4),
            "T3 (s)": round(self.t3, 4),
            "Δt₁₂ (s)": round(self.dt12, 4),
            "Δt₂₃ (s)": round(self.dt23, 4),
            "Δt Total (s)": round(self.dt_total, 4),
            "v₁₂ (m/s)": round(self.v12, 3),
            "v₂₃ (m/s)": round(self.v23, 3),
            "v Média (m/s)": round(self.v_med, 3),
            "a (m/s²)": round(self.acceleration, 3),
            "Tipo": self.motion_type
        }


def compute_kinematics(
    t1: float,
    t2: float,
    t3: float,
    config: Optional[TrackConfig] = None,
    run_id: int = 1,
    time_unit: str = "seconds"
) -> KinematicResult:
    if config is None:
        config = TrackConfig()

    if time_unit == "micros":
        t1_s = t1 / 1_000_000.0
        t2_s = t2 / 1_000_000.0
        t3_s = t3 / 1_000_000.0
    elif time_unit == "millis":
        t1_s = t1 / 1_000.0
        t2_s = t2 / 1_000.0
        t3_s = t3 / 1_000.0
    else:
        t1_s = float(t1)
        t2_s = float(t2)
        t3_s = float(t3)

    dt12 = max(0.000001, t2_s - t1_s)
    dt23 = max(0.000001, t3_s - t2_s)
    dt_total = max(0.000001, t3_s - t1_s)

    ds12 = config.delta_s12
    ds23 = config.delta_s23
    ds_tot = config.delta_s_total

    v12 = ds12 / dt12 if dt12 > 0 else 0.0
    v23 = ds23 / dt23 if dt23 > 0 else 0.0
    v_med = ds_tot / dt_total if dt_total > 0 else 0.0

    dt_between_mids = (dt12 + dt23) / 2.0
    acceleration = (v23 - v12) / dt_between_mids if dt_between_mids > 0 else 0.0

    if v12 > 0:
        speed_delta_pct = ((v23 - v12) / v12) * 100.0
    else:
        speed_delta_pct = 0.0

    if abs(speed_delta_pct) < 3.0:
        motion_type = "MRU (Velocidade Quase Constante)"
    elif acceleration > 0:
        motion_type = "MRUV Acelerado (Descida / Tração)"
    else:
        motion_type = "MRUV Retardado (Atrito / Subida)"

    return KinematicResult(
        run_id=run_id,
        d1=config.d1,
        d2=config.d2,
        d3=config.d3,
        t1=t1_s,
        t2=t2_s,
        t3=t3_s,
        dt12=dt12,
        dt23=dt23,
        dt_total=dt_total,
        v12=v12,
        v23=v23,
        v_med=v_med,
        acceleration=acceleration,
        speed_delta_pct=speed_delta_pct,
        motion_type=motion_type
    )
