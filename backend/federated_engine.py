import sys
# Prevent global tensorflow/tensorboard imports from throwing compatibility errors
sys.modules['tensorflow'] = None
sys.modules['tensorboard'] = None


import os
import flwr as fl
import torch
import torch.nn as nn
import numpy as np
import matplotlib.pyplot as plt
from collections import OrderedDict
from backend.model import DosagePredictionModel, get_model_parameters, set_model_parameters
from backend.data_utils import load_hospital_data

# Ensure matplolib runs smoothly in interactive mode for live plotting
plt.ion()
fig, ax = plt.subplots(figsize=(8, 5))
rounds_log, loss_log = [], []

# Define standard Criterion and Local Hyperparameters for FedProx
CRITERION = nn.MSELoss()
MU = 0.01  # Proximal term constant for FedProx regularization

def train_fedprox(model, train_loader, epochs, mu, global_params):
    """Trains the local model using the FedProx optimization constraint."""
    optimizer = torch.optim.SGD(model.parameters(), lr=0.001)
    model.train()
    
    for epoch in range(epochs):
        for X_batch, y_batch in train_loader:
            optimizer.zero_grad()
            output = model(X_batch)
            
            # Standard structural Loss (MSE)
            base_loss = CRITERION(output, y_batch)
            
            # FedProx Proximal Term calculation: Penalize deviation from Global Server weights
            proximal_term = 0.0
            for param, global_param in zip(model.parameters(), global_params):
                proximal_term += torch.true_divide(torch.sum((param - torch.tensor(global_param)) ** 2), 2.0)
            
            # Total Loss formulation
            total_loss = base_loss + (mu * proximal_term)
            total_loss.backward()
            optimizer.step()

def test_model(model, val_loader):
    """Evaluates local performance metrics."""
    model.eval()
    total_loss = 0.0
    with torch.no_grad():
        for X_batch, y_batch in val_loader:
            output = model(X_batch)
            total_loss += CRITERION(output, y_batch).item()
    return total_loss / len(val_loader) if len(val_loader) > 0 else 0.0

class FlowerVirtualClient(fl.client.NumPyClient):
    """Virtual Client representational container managed by Flower Simulation."""
    def __init__(self, hospital_id):
        self.hospital_id = hospital_id
        self.train_loader, self.val_loader = load_hospital_data(hospital_id)
        self.model = DosagePredictionModel()

    def get_parameters(self, config):
        return get_model_parameters(self.model)

    def fit(self, parameters, config):
        # Synchronize local model parameters with current global state
        set_model_parameters(self.model, parameters)
        # Train locally keeping track of previous global parameters
        train_fedprox(self.model, self.train_loader, epochs=3, mu=MU, global_params=parameters)
        return get_model_parameters(self.model), len(self.train_loader.dataset), {}

    def evaluate(self, parameters, config):
        set_model_parameters(self.model, parameters)
        loss = test_model(self.model, self.val_loader)
        return float(loss), len(self.val_loader.dataset), {"loss": float(loss)}

def client_fn(cid: str) -> fl.client.Client:
    """Spawns isolated client runtime targets on-demand."""
    hospital_map = {"0": "alpha", "1": "beta"}
    return FlowerVirtualClient(hospital_map[cid]).to_client()

class LivePlottingStrategy(fl.server.strategy.FedProx):
    """Custom Flower Strategy wrapper to intercept aggregations and draw plots live."""
    def aggregate_evaluate(self, server_round, results, failures):
        # Call baseline FedProx aggregation logic
        loss_aggregated, metrics_aggregated = super().aggregate_evaluate(server_round, results, failures)
        
        if loss_aggregated is not None:
            print(f"\n📢 [ROUND {server_round}] Server Aggregation Complete. Global Evaluation Loss: {loss_aggregated:.4f}")
            
            # Append metrics to tracking logs
            rounds_log.append(server_round)
            loss_log.append(loss_aggregated)
            
            # Update Matplotlib Screen
            ax.clear()
            ax.plot(rounds_log, loss_log, marker='o', linestyle='-', color='#10b981', linewidth=2)
            ax.set_title("GenieDose: Real-Time FedProx Global Convergence", fontsize=12, fontweight='bold')
            ax.set_xlabel("Federated Communication Round", fontsize=10)
            ax.set_ylabel("Mean Squared Error (Loss)", fontsize=10)
            ax.grid(True, linestyle='--', alpha=0.6)
            
            plt.draw()
            plt.pause(0.5)  # Keep window active briefly to allow paint loop
            
        return loss_aggregated, metrics_aggregated

def run_fl_simulation(num_rounds=5):
    """Triggers the centralized standalone evaluation simulation architecture."""
    print("🚀 Initializing GenieDose Federated Engine via Virtual Process Simulation...")
    
    strategy = LivePlottingStrategy(
        fraction_fit=1.0,
        fraction_evaluate=1.0,
        min_fit_clients=2,
        min_evaluate_clients=2,
        min_available_clients=2,
        proximal_mu=MU,
        initial_parameters=fl.common.ndarrays_to_parameters(get_model_parameters(DosagePredictionModel()))
    )
    
    # Run simulation
    fl.simulation.start_simulation(
        client_fn=client_fn,
        num_clients=2,
        config=fl.server.ServerConfig(num_rounds=num_rounds),
        strategy=strategy,
    )
    
    # Keep the final plot open at completion
    plt.ioff()
    plt.show()

if __name__ == "__main__":
    run_fl_simulation(num_rounds=5)