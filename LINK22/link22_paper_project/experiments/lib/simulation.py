import math
import numpy as np


def ber_bpsk_awgn(snr_db: float) -> float:
    """基于AWGN信道的BPSK误码率近似。"""
    snr_linear = 10 ** (snr_db / 10)
    return 0.5 * math.erfc(math.sqrt(snr_linear))


def jammed_ber(snr_db: float, jammer_power_db: float = 10.0) -> float:
    """用等效SNR惩罚模拟干扰造成的误码率提升。"""
    return ber_bpsk_awgn(snr_db - jammer_power_db)


def simulate_ber(
    rng: np.random.Generator,
    snr_db: float,
    num_bits: int,
    hopset_size: int,
    jammer_occupancy: float,
) -> float:
    """仿真在跳频+干扰环境下的BER。"""
    # 为每个比特选择一个跳频通道
    hop_indices = rng.integers(0, hopset_size, size=num_bits)
    # 标记被干扰的通道
    jammer_mask = rng.random(hopset_size) < jammer_occupancy
    jammed = jammer_mask[hop_indices]
    ber_clean = ber_bpsk_awgn(snr_db)
    ber_jammed = jammed_ber(snr_db)
    ber = np.where(jammed, ber_jammed, ber_clean)
    errors = rng.random(num_bits) < ber
    return errors.mean()


def adaptive_hopset_size(
    base_size: int,
    jammer_occupancy: float,
    min_size: int,
    max_size: int,
) -> int:
    """根据干扰占用率调整跳频集大小。"""
    reduction = int((max_size - min_size) * jammer_occupancy)
    return max(min_size, base_size - reduction)


def simulate_throughput(
    rng: np.random.Generator,
    num_nodes: int,
    num_slots: int,
    hopset_size: int,
    jammer_occupancy: float,
    snr_db: float,
) -> float:
    """以每个时隙是否成功解调为指标估计吞吐率。"""
    # 每个时隙的拥有者仅用于保持多用户感知，不直接参与计算
    slot_owner = rng.integers(0, num_nodes, size=num_slots)
    hop_indices = rng.integers(0, hopset_size, size=num_slots)
    jammer_mask = rng.random(hopset_size) < jammer_occupancy
    jammed = jammer_mask[hop_indices]
    ber_clean = ber_bpsk_awgn(snr_db)
    ber_jammed = jammed_ber(snr_db)
    per = np.where(jammed, ber_jammed, ber_clean)
    success = rng.random(num_slots) > per
    return success.mean()


def kalman_sync(
    rng: np.random.Generator,
    frames: int,
    frame_period_s: float,
    clock_drift_ppm: float,
    doppler_hz: float,
    measurement_noise_ms: float,
) -> np.ndarray:
    """基于频偏辅助量测的卡尔曼同步器。"""
    # 漂移模型：ppm换算为每帧累计偏差
    drift_per_frame = clock_drift_ppm * 1e-6 * frame_period_s
    true_offset = 0.0
    est_offset = 0.0
    est_drift = 0.0
    # 协方差矩阵与噪声设置
    p = np.diag([1e-4, 1e-6])
    q = np.diag([1e-6, 1e-9])
    r = measurement_noise_ms ** 2

    offsets = []
    for _ in range(frames):
        # 真实偏差演化：时钟漂移 + 多普勒引起的随机扰动
        true_offset += drift_per_frame
        true_offset += rng.normal(0.0, doppler_hz * 1e-6)

        # 预测步骤
        est_offset += est_drift * frame_period_s
        p = p + q

        # 量测更新：频偏辅助的时间偏差测量
        measurement = true_offset + rng.normal(0.0, measurement_noise_ms)
        h = np.array([1.0, 0.0])
        s = h @ p @ h.T + r
        k = (p @ h.T) / s
        innovation = measurement - est_offset
        est_offset += k[0] * innovation
        est_drift += k[1] * innovation
        p = (np.eye(2) - np.outer(k, h)) @ p

        offsets.append(est_offset)

    return np.array(offsets)


def simulate_baseline_sync(
    rng: np.random.Generator,
    frames: int,
    frame_period_s: float,
    clock_drift_ppm: float,
    doppler_hz: float,
) -> np.ndarray:
    """不进行滤波校正的基线同步误差演化。"""
    drift_per_frame = clock_drift_ppm * 1e-6 * frame_period_s
    true_offset = 0.0
    offsets = []
    for _ in range(frames):
        true_offset += drift_per_frame
        true_offset += rng.normal(0.0, doppler_hz * 1e-6)
        offsets.append(true_offset)
    return np.array(offsets)


def slot_collision_probability(
    sync_error_ms: np.ndarray,
    slot_guard_ms: float,
) -> float:
    """根据守护间隔判断时隙冲突概率。"""
    collisions = np.abs(sync_error_ms) > slot_guard_ms
    return collisions.mean()
