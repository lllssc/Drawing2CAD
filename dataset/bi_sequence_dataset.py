from torch.utils.data import Dataset, DataLoader
import torch
import os
import json
import h5py
import numpy as np
from config.macro import *

def get_dataloader(phase, config, shuffle=None):
    is_shuffle = phase == 'train' if shuffle is None else shuffle

    dataset = BiSequenceDataset(phase, config)
    dataloader = DataLoader(dataset, batch_size=config.batch_size, shuffle=is_shuffle, num_workers=config.num_workers,
                            worker_init_fn=np.random.seed())
    return dataloader

class BiSequenceDataset(Dataset):
    def __init__(self, phase, config):
        super(BiSequenceDataset, self).__init__()
        self.svg_vec = os.path.join(config.data_root, "svg_vec") # svg_vec data root
        self.cad_vec = os.path.join(config.data_root, "cad_vec") # cad_vec data root
        self.path = os.path.join(config.data_root, "train_val_test_split.json")

        with open(self.path, "r") as fp:
            self.all_data = json.load(fp)[phase]

        self.svg_max_total_len = SVG_MAX_TOTAL_LEN
        self.cad_max_total_len = CAD_MAX_TOTAL_LEN
        
        self.input_option = config.input_option

    def __len__(self):
        return len(self.all_data)
    
    def get_data_by_id(self, data_id):
        idx = self.all_data.index(data_id)
        return self.__getitem__(idx)

    def get_svg_data(self, data_id):
        npy_path = os.path.join(self.svg_vec, data_id + ".npy")
        data = np.load(npy_path)

        # 1x
        if self.input_option == "1x":
            view_vec = data[300:, 0]
            command_vec = data[300:, 1]
            args_vec = data[300:, 2:]
        # 3x
        if self.input_option == "3x":
            view_vec = data[:300, 0]
            command_vec = data[:300, 1]
            args_vec = data[:300, 2:]
        # 4x
        if self.input_option == "4x":
            view_vec = data[:, 0]
            command_vec = data[:, 1]
            args_vec = data[:, 2:]

        view_vec = torch.tensor(view_vec, dtype=torch.long)
        command_vec = torch.tensor(command_vec, dtype=torch.long)
        args_vec = torch.tensor(args_vec, dtype=torch.long)
        
        return {"view": view_vec, "command": command_vec, "args": args_vec}


    def get_cad_data(self, data_id):
        h5_path = os.path.join(self.cad_vec, data_id + ".h5")
        with h5py.File(h5_path, "r") as fp:
            cad_vec = fp["vec"][:] # (len, 1 + N_ARGS)

        pad_len = self.cad_max_total_len - cad_vec.shape[0]
        cad_vec = np.concatenate([cad_vec, CAD_EOS_VEC[np.newaxis].repeat(pad_len, axis=0)], axis=0)

        command = cad_vec[:, 0]
        args = cad_vec[:, 1:]
        command = torch.tensor(command, dtype=torch.long)
        args = torch.tensor(args, dtype=torch.long)
        return {"command": command, "args": args}


    def __getitem__(self, index):
        data_id = self.all_data[index]
        cad_data = self.get_cad_data(data_id)
        svg_data = self.get_svg_data(data_id)

        return {"svg": svg_data, "cad": cad_data, "id": data_id}

