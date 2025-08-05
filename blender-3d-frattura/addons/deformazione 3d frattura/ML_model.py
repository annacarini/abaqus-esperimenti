import os
import re

import csv
import numpy as np
import pandas as pd

from tqdm import tqdm

import torch
from torch import nn
from torch.utils.data import random_split
import torch.optim as optim
import torchvision.models as models
from torch.utils.data import Dataset, DataLoader, random_split
from torch.utils.tensorboard import SummaryWriter
from torch.optim.lr_scheduler import OneCycleLR

from PIL import Image

from torchvision.models import  ResNet18_Weights
import copy
from transformers import ConvNextConfig, ConvNextModel
import math 

from .ML_utils import *


#*********************** CLASSI ML ***********************



class PointsDataset(Dataset):
    def __init__(self, root_dir, transform=None, padding=None, noise=None):
        """
        Args:
            root_dir (str): Root directory containing subfolders, each representing a sample.
            transform (callable, optional): Optional transform to be applied on a sample.
        """
        self.root_dir = root_dir
        self.transform = transform
        self.data = []
        self.sim_info = []
        self.noise = noise
        self.noise_std = 1.0
        try:
            with open(os.path.join(self.root_dir, "Simulations_Info.csv"), newline='') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    index = int(row["INDEX"])
                    completed = row["COMPLETED"].strip().lower() in ["true", "1", "yes"]
                    self.sim_info.append((index, completed))
        except:
            self.sim_info = [(i, True) for i in range(5001)]

        # Iterate over each subfolder in root_dir and load all data
        for subfolder in os.listdir(root_dir):
            subfolder_path = os.path.join(root_dir, subfolder)
            sample_idx = [int(s) for s in re.findall(r'\d+', subfolder)]  # Extract the first number in the subfolder name
            if sample_idx:
                sample_idx = sample_idx[0]
            else:
                continue
           
            completed = next((item[1] for item in self.sim_info if item[0] == sample_idx), None) #completed refers to abaqus simulation stsatus
            if os.path.isdir(subfolder_path) and sample_idx and completed:
                init_coords_circle_file = next((f for f in os.listdir(subfolder_path) if f.endswith('input_coordinates_circle_1.csv')), None)
                before_coords_file = next((f for f in os.listdir(subfolder_path) if f.endswith('input_coordinates_circle_2.csv')), None)
                gt_file = next((f for f in os.listdir(subfolder_path) if f.endswith('output_displacement_external.csv')), None)
                init_coord_plate_file = os.path.join(root_dir,'plate_initial_coordinates.csv')
                # Load ground truth data (displacement external)
                init_coord_plate_data = pd.read_csv(os.path.join(subfolder_path, init_coord_plate_file), skiprows=0, usecols=[1, 2, 3])
                init_coord_plate_data = init_coord_plate_data.to_numpy().flatten()
                init_coord_plate_data = torch.tensor(init_coord_plate_data).float()
                
                if init_coords_circle_file and before_coords_file and gt_file and init_coord_plate_file:

                    #load initial circle data
                    init_coords_circle_data = pd.read_csv(os.path.join(subfolder_path, init_coords_circle_file), skiprows=0, usecols=[1, 2, 3])
                    init_coords_circle_data = init_coords_circle_data.to_numpy()
                    init_coords_circle_data = torch.tensor(init_coords_circle_data).float()

                    #load before_impact circle data
                    before_coords_data = pd.read_csv(os.path.join(subfolder_path, before_coords_file), skiprows=0, usecols=[1, 2, 3])
                    before_coords_data = before_coords_data.to_numpy()
                    before_coords_data = torch.tensor(before_coords_data).float()
                    
                    total_data = torch.cat((init_coords_circle_data,before_coords_data),1)
                    if (padding is not None) and total_data.shape[0]<padding:
                        total_data = zero_pad_tensor(total_data,target_size=padding)
                    #import pdb;pdb.set_trace()
                    gt_data = pd.read_csv(os.path.join(subfolder_path, gt_file), skiprows=0, usecols=[1, 2, 3])
                    gt_data = gt_data.to_numpy().flatten()
                    gt_data = torch.tensor(gt_data).float()

                    class_data = pd.read_csv(os.path.join(subfolder_path, gt_file), skiprows=0, usecols=[4])
                    class_data = class_data.to_numpy().flatten()
                    class_data = torch.tensor(class_data).float()                    

                    # Append the final_image, gt_data, init_coord_plate_data tuple to the data list
                    self.data.append((total_data, gt_data, class_data, init_coord_plate_data))

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        # Retrieve preloaded data
        total_data, gt_data, labels_data, init_coord_plate_data = self.data[idx]

        # Apply transformation if available
        if self.transform:
            total_data = self.transform(total_data)
        if self.noise:
            noise = torch.randn_like(signal) * self.noise_std
            total_data+=noise
        return total_data, gt_data, labels_data, init_coord_plate_data


class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=5000):
        super(PositionalEncoding, self).__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  # Shape: (1, max_len, d_model)
        self.register_buffer('pe', pe)

    def forward(self, x):
        # x shape: (batch_size, seq_len, d_model)
        x = x + self.pe[:, :x.size(1), :]  # Add positional encoding
        return x

class Transformer3DPointsModel(nn.Module):
    def __init__(self, input_dim,input_seq_len, d_model, nhead, num_encoder_layers, dim_feedforward, output_dim, dropout=0.1):
        super(Transformer3DPointsModel, self).__init__()
        self.d_model = d_model
        self.linear_in = nn.Linear(input_dim, d_model)  # Project input to d_model
        self.positional_encoding = PositionalEncoding(d_model)
        self.transformer_encoder = nn.TransformerEncoder(
            nn.TransformerEncoderLayer(d_model, nhead, dim_feedforward, dropout, batch_first=True),
            num_encoder_layers
        )
        self.attention = AttentionLayer(d_model)  # Add attention layer
        #self.linear_out = nn.Linear(d_model, output_dim)  # Map to the desired output size
        self.linear_out = nn.Linear(d_model*input_seq_len, output_dim)  # Map to the desired output size
        self.linear_class = nn.Linear(d_model*input_seq_len, output_dim//3)

    def forward(self, src, src_mask=None):
        
        # src shape: (batch_size, seq_len, input_dim)
        src = self.linear_in(src)  # Project input to d_model
        src = self.positional_encoding(src)  # Add positional encoding
        #memory = self.transformer_encoder(src, src_key_padding_mask=src_mask)  # Pass through transformer encoder
                # memory shape: (batch_size, seq_len, d_model)
        # Zero out padded tokens using src_mask
        if src_mask is not None:
            memory = memory * src_mask.unsqueeze(-1)
            src_key_padding_mask = (src_mask == 0) # Convert 0/1 mask to boolean
            memory = self.transformer_encoder(src, src_key_padding_mask=src_key_padding_mask)
        else:
            memory = self.transformer_encoder(src)
            
        # Apply attention mechanism
        #aggregated = self.attention(memory, src_mask)  # Shape: (batch_size, d_model)

        # Map to the desired output size
        #output = self.linear_out(aggregated)  # Shape: (batch_size, output_dim)

        memory = memory.view(memory.shape[0], -1)  # Shape: (batch_size, d_model, seq_len)
        # Map to the desired output size
        output = self.linear_out(memory)  # Shape: (batch_size, output_dim)
        output_class = self.linear_class(memory)  # Shape: (batch_size, output_dim)        
        return output, output_class

class MLP(nn.Module):
    def __init__(self):
        super(MLP, self).__init__()
        self.fc1 = nn.Linear(in_features=288, out_features=2493, bias=True)
        self.fc2 = nn.Linear(in_features=2493, out_features=1386, bias=True)
        self.fc3 = nn.Linear(in_features=1386, out_features=280, bias=True)
        self.relu = nn.ReLU()
    def forward(self, src, src_mask=None):
        src = src.view(src.shape[0],-1)
        x = self.fc1(self.relu(src))
        x = self.fc2(self.relu(x))
        x = self.fc3(self.relu(x))
        return x