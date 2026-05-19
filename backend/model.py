import torch
import torch.nn as nn
import torch.nn.functional as F

class DosagePredictionModel(nn.Module):
    def __init__(self, input_dim=10):
        super(DosagePredictionModel, self).__init__()
        # Input layer: map the 10 structural genetic variables to a dense space
        self.fc1 = nn.Linear(input_dim, 32)
        self.fc2 = nn.Linear(32, 16)
        # Final output scalar (continuous distribution representing mg dosage concentration)
        self.fc3 = nn.Linear(16, 1)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        return self.fc3(x)

def get_model_parameters(model):
    """Extracts weights as raw NumPy layers to communicate across the network framework."""
    return [val.cpu().numpy() for _, val in model.state_dict().items()]

def set_model_parameters(model, parameters):
    """Re-injects updated network parameters back into the active network matrix."""
    params_dict = zip(model.state_dict().keys(), parameters)
    state_dict = {k: torch.tensor(v) for k, v in params_dict}
    model.load_state_dict(state_dict, strict=True)