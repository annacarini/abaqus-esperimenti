import torch
import math
import pickle
import numpy as np
from random import random

# Classi e funzioni per ML definite negli altri file
from ML_model import *
from ML_utils import *

    
PATH_WEIGHTS = "C:\\Users\\Anna\\Documents\\GitHub\\abaqus-esperimenti\\blender-3d\\addons\\model_state_dict.pth"
PATH_MODEL = "C:\\Users\\Anna\\Documents\\GitHub\\abaqus-esperimenti\\blender-3d\\addons\\full_model.pth"
PATH_NORM_VALUES = "C:\\Users\\Anna\\Documents\\GitHub\\abaqus-esperimenti\\blender-3d\\addons\\saved_dictionary_3D.pkl"


# creo coordinate random
print("creo coord random")
coord_1 = [[random(), random(), random()] for i in range (0, 98)]
coord_2 = [[random(), random(), random()] for i in range (0, 98)]


print("creo modello")

if torch.cuda.is_available():
    print("cuda available")
    device = "cuda"
    using_cuda = True
else:
    device = "cpu"
    using_cuda = False

#device = "cpu"

input_seq_len = 98 #72
input_dim = 6 #4  # Each input is a sequence of 2Dx2 points (x, y)
d_model = 512  # Embedding dimension
nhead = 4  # Number of attention heads
num_encoder_layers = 4  # Number of transformer encoder layers
dim_feedforward = 512  # Feedforward network dimension
output_dim = 9078 #280  # Each output is a 2D point (x, y)
dropout = 0.0

model = Transformer2DPointsModel(input_dim, input_seq_len, d_model, nhead, num_encoder_layers, dim_feedforward, output_dim, dropout).to(device)

# Carica i pesi
print("carico pesi")
model.load_state_dict(torch.load(PATH_WEIGHTS, weights_only=True, map_location=torch.device(device)))



# prendo mean e std
print("carico mean e std")
norm_values = {}
with open(PATH_NORM_VALUES, 'rb') as input_file:
    norm_values = pickle.load(input_file)   


with torch.autograd.profiler.profile(use_cuda=using_cuda) as prof:

    # trasformo coordinate in tensore
    init_coords_circle_data = np.array(coord_1)             
    init_coords_circle_data = torch.tensor(init_coords_circle_data).float()

    before_coords_data = np.array(coord_2)  
    before_coords_data = torch.tensor(before_coords_data).float()

    total_data = torch.cat((init_coords_circle_data,before_coords_data),1)
    
    images = total_data
    images = images.to(device)
    images = images[None, :, :]

    print("chiamo modello ML")

    # passo in input alla rete neurale
    predicted_displacements = model(images,None)

    # de-normalizzo:
    predicted_displacements = denormalize_targets(predicted_displacements,norm_values)

    predicted_displacements = predicted_displacements.cpu().detach().numpy()
    predicted_displacements = predicted_displacements.reshape(-1,3)

    print("predicted displacements:")
    print(predicted_displacements)

print("cuda time:")
print(prof)