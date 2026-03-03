"""Interactive pygame interface for MiniPong."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
import torch

from src.envs.minipong import MiniPongConfig, MiniPongEnv
from src.envs.wrappers import wrap_env
from src.rl.networks import create_q_network

Side = Literal["left", "right"]
Action = int


@dataclass
class GameController:
    left_agent_enabled: bool = False
    right_agent_enabled: bool = False
    debug: bool = False
    checkpoint_path: str = ""

    def toggle_agent(self, side: Side) -> bool:
        if side == "left":
            self.left_agent_enabled = not self.left_agent_enabled
            return self.left_agent_enabled
        self.right_agent_enabled = not self.right_agent_enabled
        return self.right_agent_enabled

    def get_controller(self, side: Side) -> Literal["agent", "human"]:
        enabled = self.left_agent_enabled if side == "left" else self.right_agent_enabled
        return "agent" if enabled else "human"

    def get_status_tag(self, side: Side) -> str:
        if self.get_controller(side) == "agent":
            if not self.debug:
                return "AI Agent"
            policy_name = Path(self.checkpoint_path).name if self.checkpoint_path else "random"
            return f"Policy: {policy_name}"
        if side == "left":
            return "Keyboard: Up:Q, Down:A"
        return "Keyboard: Up:P, Down:L"

    def restart(self) -> None:
        return None


def get_action_from_keys(side: Side, pressed: set[str]) -> Action:
    if side == "left":
        if "q" in pressed:
            return 0
        if "a" in pressed:
            return 1
        return 2
    if "p" in pressed:
        return 0
    if "l" in pressed:
        return 1
    return 2


def prepare_agent_obs(obs: np.ndarray, side: Side) -> np.ndarray:
    if side == "right":
        return np.ascontiguousarray(np.flip(obs, axis=1))
    return obs


class AgentPolicy:
    def __init__(self, obs_shape: tuple[int, int, int], checkpoint: str) -> None:
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.network = create_q_network(obs_shape, 3).to(self.device)
        self.network.eval()
        self.policy_name = "random"

        if checkpoint:
            checkpoint_path = Path(checkpoint)
            data = torch.load(checkpoint_path, map_location=self.device, weights_only=True)
            state = data["model"] if isinstance(data, dict) and "model" in data else data
            self.network.load_state_dict(state)
            self.policy_name = checkpoint_path.name

    def act(self, obs: np.ndarray, noise: float = 0.0) -> int:
        if self.policy_name == "random":
            return int(np.random.randint(3))
        with torch.no_grad():
            obs_tensor = torch.tensor(obs[None], dtype=torch.float32, device=self.device)
            q_values = self.network(obs_tensor)
            # Symmetric Q: average both orientations for side-invariant play
            q_values = (q_values + self.network(obs_tensor.flip(dims=[2]))) / 2
            # Add noise for variety so symmetric agents don't move in perfect lockstep
            if noise > 0:
                q_values = q_values + torch.randn_like(q_values) * noise
            return int(torch.argmax(q_values, dim=1).item())


def _pressed_key_names(pygame: Any) -> set[str]:
    keys = pygame.key.get_pressed()
    pressed: set[str] = set()
    keymap = {
        pygame.K_q: "q",
        pygame.K_a: "a",
        pygame.K_p: "p",
        pygame.K_l: "l",
    }
    for code, name in keymap.items():
        if keys[code]:
            pressed.add(name)
    return pressed


def run_game(
    debug: bool, checkpoint: str, left_agent: bool, right_agent: bool, frame_stack: int = 4
) -> None:
    import pygame

    scale = 6
    header_height = 80
    footer_height = 30
    fps = 30
    agent_noise = 0.05  # small Q-value noise so symmetric agents don't move in lockstep
    action_repeat = 3  # repeat each agent action for N frames to reduce jitter

    raw_env = MiniPongEnv(render_mode="rgb_array", config=MiniPongConfig(score_limit=11))
    env = wrap_env(raw_env, frame_stack=frame_stack) if checkpoint else raw_env
    obs, info = env.reset(seed=0)

    controller = GameController(
        left_agent_enabled=left_agent,
        right_agent_enabled=right_agent,
        debug=debug,
        checkpoint_path=checkpoint,
    )
    policy = AgentPolicy(obs.shape, checkpoint)

    # Action repeat state for smoothing jitter
    left_held_action = 2  # stay
    right_held_action = 2
    left_hold_count = 0
    right_hold_count = 0

    pygame.init()
    window_size = (
        raw_env.config.width * scale,
        raw_env.config.height * scale + header_height + footer_height,
    )
    screen = pygame.display.set_mode(window_size)
    pygame.display.set_caption("MiniPong")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 26)
    small_font = pygame.font.SysFont(None, 22)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    controller.restart()
                    obs, info = env.reset(seed=0)
                elif event.key == pygame.K_a and (event.mod & pygame.KMOD_SHIFT):
                    controller.toggle_agent("left")
                elif event.key == pygame.K_l and (event.mod & pygame.KMOD_SHIFT):
                    controller.toggle_agent("right")

        pressed = _pressed_key_names(pygame)

        left_action = get_action_from_keys("left", pressed)
        if controller.get_controller("left") == "agent":
            if left_hold_count <= 0:
                left_held_action = int(policy.act(
                    prepare_agent_obs(obs, "left"), noise=agent_noise,
                ))
                left_hold_count = action_repeat
            left_action = left_held_action
            left_hold_count -= 1

        right_action = get_action_from_keys("right", pressed)
        if controller.get_controller("right") == "agent":
            if right_hold_count <= 0:
                right_held_action = int(policy.act(
                    prepare_agent_obs(obs, "right"), noise=agent_noise,
                ))
                right_hold_count = action_repeat
            right_action = right_held_action
            right_hold_count -= 1

        raw_env.set_opponent_action(right_action)
        obs, _, terminated, truncated, info = env.step(left_action)
        if terminated or truncated:
            controller.restart()
            obs, info = env.reset(seed=0)

        frame = raw_env.render()
        surface = pygame.surfarray.make_surface(np.transpose(frame, (1, 0, 2)))
        surface = pygame.transform.scale(
            surface, (raw_env.config.width * scale, raw_env.config.height * scale)
        )

        screen.fill((0, 0, 0))
        screen.blit(surface, (0, header_height))

        score_text = f"Left {info['agent_score']} : {info['opponent_score']} Right"
        screen.blit(font.render(score_text, True, (255, 255, 255)), (10, 10))

        left_tag = controller.get_status_tag("left")
        right_tag = controller.get_status_tag("right")
        screen.blit(font.render(left_tag, True, (255, 255, 255)), (10, 42))
        right_surface = font.render(right_tag, True, (255, 255, 255))
        screen.blit(right_surface, (window_size[0] - right_surface.get_width() - 10, 42))

        # Rally length counter at the bottom
        rally = info.get("rally_length", 0)
        rally_text = f"Rally: {rally}"
        rally_surface = small_font.render(rally_text, True, (180, 180, 180))
        rally_x = (window_size[0] - rally_surface.get_width()) // 2
        rally_y = window_size[1] - footer_height + 5
        screen.blit(rally_surface, (rally_x, rally_y))

        pygame.display.flip()
        clock.tick(fps)

    pygame.quit()


def _resolve_run_id(run_id: str) -> str:
    """Resolve a run ID to the latest checkpoint path."""
    checkpoint_dir = Path("artifacts") / run_id / "checkpoints"
    if not checkpoint_dir.is_dir():
        print(f"Error: run directory not found: {checkpoint_dir}", file=sys.stderr)
        sys.exit(1)

    checkpoints = sorted(
        checkpoint_dir.glob("step_*.pt"),
        key=lambda p: int(m.group(1)) if (m := re.search(r"step_(\d+)", p.stem)) else -1,
    )
    if not checkpoints:
        print(f"Error: no checkpoints found in {checkpoint_dir}", file=sys.stderr)
        sys.exit(1)

    return str(checkpoints[-1])


def main() -> None:
    parser = argparse.ArgumentParser(description="Play MiniPong interactively")
    parser.add_argument("--checkpoint", default="", help="Path to trained checkpoint (.pt)")
    parser.add_argument("--run-id", default="", help="Run ID to load latest checkpoint from")
    parser.add_argument("--debug", action="store_true", help="Show policy names in status tags")
    parser.add_argument("--left-agent", action="store_true", help="Start with left side on agent")
    parser.add_argument("--right-agent", action="store_true", help="Start with right side on agent")
    args = parser.parse_args()

    checkpoint: str = args.checkpoint
    if not checkpoint and args.run_id:
        checkpoint = _resolve_run_id(args.run_id)

    run_game(
        debug=args.debug,
        checkpoint=checkpoint,
        left_agent=args.left_agent,
        right_agent=args.right_agent,
    )


if __name__ == "__main__":
    main()
