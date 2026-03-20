"""Простейший обучающийся агент для навигации по 3D мешу.

Модуль не требует PyTorch: используется табличное Q‑обучение и
дискретные действия по сетке меша.
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np


def _infer_grid_shape(mesh) -> Tuple[int, int]:
    """Возвращает (Tn, Fn) для регулярной сетки меша."""
    # Сначала пробуем взять сохраненную метаинформацию
    try:
        if hasattr(mesh, "field_data") and "grid_shape" in mesh.field_data:
            shape = mesh.field_data["grid_shape"].ravel().astype(int)
            if shape.size >= 2 and shape[0] > 0 and shape[1] > 0:
                return int(shape[0]), int(shape[1])
    except Exception:
        pass

    # Падение до вычисления из координат (используются целочисленные x/y)
    xs = np.asarray(mesh.points[:, 0])
    ys = np.asarray(mesh.points[:, 1])
    Tn = int(np.round(xs.max())) + 1
    Fn = int(np.round(ys.max())) + 1
    if Tn <= 0 or Fn <= 0:
        raise ValueError("Не удалось определить размеры сетки меша")
    return Tn, Fn


def _block_mean(arr: np.ndarray, factor: int) -> np.ndarray:
    """Усредняет массив блоками factor x factor."""
    if factor <= 1:
        return arr
    Tn, Fn = arr.shape[:2]
    t_ds = math.ceil(Tn / factor)
    f_ds = math.ceil(Fn / factor)
    out_shape = (t_ds, f_ds) + arr.shape[2:]
    out = np.zeros(out_shape, dtype=float)
    for i in range(t_ds):
        for j in range(f_ds):
            i0, i1 = i * factor, min((i + 1) * factor, Tn)
            j0, j1 = j * factor, min((j + 1) * factor, Fn)
            block = arr[i0:i1, j0:j1]
            out[i, j] = block.mean(axis=(0, 1))
    return out


def extract_height_map(mesh, max_size: int = 96, normalize: bool = True):
    """Преобразует PyVista меш в регулярную высотную карту.

    Args:
        mesh: PyVista PolyData
        max_size: Максимальное число точек по одной оси (с даунсэмплингом)
        normalize: Нормализовать высоты в [0, 1]

    Returns:
        (height_map, meta) где meta содержит:
            - grid_points: усредненные XYZ для каждой клетки
            - original_shape: исходные (Tn, Fn)
            - downsample_factor: использованный фактор даунсэмплинга
            - amplitudes: амплитуды (если есть), приведенные к той же сетке
    """
    Tn, Fn = _infer_grid_shape(mesh)

    grid_points = np.zeros((Tn, Fn, 3), dtype=float)
    index_map = np.full((Tn, Fn), -1, dtype=int)
    for idx, p in enumerate(mesh.points):
        i = int(round(p[0]))
        j = int(round(p[1]))
        if 0 <= i < Tn and 0 <= j < Fn:
            grid_points[i, j] = p
            index_map[i, j] = idx

    heights = grid_points[:, :, 2].copy()

    amps = None
    if "amplitude" in mesh.point_data:
        amp_raw = np.asarray(mesh.point_data["amplitude"])
        if amp_raw.size == Tn * Fn:
            amps = amp_raw.reshape((Tn, Fn))

    # Даунсэмплинг, если сетка слишком большая
    factor = max(1, math.ceil(max(Tn, Fn) / max_size))
    grid_points_ds = _block_mean(grid_points, factor)
    heights_ds = _block_mean(heights, factor)
    amps_ds = _block_mean(amps, factor) if amps is not None else None

    if normalize and amps_ds is not None:
        a_min, a_max = amps_ds.min(), amps_ds.max()
        if a_max - a_min > 1e-9:
            amps_ds = (amps_ds - a_min) / (a_max - a_min + 1e-9)

    if normalize:
        h_min, h_max = heights_ds.min(), heights_ds.max()
        if h_max - h_min > 1e-9:
            heights_ds = (heights_ds - h_min) / (h_max - h_min + 1e-9)

    meta = {
        "grid_points": grid_points_ds,
        "original_shape": (Tn, Fn),
        "downsample_factor": factor,
        "amplitudes": amps_ds,
    }
    return heights_ds, meta


@dataclass
class MeshNavigationEnv:
    """Простая дискретная среда навигации по высотной карте."""

    height_map: np.ndarray
    start: Tuple[int, int]
    goal: Tuple[int, int]
    slope_penalty: float = 0.3
    step_cost: float = 0.01
    goal_reward: float = 2.0
    out_penalty: float = 0.5
    max_steps: Optional[int] = None
    amplitude_map: Optional[np.ndarray] = None
    amplitude_weight: float = 0.0
    slope_hard_limit: Optional[float] = None  # если превышен, считаем стенкой

    def __post_init__(self):
        self.height_map = np.asarray(self.height_map, dtype=float)
        if self.amplitude_map is not None:
            self.amplitude_map = np.asarray(self.amplitude_map, dtype=float)
        self.actions = [
            (-1, 0),
            (1, 0),
            (0, -1),
            (0, 1),
            (-1, -1),
            (-1, 1),
            (1, -1),
            (1, 1),
        ]
        self.n_actions = len(self.actions)
        self.shape = self.height_map.shape
        self.max_steps = self.max_steps or (self.height_map.size * 4)
        self.state = self.start
        self._steps = 0

    def reset(self) -> Tuple[int, int]:
        self.state = self.start
        self._steps = 0
        return self.state

    def _in_bounds(self, i: int, j: int) -> bool:
        return 0 <= i < self.shape[0] and 0 <= j < self.shape[1]

    def step(self, action_idx: int) -> Tuple[Tuple[int, int], float, bool]:
        di, dj = self.actions[action_idx]
        ci, cj = self.state
        ni, nj = ci + di, cj + dj
        reward = -self.step_cost
        done = False

        if not self._in_bounds(ni, nj):
            reward -= self.out_penalty
            ni, nj = ci, cj  # остаемся на месте
        else:
            slope = abs(self.height_map[ni, nj] - self.height_map[ci, cj])
            if self.slope_hard_limit is not None and slope > self.slope_hard_limit:
                reward -= self.out_penalty
                ni, nj = ci, cj
            else:
                reward -= self.slope_penalty * slope
                if self.amplitude_map is not None:
                    reward -= self.amplitude_weight * float(self.amplitude_map[ni, nj])
            if (ni, nj) == self.goal:
                reward += self.goal_reward
                done = True

        self.state = (ni, nj)
        self._steps += 1
        if self._steps >= self.max_steps:
            done = True
        return self.state, reward, done


class MeshQLearningAgent:
    """Табличный Q‑агент для MeshNavigationEnv."""

    def __init__(
        self,
        env: MeshNavigationEnv,
        alpha: float = 0.2,
        gamma: float = 0.97,
        epsilon: float = 0.25,
        epsilon_min: float = 0.02,
        epsilon_decay: float = 0.995,
        seed: Optional[int] = None,
    ):
        self.env = env
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.rng = np.random.default_rng(seed)
        self.Q = np.zeros(env.shape + (env.n_actions,), dtype=np.float32)

    def _select_action(self, state: Tuple[int, int], explore: bool = True) -> int:
        if explore and self.rng.random() < self.epsilon:
            return int(self.rng.integers(self.env.n_actions))
        i, j = state
        return int(np.argmax(self.Q[i, j]))

    def train(
        self,
        episodes: int = 200,
        max_steps: Optional[int] = None,
        progress_cb=None,
        paths_recorder=None,
    ) -> List[Dict]:
        stats: List[Dict] = []
        for ep in range(episodes):
            state = self.env.reset()
            total_reward = 0.0
            max_ep_steps = max_steps or self.env.max_steps
            ep_path = [state]

            for _ in range(max_ep_steps):
                action = self._select_action(state, explore=True)
                next_state, reward, done = self.env.step(action)
                total_reward += reward
                ep_path.append(next_state)

                i, j = state
                ni, nj = next_state
                best_next = 0.0 if done else float(self.Q[ni, nj].max())
                td_target = reward + self.gamma * best_next
                self.Q[i, j, action] += self.alpha * (td_target - self.Q[i, j, action])

                state = next_state
                if done:
                    break

            self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
            ep_stat = {
                "episode": ep + 1,
                "total_reward": total_reward,
                "epsilon": self.epsilon,
            }
            stats.append(ep_stat)
            if paths_recorder:
                try:
                    paths_recorder(ep + 1, list(ep_path))
                except Exception:
                    pass
            if progress_cb:
                try:
                    progress_cb(ep_stat)
                except Exception:
                    pass
        return stats

    def rollout(
        self, max_steps: Optional[int] = None, explore: bool = False
    ) -> Tuple[List[Tuple[int, int]], float, bool]:
        state = self.env.reset()
        path = [state]
        total_reward = 0.0
        reached = False
        max_ep_steps = max_steps or self.env.max_steps

        for _ in range(max_ep_steps):
            action = self._select_action(state, explore=explore)
            state, reward, done = self.env.step(action)
            path.append(state)
            total_reward += reward
            if done:
                reached = state == self.env.goal
                break

        return path, total_reward, reached

