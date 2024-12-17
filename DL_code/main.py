import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
from dataset import DisplacementDataset
import argparse
from torch.utils.tensorboard import SummaryWriter
import matplotlib.pyplot as plt

# Define the regression model
class RegressionModel(nn.Module):
    def __init__(self, input_size, output_size):
        super(RegressionModel, self).__init__()
        self.fc = nn.Sequential(
            nn.Linear(input_size, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Linear(128, output_size)
        )

    def forward(self, x):
        return self.fc(x)
# Create a 2D scatter plot with matplotlib
def plot_2d_ground_truth_vs_prediction(ground_truth, prediction):
    fig, ax = plt.subplots(figsize=(10, 7))

    # Plot ground truth points
    ax.scatter(ground_truth[:, 0], ground_truth[:, 1], 
               c='blue', label='Ground Truth', alpha=0.7)

    # Plot predicted points
    ax.scatter(prediction[:, 0], prediction[:, 1], 
               c='red', label='Prediction', alpha=0.7)

    # Customize plot
    ax.set_title("2D Ground Truth vs Prediction (XY Plane)")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.legend()
    
    return fig


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--train_dir', help='training root folder',default="/mnt/c/Abaqus_working_dir/train_set")
    parser.add_argument('--test_dir', help='test root folder',default="/mnt/c/Abaqus_working_dir/test_set")
    args = parser.parse_args()

    # Initialize TensorBoard SummaryWriter
    writer = SummaryWriter(log_dir='runs/experiment_name')

    # Hyperparameters
    batch_size = 4
    learning_rate = 0.001
    num_epochs = 500

    # Load the dataset
    train_dataset = DisplacementDataset(args.train_dir)
    #normalizing with train mean and std.
    test_dataset = DisplacementDataset(args.test_dir,None,train_dataset.inputs_mean, train_dataset.inputs_std, train_dataset.gt_mean, train_dataset.gt_std)
    input_size = 3  # "circle_speed_x", "circle_speed_y", "circle_impact_angle"
  #  import pdb; pdb.set_trace()
    output_size = train_dataset[0][1].shape[0] # Number of values in the ground truth CSV

    # Split into train and test sets
    #test_size = int(len(dataset) * test_split_ratio)
    #train_size = len(dataset) - test_size
    #train_dataset, test_dataset = random_split(dataset, [train_size, test_size])

    # Create DataLoaders
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

    # Initialize the model, loss function, and optimizer
    model = RegressionModel(input_size, output_size)
    criterion = nn.MSELoss()
    criterion_mae = nn.L1Loss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
   # Training loop
    for epoch in range(num_epochs):
        model.train()
        train_loss = 0.0
        for inputs, targets in train_loader:
            # Forward pass
            outputs = model(inputs)
            loss = criterion(outputs, targets)

            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            train_loss += loss.item()

        train_loss /= len(train_loader)
        print()

         # Evaluation on the test set
        model.eval()
        test_loss = 0.0
        unnorm_test_loss = 0.0
        with torch.no_grad():
            for inputs, targets in test_loader:
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                #a long and ugly line of code to un-normalize following statistics calculated on training data, in order to show the "true" error.
                unnorm_loss = criterion_mae(train_dataset._unnormalize_features(outputs,train_dataset.gt_mean,train_dataset.gt_std),train_dataset._unnormalize_features(targets,train_dataset.gt_mean,train_dataset.gt_std) )
                test_loss += loss.item()
                unnorm_test_loss+=unnorm_loss.item()

        test_loss /= len(test_loader)
        unnorm_test_loss /= len(test_loader)
        print(f"Epoch {epoch+1}/{num_epochs}, Train Loss: {train_loss:.4f}"+f", Test Loss: {test_loss:.4f}"+f", Unnorm Test Loss: {unnorm_test_loss:.4f}")
          # TensorBoard logging
        writer.add_scalars('Loss', 
                   {'Train': train_loss,
                    'Test': test_loss}, 
                   epoch+1)
        writer.add_scalar('Loss/Unnorm_Test', unnorm_test_loss, epoch+1)

    #plotting an example
    input,target = test_dataset[0]
    target = train_dataset._unnormalize_features(target,train_dataset.gt_mean,train_dataset.gt_std)
    target = target.numpy().reshape(-1, 3)
    model.eval()
    with torch.no_grad():
        prediction = model(input.unsqueeze(0))  # Add batch dimension
        prediction = train_dataset._unnormalize_features(prediction,train_dataset.gt_mean,train_dataset.gt_std)
        prediction = prediction.cpu().numpy().reshape(-1, 3)  # Reshape to (139, 3)
        # Create a 2D scatter plot
    # Ignore the Z-axis for 2D plotting
    target_2d = target[:, :2]  # Select only X and Y
    prediction_2d = prediction[:, :2]  # Select only X and Y
    # Generate the plot
    fig = plot_2d_ground_truth_vs_prediction(target_2d, prediction_2d)
    # Log the plot to TensorBoard
    writer.add_figure('3D Plot/Ground Truth vs Prediction', fig, global_step=num_epochs)
    # Close TensorBoard writer after training
    writer.close()
if __name__ == "__main__":
    main()