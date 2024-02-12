import argparse
import importlib
import os
import sys
import time

import numpy as np
import torch as th
import yaml
from huggingface_sb3 import EnvironmentName
from stable_baselines3.common.callbacks import tqdm
from stable_baselines3.common.utils import set_random_seed

import rl_zoo3.import_envs  # noqa: F401 pylint: disable=unused-import
from rl_zoo3 import ALGOS, create_test_env, get_saved_hyperparams
from rl_zoo3.exp_manager import ExperimentManager
from rl_zoo3.load_from_hub import download_from_hub
from rl_zoo3.utils import StoreDict, get_model_path


def debug() -> None:  # noqa: C901
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", help="environment ID", type=EnvironmentName, default="CartPole-v1")
    parser.add_argument("-f", "--folder", help="Log folder", type=str, default="rl-trained-agents")
    parser.add_argument("-s", "--save-folder", help="Save folder", type=str, default="/home/deniz.seven/Desktop/Thesis_Documents/replay_buffer")
    parser.add_argument("--algo", help="RL Algorithm", default="ppo", type=str, required=False, choices=list(ALGOS.keys()))
    parser.add_argument("-n", "--n-timesteps", help="number of timesteps", default=1000, type=int)
    parser.add_argument("--num-threads", help="Number of threads for PyTorch (-1 to use default)", default=-1, type=int)
    parser.add_argument("--n-envs", help="number of environments", default=1, type=int)
    parser.add_argument("--exp-id", help="Experiment ID (default: 0: latest, -1: no exp folder)", default=0, type=int)
    parser.add_argument("--verbose", help="Verbose mode (0: no output, 1: INFO)", default=1, type=int)
    parser.add_argument(
        "--no-render", action="store_true", default=False, help="Do not render the environment (useful for tests)"
    )
    parser.add_argument("--deterministic", action="store_true", default=False, help="Use deterministic actions")
    parser.add_argument("--device", help="PyTorch device to be use (ex: cpu, cuda...)", default="auto", type=str)
    parser.add_argument(
        "--load-best", action="store_true", default=False, help="Load best model instead of last model if available"
    )
    parser.add_argument(
        "--load-checkpoint",
        type=int,
        help="Load checkpoint instead of last model if available, "
        "you must pass the number of timesteps corresponding to it",
    )
    parser.add_argument(
        "--load-last-checkpoint",
        action="store_true",
        default=False,
        help="Load last checkpoint instead of last model if available",
    )
    parser.add_argument("--stochastic", action="store_true", default=False, help="Use stochastic actions")
    parser.add_argument(
        "--norm-reward", action="store_true", default=False, help="Normalize reward if applicable (trained with VecNormalize)"
    )
    parser.add_argument("--seed", help="Random generator seed", type=int, default=0)
    parser.add_argument("--reward-log", help="Where to log reward", default="", type=str)
    parser.add_argument(
        "--gym-packages",
        type=str,
        nargs="+",
        default=[],
        help="Additional external Gym environment package modules to import",
    )
    parser.add_argument(
        "--env-kwargs", type=str, nargs="+", action=StoreDict, help="Optional keyword argument to pass to the env constructor"
    )
    parser.add_argument(
        "--custom-objects", action="store_true", default=False, help="Use custom objects to solve loading issues"
    )
    parser.add_argument(
        "-P",
        "--progress",
        action="store_true",
        default=False,
        help="if toggled, display a progress bar using tqdm and rich",
    )
    args = parser.parse_args()

    # Going through custom gym packages to let them register in the global registory
    for env_module in args.gym_packages:
        importlib.import_module(env_module)

    env_name: EnvironmentName = args.env
    algo = args.algo
    folder = args.folder

    try:
        _, model_path, log_path = get_model_path(
            args.exp_id,
            folder,
            algo,
            env_name,
            args.load_best,
            args.load_checkpoint,
            args.load_last_checkpoint,
        )
    except (AssertionError, ValueError) as e:
        # Special case for rl-trained agents
        # auto-download from the hub
        if "rl-trained-agents" not in folder:
            raise e
        else:
            print("Pretrained model not found, trying to download it from sb3 Huggingface hub: https://huggingface.co/sb3")
            # Auto-download
            download_from_hub(
                algo=algo,
                env_name=env_name,
                exp_id=args.exp_id,
                folder=folder,
                organization="sb3",
                repo_name=None,
                force=False,
            )
            # Try again
            _, model_path, log_path = get_model_path(
                args.exp_id,
                folder,
                algo,
                env_name,
                args.load_best,
                args.load_checkpoint,
                args.load_last_checkpoint,
            )

    print(f"Loading {model_path}")

    # Off-policy algorithm only support one env for now
    off_policy_algos = ["qrdqn", "dqn", "ddpg", "sac", "her", "td3", "tqc"]

    if algo in off_policy_algos:
        args.n_envs = 1

    set_random_seed(args.seed)

    if args.num_threads > 0:
        if args.verbose > 1:
            print(f"Setting torch.num_threads to {args.num_threads}")
        th.set_num_threads(args.num_threads)

    is_atari = ExperimentManager.is_atari(env_name.gym_id)
    is_minigrid = ExperimentManager.is_minigrid(env_name.gym_id)

    stats_path = os.path.join(log_path, env_name)
    hyperparams, maybe_stats_path = get_saved_hyperparams(stats_path, norm_reward=args.norm_reward, test_mode=True)

    # load env_kwargs if existing
    env_kwargs = {}
    args_path = os.path.join(log_path, env_name, "args.yml")
    if os.path.isfile(args_path):
        with open(args_path) as f:
            loaded_args = yaml.load(f, Loader=yaml.UnsafeLoader)  # pytype: disable=module-attr
            if loaded_args["env_kwargs"] is not None:
                env_kwargs = loaded_args["env_kwargs"]
    # overwrite with command line arguments
    if args.env_kwargs is not None:
        env_kwargs.update(args.env_kwargs)

    log_dir = args.reward_log if args.reward_log != "" else None

    hyperparams["normalize"] = False
    hyperparams["normalize_kwargs"] = {"norm_obs": False, "norm_reward": False}
    env = create_test_env(
        env_name.gym_id,
        n_envs=args.n_envs,
        stats_path=maybe_stats_path,
        seed=args.seed,
        log_dir=log_dir,
        should_render=not args.no_render,
        hyperparams=hyperparams,
        env_kwargs=env_kwargs,
    )

    kwargs = dict(seed=args.seed)
    if algo in off_policy_algos:
        # Dummy buffer size as we don't need memory to enjoy the trained agent
        kwargs.update(dict(buffer_size=1))
        # Hack due to breaking change in v1.6
        # handle_timeout_termination cannot be at the same time
        # with optimize_memory_usage
        if "optimize_memory_usage" in hyperparams:
            kwargs.update(optimize_memory_usage=False)

    # Check if we are running python 3.8+
    # we need to patch saved model under python 3.6/3.7 to load them
    newer_python_version = sys.version_info.major == 3 and sys.version_info.minor >= 8

    custom_objects = {}
    if newer_python_version or args.custom_objects:
        custom_objects = {
            "learning_rate": 0.0,
            "lr_schedule": lambda _: 0.0,
            "clip_range": lambda _: 0.0,
        }

    if "HerReplayBuffer" in hyperparams.get("replay_buffer_class", ""):
        kwargs["env"] = env

    model = ALGOS[algo].load(model_path, custom_objects=custom_objects, device=args.device, **kwargs)
    old_obs = env.reset()
    import pybullet as p
    import pickle
    from stable_baselines3.her.her_replay_buffer import HerReplayBuffer
    from stable_baselines3.common.buffers import ReplayBuffer
    import numpy as np
    debuger_sim = DebugSimulation(p)

    record_size = 5000
    file_paths = []
    directory_path = '/home/deniz.seven/Desktop/Thesis_Documents/agent_recordings/Stage3_v4'
    for filename in os.listdir(directory_path):
        if filename.endswith(".pkl"):
            file_path = os.path.join(directory_path, filename)
            file_paths.append(file_path)
    
    replay_buffer = HerReplayBuffer(36090, env.observation_space, env.action_space, env)
    plain_replay_buffer = ReplayBuffer(36090, env.observation_space["observation"], env.action_space)# ReplayBuffer(, env.observation_space, env.action_space)
    counter = 0
    for file in file_paths:
        counter +=1 
        print(counter)
        with open(file_path, 'rb') as file:
            loaded_object = pickle.load(file)
            for i in range(loaded_object.pos):
                replay_buffer.add(
                    {
                        "observation": loaded_object.observations["observation"][i],
                        "achieved_goal": loaded_object.observations["achieved_goal"][i],
                        "desired_goal": loaded_object.observations["desired_goal"][i],
                    },
                    {
                        "observation": loaded_object.next_observations["observation"][i],
                        "achieved_goal": loaded_object.next_observations["achieved_goal"][i],
                        "desired_goal": loaded_object.next_observations["desired_goal"][i],
                    },
                    loaded_object.actions[i],
                    loaded_object.rewards[i],
                    loaded_object.dones[i],
                    loaded_object.infos[i]
                )
                plain_replay_buffer.add(
                    loaded_object.observations["observation"][i],
                    loaded_object.next_observations["observation"][i],
                    loaded_object.actions[i],
                    loaded_object.rewards[i],
                    loaded_object.dones[i],
                    loaded_object.infos[i]
                )
    save_path = f"/home/deniz.seven/Desktop/Thesis_Documents/agent_recordings/Stage3_v4/replay_buffer_40.pkl"
    with open(save_path, 'wb') as f:
        pickle.dump(replay_buffer, f)

    save_path = f"/home/deniz.seven/Desktop/Thesis_Documents/agent_recordings/Stage3_v4/plain_replay_buffer_40.pkl"
    with open(save_path, 'wb') as f:
        pickle.dump(plain_replay_buffer, f)

   

import time
class DebugSimulation():
    """TODO add docstring"""

    def __init__(self, physics_engine):
        """TODO add docstring"""
        limit = 1
        self._physics_engine = physics_engine
        self.reset_button = physics_engine.addUserDebugParameter("reset", 1, 0, 1)
        self.latest_reset = self._physics_engine.readUserDebugParameter(
            self.reset_button
        )
        self.hand_pose = []
        self.latest_finger_contacts = np.zeros(5)
        self.hand_pose.append(
            physics_engine.addUserDebugParameter("posX", -limit, limit, 0)
        )
        self.hand_pose.append(
            physics_engine.addUserDebugParameter("posY", -limit, limit, 0)
        )
        self.hand_pose.append(
            physics_engine.addUserDebugParameter("posZ", -limit, limit, 0)
        )
        self.hand_orientation = []
        self.hand_orientation.append(
            physics_engine.addUserDebugParameter("roll", -limit, limit, 0)
        )
        self.hand_orientation.append(
            physics_engine.addUserDebugParameter("pitch", -limit, limit, 0)
        )
        self.hand_orientation.append(
            physics_engine.addUserDebugParameter("yaw", -limit, limit, 0)
        )

        self.grasp_angles = []
        for i in range(2):
            self.grasp_angles.append(
                physics_engine.addUserDebugParameter(
                    f"grasp_angle_{i}", -1.0, 1.0, 0
                )
            )
       

    def get_current_grasp_angles(self):
        grasp_angles = []
        for i in range(len(self.grasp_angles)):
            grasp_angles.append(self._physics_engine.readUserDebugParameter(self.grasp_angles[i]))
        return grasp_angles
    
    def simulate(self):
        """TODO add docstring"""
        while True:
            self.step()
            self._physics_engine.stepSimulation()
            # self._table_workspace.step()
            time.sleep(1.0 / 240.0)

    def step(self):
        """TODO add docstring"""
        if (
            self._physics_engine.readUserDebugParameter(self.reset_button)
            > self.latest_reset
        ):
            self.latest_reset = self._physics_engine.readUserDebugParameter(
                self.reset_button
            )
            self.reset()

        target_pose = []
        target_orientation = []
        for pose in self.hand_pose:
            target_pose.append(self._physics_engine.readUserDebugParameter(pose))
        for orientation in self.hand_orientation:
            target_orientation.append(
                self._physics_engine.readUserDebugParameter(orientation)
            )
        
        action = []
        action.extend(target_pose[0:3])
        action.extend([target_orientation[0]])
        action.extend(self.get_current_grasp_angles())
        return action

if __name__ == "__main__":
    debug()