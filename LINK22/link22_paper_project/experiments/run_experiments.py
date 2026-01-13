import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from lib.simulation import (
    adaptive_hopset_size,
    kalman_sync,
    simulate_baseline_sync,
    simulate_ber,
    simulate_throughput,
    slot_collision_probability,
)


def load_config(path: Path) -> dict:
    """读取实验配置。"""
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def ensure_dir(path: Path) -> None:
    """确保输出目录存在。"""
    path.mkdir(parents=True, exist_ok=True)


def run_ber_experiment(cfg: dict, rng: np.random.Generator, results_dir: Path) -> None:
    """BER随SNR变化曲线。"""
    snr_db = cfg["snr_db"]
    jammer_occupancy = 0.2
    base_hopset = cfg["hopset_size"]
    adaptive_cfg = cfg["adaptive_hopset"]

    ber_baseline = []
    ber_adaptive = []
    for snr in snr_db:
        baseline = simulate_ber(
            rng,
            snr,
            cfg["num_bits"],
            base_hopset,
            jammer_occupancy,
        )
        adaptive_size = adaptive_hopset_size(
            base_hopset,
            jammer_occupancy,
            adaptive_cfg["min_size"],
            adaptive_cfg["max_size"],
        )
        adaptive = simulate_ber(
            rng,
            snr,
            cfg["num_bits"],
            adaptive_size,
            jammer_occupancy,
        )
        ber_baseline.append(baseline)
        ber_adaptive.append(adaptive)

    data = np.column_stack([snr_db, ber_baseline, ber_adaptive])
    np.savetxt(results_dir / "ber_vs_snr.csv", data, delimiter=",", header="snr_db,baseline,adaptive", comments="")

    plt.figure(figsize=(6, 4))
    plt.semilogy(snr_db, ber_baseline, marker="o", label="Baseline FHSS")
    plt.semilogy(snr_db, ber_adaptive, marker="s", label="Adaptive hopset")
    plt.xlabel("SNR (dB)")
    plt.ylabel("BER")
    plt.grid(True, which="both", linestyle="--", linewidth=0.5)
    plt.legend()
    plt.tight_layout()
    plt.savefig(results_dir / "ber_vs_snr.png", dpi=200)
    plt.savefig(results_dir / "ber_vs_snr.svg")
    plt.close()


def run_throughput_experiment(cfg: dict, rng: np.random.Generator, results_dir: Path) -> None:
    """吞吐/时隙成功率随干扰占用变化曲线。"""
    snr_db = 6
    base_hopset = cfg["hopset_size"]
    adaptive_cfg = cfg["adaptive_hopset"]

    baseline_tp = []
    adaptive_tp = []
    for jammer in cfg["jammer_occupancy"]:
        baseline = simulate_throughput(
            rng,
            cfg["num_nodes"],
            cfg["num_slots"],
            base_hopset,
            jammer,
            snr_db,
        )
        adaptive_size = adaptive_hopset_size(
            base_hopset,
            jammer,
            adaptive_cfg["min_size"],
            adaptive_cfg["max_size"],
        )
        adaptive = simulate_throughput(
            rng,
            cfg["num_nodes"],
            cfg["num_slots"],
            adaptive_size,
            jammer,
            snr_db,
        )
        baseline_tp.append(baseline)
        adaptive_tp.append(adaptive)

    data = np.column_stack([cfg["jammer_occupancy"], baseline_tp, adaptive_tp])
    np.savetxt(
        results_dir / "throughput_vs_jammer.csv",
        data,
        delimiter=",",
        header="jammer_occupancy,baseline,adaptive",
        comments="",
    )

    plt.figure(figsize=(6, 4))
    plt.plot(cfg["jammer_occupancy"], baseline_tp, marker="o", label="Baseline FHSS")
    plt.plot(cfg["jammer_occupancy"], adaptive_tp, marker="s", label="Adaptive hopset")
    plt.xlabel("Jammer occupancy")
    plt.ylabel("Slot success rate")
    plt.grid(True, linestyle="--", linewidth=0.5)
    plt.legend()
    plt.tight_layout()
    plt.savefig(results_dir / "throughput_vs_jammer.png", dpi=200)
    plt.savefig(results_dir / "throughput_vs_jammer.svg")
    plt.close()


def run_sync_experiment(cfg: dict, rng: np.random.Generator, results_dir: Path) -> None:
    """频偏辅助同步的误差与冲突概率评估。"""
    frames = 180
    frame_period_s = 1.0 / cfg["frame_hz"]
    baseline_offset = simulate_baseline_sync(
        rng,
        frames,
        frame_period_s,
        cfg["clock_drift_ppm"],
        cfg["doppler_hz"],
    )
    kalman_offset = kalman_sync(
        rng,
        frames,
        frame_period_s,
        cfg["clock_drift_ppm"],
        cfg["doppler_hz"],
        measurement_noise_ms=0.08,
    )

    baseline_collision = slot_collision_probability(baseline_offset * 1e3, cfg["slot_guard_ms"])
    kalman_collision = slot_collision_probability(kalman_offset * 1e3, cfg["slot_guard_ms"])

    data = np.column_stack([np.arange(frames), baseline_offset, kalman_offset])
    np.savetxt(
        results_dir / "sync_offsets.csv",
        data,
        delimiter=",",
        header="frame,baseline_offset_s,kalman_offset_s",
        comments="",
    )

    summary = (
        "method,collision_probability\n"
        f"baseline,{baseline_collision:.4f}\n"
        f"kalman,{kalman_collision:.4f}\n"
    )
    (results_dir / "sync_collision_summary.csv").write_text(summary, encoding="utf-8")

    plt.figure(figsize=(6, 4))
    plt.plot(baseline_offset * 1e3, label="Baseline")
    plt.plot(kalman_offset * 1e3, label="Frequency-offset aided")
    plt.xlabel("Frame index")
    plt.ylabel("Sync error (ms)")
    plt.grid(True, linestyle="--", linewidth=0.5)
    plt.legend()
    plt.tight_layout()
    plt.savefig(results_dir / "sync_error_vs_time.png", dpi=200)
    plt.savefig(results_dir / "sync_error_vs_time.svg")
    plt.close()


def main() -> None:
    root = Path(__file__).resolve().parent
    cfg = load_config(root / "config.json")
    results_dir = root / "results"
    ensure_dir(results_dir)

    # 固定随机种子以保证可复现
    rng = np.random.default_rng(cfg["random_seed"])
    run_ber_experiment(cfg, rng, results_dir)
    run_throughput_experiment(cfg, rng, results_dir)
    run_sync_experiment(cfg, rng, results_dir)

    # 拷贝图表到论文目录
    figures_dir = root.parent / "paper" / "figures"
    ensure_dir(figures_dir)
    for image in list(results_dir.glob("*.png")) + list(results_dir.glob("*.svg")):
        target = figures_dir / image.name
        target.write_bytes(image.read_bytes())


if __name__ == "__main__":
    main()
