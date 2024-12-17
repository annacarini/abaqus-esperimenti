import os
import pandas as pd
import numpy as np
import json
from torch.utils.data import Dataset
import torch

class DisplacementDataset(Dataset):
    def __init__(self, root_dir, transform=None, inputs_mean=None, inputs_std=None, gt_mean=None, gt_std=None):
        """
        Args:
            root_dir (str): Path to the root directory containing subfolders with data samples.
            transform (callable, optional): Optional transform to be applied on a sample.
        """
        self.root_dir = root_dir
        self.transform = transform
        self.inputs, self.gt = self._load_all_samples()
        # Normalize the features
        self.inputs, self.inputs_mean, self.inputs_std = self._normalize_features(self.inputs,inputs_mean,inputs_std)
        self.gt, self.gt_mean, self.gt_std = self._normalize_features(self.gt,gt_mean,gt_std )

   
    def _load_all_samples(self):
        """
        Parses the root folder, loads CSV and JSON files, and combines them into samples.

        Returns:
            list: List of dictionaries containing inputs and ground truths for each sample.
        """
        inputs = []
        gt = []
        for subfolder in sorted(os.listdir(self.root_dir)):
            subfolder_path = os.path.join(self.root_dir, subfolder)
            if os.path.isdir(subfolder_path):
                for file_name in os.listdir(subfolder_path):
                    if file_name.endswith("_output_displacement_external.csv"):
                        # Extract index from the filename
                        index = file_name.split("_")[0]
                        csv_path = os.path.join(subfolder_path, file_name)
                        json_path = os.path.join(subfolder_path, f"Dynamic_Simulation_{index}_input.json")

                        # Load CSV (ground truth)
                        ground_truth = pd.read_csv(csv_path).values

                        # Load JSON (input features)
                        with open(json_path, "r") as f:
                            input_features = json.load(f)
                        
                        # Store the sample
                        inputs.append(np.array([
                                input_features["circle_speed_x"],
                                input_features["circle_speed_y"],
                                input_features["circle_impact_angle"]
                            ], dtype=np.float32))
                        gt.append(ground_truth.flatten().astype(np.float32))

        return inputs, gt
    def _normalize_features(self, features, mean=None, std=None):
        """
        Normalizes features to have zero mean and unit variance.

        Args:
            features (list of numpy.ndarray): List of feature arrays.

        Returns:
            tuple: (normalized_features, mean, std) where:
                - normalized_features is the list of normalized arrays,
                - mean is the mean value of each feature across the dataset,
                - std is the standard deviation of each feature across the dataset.
        """
        # Stack features into a single array for mean and std calculation
        stacked_features = np.vstack(features)
        if mean is None:
            mean = stacked_features.mean(axis=0) 
        if std is None:
            std = stacked_features.std(axis=0)


        # Avoid division by zero in case of zero standard deviation
        std[std == 0] = 1.0
        # Normalize each feature
        normalized_features = [(f - mean) / std for f in features]

        return normalized_features, mean, std
    def _unnormalize_features(self, normalized_features, mean, std):

        """
        Unnormalizes features to restore the original scale.

        Args:
            normalized_features (list of numpy.ndarray or torch.Tensor): Normalized feature arrays or tensor batch.
            mean (numpy.ndarray or torch.Tensor): Mean values used during normalization.
            std (numpy.ndarray or torch.Tensor): Standard deviation values used during normalization.

        Returns:
            list or torch.Tensor: Unnormalized features as the same type as the input.
        """
        # Convert mean and std to PyTorch tensors if the input is a tensor
        if isinstance(normalized_features, torch.Tensor):
            mean = torch.tensor(mean, dtype=normalized_features.dtype, device=normalized_features.device)
            std = torch.tensor(std, dtype=normalized_features.dtype, device=normalized_features.device)
            
            # Broadcast mean and std for unnormalization
            unnormalized_features = normalized_features * std + mean

        elif isinstance(normalized_features, list):
            # Handle the list of NumPy arrays
            unnormalized_features = [f * std + mean for f in normalized_features]
        
        else:
            raise TypeError("normalized_features must be a list of numpy arrays or a torch.Tensor.")

        return unnormalized_features

    def __len__(self):
        return len(self.gt)

    def __getitem__(self, idx):
        """
        Args:
            idx (int): Index of the sample to retrieve.

        Returns:
            dict: A dictionary containing 'inputs' and 'ground_truth'.
        """
        if idx >= len(self.gt):
            raise IndexError("Index out of range")
        
        input = self.inputs[idx]
        gt = self.gt[idx]
        if self.transform:
            input = self.transform(input)
        
        return torch.from_numpy(input), torch.from_numpy(gt)
