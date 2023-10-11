import os
import pickle
import time

import torch
from torch.utils.data import DataLoader
from torch.utils.data import Dataset

import chatlearn
from chatlearn import RLHFEngine
from chatlearn import RLHFTorchModule


class CustomDataset(Dataset):
    def __init__(self, data):
        self.data = data
        self.collate_fn = None

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        return {"query": self.data[idx]}




class PolicyModel(RLHFTorchModule):

    def setup(self):
        time.sleep(0.05)
        # self._iter = 0

    def forward_step(self, data, iteration):
        save_dir = self.rlhf_args.data_checkpoint_path
        fn = f"{save_dir}/data_replica{self.replica_id}_{iteration}"
        if self.rlhf_args.load_data_checkpoint_iteration:
            fn = f"{fn}_{self.rlhf_args.load_data_checkpoint_iteration}"
        fn = f"{fn}.pkl"
        with open(fn, 'wb') as f:
            pickle.dump(data, f)
            print(f"save to {fn}", flush=True)
            # self._iter += 1

        query = data["query"]
        time.sleep(0.1)
        data["policy_out"] = query
        return data

    def build_dataset(self, prompts):
        dataset = CustomDataset(prompts)
        return dataset



class ReferenceModel(RLHFTorchModule):


    def forward_step(self, data, iteration):
        query = data["policy_out"].cuda()
        time.sleep(0.01)
        data["ref_out"] = query
        return data


class RewardModel(RLHFTorchModule):


    def forward_step(self, data, iteration):
        data["reward_out"] = data["ref_out"].cuda()
        time.sleep(0.01)
        return data

class ValueModel(RLHFTorchModule):

    def forward_step(self, data, iteration):
        data["value_out"] = data["policy_out"].cuda() * 3
        time.sleep(0.01)
        return data


class PPOPolicy(RLHFTorchModule):

    def train_step(self, data, train_info):
        num_mb = len(data)
        time.sleep(0.1)
        return num_mb


class PPOValue(RLHFTorchModule):

    def train_step(self, data, train_info):
        num_mb = len(data)
        time.sleep(0.1)
        return num_mb


run = os.environ["RUN_FLAG"]


chatlearn.init()
if run == "resume":
    chatlearn.get_args().rlhf_args.load_data_checkpoint_iteration = 2
chatlearn.get_args().models["policy"].num_device = 2
chatlearn.get_args().models["policy"].generation_batch_size = 4
chatlearn.get_args().rlhf_args.data_checkpoint_path = os.path.join(os.getcwd(), "checkpoint2")
chatlearn.get_args().rlhf_args.save_episode_interval = 1
chatlearn.get_args().rlhf_args.num_ppo_episode = 4
chatlearn.get_args().rlhf_args.train_global_batch_size = 8
chatlearn.get_args().rlhf_args.sample_per_episode = 16
policy = PolicyModel("policy")
reference = ReferenceModel("reference")
reward = RewardModel("reward")
value = ValueModel("value")
ppo_policy = PPOPolicy("ppo_policy")
ppo_value = PPOValue("ppo_value")


engine = RLHFEngine(policy, reference, reward, value, ppo_policy, ppo_value)

data = [torch.Tensor([i]) for i in range(100)]
engine.set_dataset(data)
engine.learn()
if run == "resume":
    assert engine._start_episode == 1
    data = {}
    for fn in os.listdir(chatlearn.get_args().rlhf_args.data_checkpoint_path):
        if not fn.endswith('.pkl'):
            continue

        with open(os.path.join(chatlearn.get_args().rlhf_args.data_checkpoint_path, fn), 'rb') as f:
            data[fn] = pickle.load(f)
    for replica in range(2):
        for i in range(2, 8):
            fn_resume = f"data_replica{replica}_{i}_2.pkl"
            fn = f"data_replica{replica}_{i}.pkl"
            assert (data[fn_resume]['query'] == data[fn]['query']).all()
assert engine.trainer.iteration == 8, engine.trainer.iteration
