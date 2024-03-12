import os

# Important: import gym patches before everything
# isort: off

import rl_zoo3.gym_patches  # noqa: F401

# isort: on

from rl_zoo3.utils import (
    ALGOS,
    create_test_env,
    get_latest_run_id,
    get_saved_hyperparams,
    get_trained_models,
    get_wrapper_class,
    linear_schedule,
)

# Read version from file
version_file = os.path.join(os.path.dirname(__file__), "version.txt")
with open(version_file) as file_handler:
    __version__ = file_handler.read().strip()

__all__ = [
    "ALGOS",
    "create_test_env",
    "get_latest_run_id",
    "get_saved_hyperparams",
    "get_trained_models",
    "get_wrapper_class",
    "linear_schedule",
]

import gymnasium as gym

def register(id, *args, **kvargs):
    return gym.envs.registration.register(id, *args, **kvargs)

import sys
sys.path.append(f"{os.environ['TEKKEN_PATH']}/src")
register(
    id='StageTwoTekkenEnv-v1',
    entry_point='simulations.stage_two_tekken_env:StageTwoTekkenEnv',
    max_episode_steps=5000,
    reward_threshold=2000.0
)

register(
    id='StageTwoTekkenEnv-v2',
    entry_point='simulations.stage_two_tekken_env_v2:StageTwoTekkenEnv',
    max_episode_steps=5000,
    reward_threshold=2000.0
)

register(
    id='StageTwoTekkenEnv-v3',
    entry_point='simulations.stage_two_tekken_env_v3:StageTwoTekkenEnv',
    max_episode_steps=5000,
    reward_threshold=2000.0
)

register(
    id='StageTwoTekkenEnv-v4',
    entry_point='simulations.stage_two_tekken_env_v4:StageTwoTekkenEnv',
    max_episode_steps=5000,
    reward_threshold=2000.0
)

register(
    id='StageTwoTekkenEnv-v5',
    entry_point='simulations.stage_two_tekken_env_v5:StageTwoTekkenEnv',
    max_episode_steps=5000,
    reward_threshold=2000.0
)

register(
    id='StageTwoRobotiqEnv-v1',
    entry_point='simulations.stage_two_robotiq_env:StageTwoRobotiqEnv',
    max_episode_steps=5000,
    reward_threshold=2000.0
)

register(
    id='StageThreeTekkenEnv-v1',
    entry_point='simulations.stage_three_tekken_env:StageThreeTekkenEnv',
    max_episode_steps=5000,
    reward_threshold=2000.0
)


register(
    id='StageThreeTekkenEnv-v2',
    entry_point='simulations.stage_three_tekken_env_v2:StageThreeTekkenEnv',
    max_episode_steps=5000,
    reward_threshold=2000.0
)


register(
    id='StageThreeTekkenEnv-v3',
    entry_point='simulations.stage_three_tekken_env_v3:StageThreeTekkenEnv',
    max_episode_steps=5000,
    reward_threshold=2000.0
)

register(
    id='StageThreeTekkenEnv-v4',
    entry_point='simulations.stage_three_tekken_env_v4:StageThreeTekkenEnv',
    max_episode_steps=5000,
    reward_threshold=2000.0
)

register(
    id='StageThreeTekkenEnv-v5',
    entry_point='simulations.stage_three_tekken_env_v5:StageThreeTekkenEnv',
    max_episode_steps=5000,
    reward_threshold=2000.0
)
