#!/usr/bin/env python3
"""
Birth logic visualization with improved structure, determinism, and CLI options.

Features:
- Type hints and docstrings
- Deterministic runs via seed
- Bounded per-pattern history (deque)
- knowledge_bank stores simple threshold values (ints) rather than mutable Theory objects
- Plots both observations and best-theory thresholds over time
- FuncAnimation assigned to a variable to avoid GC
- Option to save animation (GIF/MP4). MP4 requires ffmpeg; GIF uses PillowWriter.
- CLI flags for steps, seed, max-history, pattern weights, save path/fps.
"""

from collections import deque
import argparse
import random
from typing import Deque, Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.animation import PillowWriter
import sys

# Constants
THRESHOLD_MIN = 1
THRESHOLD_MAX = 100
MUTATION_STEP = 10
DECAY_RATE = 0.9
VALUE_INIT = 1.0
VALUE_MIN_ALIVE = 0.1
LEARN_VALUE_INC = 0.05
EVOLVE_USES = 10
DEFAULT_MAX_HISTORY = 200
DEFAULT_PATTERNS = ["A", "B", "C", "D"]


class Theory:
    """A simple theory represented by a threshold and success/failure counters."""

    def __init__(self, threshold: int) -> None:
        self.threshold: int = threshold
        self.success: int = 1
        self.failure: int = 1

    @property
    def score(self) -> float:
        return self.success / (self.success + self.failure)

    def update(self, observation: int) -> None:
        if observation > self.threshold:
            self.success += 1
        else:
            self.failure += 1

    def mutate(self) -> "Theory":
        delta = random.randint(-MUTATION_STEP, MUTATION_STEP)
        new_threshold = max(THRESHOLD_MIN, min(THRESHOLD_MAX, self.threshold + delta))
        return Theory(new_threshold)


class Birth:
    """Represents a 'birth' with multiple theories and simple life-cycle logic."""

    def __init__(self, pattern: str, inherited_theories: Optional[List[int]] = None) -> None:
        self.pattern = pattern
        self.value: float = VALUE_INIT
        self.age: int = 0
        self.uses: int = 0

        if inherited_theories:
            # inherited_theories is a list of threshold ints
            self.theories: List[Theory] = [Theory(t) for t in inherited_theories]
        else:
            self.theories = [Theory(random.randint(20, 80)) for _ in range(3)]

    def best_theory(self) -> Theory:
        return max(self.theories, key=lambda t: t.score)

    def learn(self, observation: int) -> None:
        self.uses += 1
        for theory in self.theories:
            theory.update(observation)
        self.value += LEARN_VALUE_INC
        if self.uses % EVOLVE_USES == 0:
            self.evolve()

    def evolve(self) -> None:
        # Keep top 2 and add a mutated copy of the best
        self.theories.sort(key=lambda t: t.score, reverse=True)
        survivors = self.theories[:2]
        mutated = survivors[0].mutate()
        self.theories = survivors + [mutated]

    def decay(self) -> None:
        self.age += 1
        self.value *= DECAY_RATE

    def alive(self) -> bool:
        return self.value > VALUE_MIN_ALIVE

    def inherited_knowledge(self) -> List[int]:
        # Return top thresholds (ints) to store in knowledge_bank
        self.theories.sort(key=lambda t: t.score, reverse=True)
        return [t.threshold for t in self.theories[:2]]


class BirthLogicSystem:
    """Manages births, observations, and a knowledge bank."""

    def __init__(
        self,
        seed: Optional[int] = None,
        pattern_weights: Optional[Dict[str, int]] = None,
        max_history_per_pattern: int = DEFAULT_MAX_HISTORY,
        patterns: Optional[List[str]] = None,
    ) -> None:
        if seed is not None:
            random.seed(seed)

        self.patterns = patterns if patterns is not None else DEFAULT_PATTERNS
        # pattern weights for observe_pattern
        if pattern_weights:
            # ensure all patterns exist; default to 1 if missing
            self.pattern_weights = [pattern_weights.get(p, 1) for p in self.patterns]
        else:
            # default biased distribution like original: A x3, B x2, C x1, D x1
            # but allow override through CLI
            default_map = {"A": 3, "B": 2, "C": 1, "D": 1}
            self.pattern_weights = [default_map.get(p, 1) for p in self.patterns]

        self.births: Dict[str, Birth] = {}
        # knowledge_bank maps pattern -> list[int] (thresholds)
        self.knowledge_bank: Dict[str, List[int]] = {}
        # history maps pattern -> deque of (observation, best_threshold)
        self.history: Dict[str, Deque[Tuple[int, int]]] = {
            p: deque(maxlen=max_history_per_pattern) for p in self.patterns
        }
        self.max_history_per_pattern = max_history_per_pattern

    def observe_pattern(self) -> str:
        return random.choices(self.patterns, weights=self.pattern_weights, k=1)[0]

    def observe_value(self, pattern: str) -> int:
        center_map = {"A": 70, "B": 50, "C": 30, "D": 10}
        center = center_map.get(pattern, 50)
        return max(THRESHOLD_MIN, min(THRESHOLD_MAX, center + random.randint(-15, 15)))

    def process(self) -> None:
        pattern = self.observe_pattern()

        if pattern not in self.births:
            inherited = self.knowledge_bank.get(pattern)
            self.births[pattern] = Birth(pattern, inherited)

        observation = self.observe_value(pattern)
        birth = self.births[pattern]
        birth.learn(observation)

        best_threshold = birth.best_theory().threshold
        self.history[pattern].append((observation, best_threshold))

    def decay_all(self) -> None:
        dead: List[str] = []
        for key, birth in list(self.births.items()):
            birth.decay()
            if not birth.alive():
                dead.append(key)

        for key in dead:
            self.knowledge_bank[key] = self.births[key].inherited_knowledge()
            del self.births[key]


def animate(
    system: BirthLogicSystem,
    steps: int = 200,
    save_path: Optional[str] = None,
    fps: int = 10,
) -> None:
    """Run the animation and optionally save it to a file."""
    fig, axs = plt.subplots(2, 2, figsize=(12, 8))
    axs = axs.flatten()
    patterns = system.patterns

    # Pre-configure axes limits and labels once
    for ax, p in zip(axs, patterns):
        ax.set_title(f"Pattern {p}")
        ax.set_ylim(0, 100)
        ax.set_xlim(0, system.max_history_per_pattern)
        ax.set_xlabel("Time (samples)")
        ax.set_ylabel("Value / Threshold")

    lines_obs = [ax.plot([], [], label="observation")[0] for ax in axs]
    lines_thr = [ax.plot([], [], linestyle="--", color="orange", label="best threshold")[0] for ax in axs]
    for ax in axs:
        ax.legend(loc="upper right")

    def update(frame: int) -> None:
        if frame < steps:
            system.process()
            system.decay_all()

        for i, p in enumerate(patterns):
            ax = axs[i]
            pdata = list(system.history[p])
            if pdata:
                ys_obs = [t[0] for t in pdata]
                ys_thr = [t[1] for t in pdata]
                xs = list(range(len(ys_obs)))
                lines_obs[i].set_data(xs, ys_obs)
                lines_thr[i].set_data(xs, ys_thr)
                ax.set_xlim(max(0, len(xs) - system.max_history_per_pattern), max(len(xs), system.max_history_per_pattern))
            else:
                lines_obs[i].set_data([], [])
                lines_thr[i].set_data([], [])

    anim = FuncAnimation(fig, update, frames=steps + 1, interval=100, repeat=False)

    if save_path:
        try:
            if save_path.lower().endswith(".gif"):
                writer = PillowWriter(fps=fps)
                anim.save(save_path, writer=writer)
                print(f"Saved GIF to {save_path}")
            else:
                # MP4: requires ffmpeg available in PATH
                anim.save(save_path, fps=fps)
                print(f"Saved animation to {save_path}")
        except Exception as e:
            print(f"Saving animation failed: {e}", file=sys.stderr)
    else:
        plt.show()


def parse_weights(s: Optional[str], patterns: List[str]) -> Optional[Dict[str, int]]:
    """Parse weight string like 'A:3,B:2,C:1' into dict."""
    if not s:
        return None
    parts = s.split(",")
    result: Dict[str, int] = {}
    for part in parts:
        if ":" in part:
            k, v = part.split(":", 1)
            k = k.strip()
            try:
                result[k] = int(v)
            except ValueError:
                raise argparse.ArgumentTypeError(f"Invalid weight value: {v}")
        else:
            raise argparse.ArgumentTypeError(f"Invalid weight part: {part}")
    # Ensure all patterns have at least weight 1 if missing
    for p in patterns:
        result.setdefault(p, 1)
    return result


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Birth logic visualization")
    parser.add_argument("--steps", type=int, default=200, help="Number of processing steps")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for deterministic runs")
    parser.add_argument("--max-history", type=int, default=DEFAULT_MAX_HISTORY, help="Max history per pattern")
    parser.add_argument("--weights", type=str, default=None, help="Pattern weights, e.g. 'A:3,B:2,C:1,D:1'")
    parser.add_argument("--save", type=str, default=None, help="Path to save animation (GIF/MP4)")
    parser.add_argument("--fps", type=int, default=10, help="Frames per second when saving")
    args = parser.parse_args(argv)

    patterns = DEFAULT_PATTERNS
    weight_map = parse_weights(args.weights, patterns)

    system = BirthLogicSystem(seed=args.seed, pattern_weights=weight_map, max_history_per_pattern=args.max_history, patterns=patterns)
    animate(system, steps=args.steps, save_path=args.save, fps=args.fps)


if __name__ == "__main__":
    main()