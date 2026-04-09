import torch
import torch.nn as nn
import os

class PriceLSTMModel(nn.Module):
    def __init__(self, input_size: int, hidden_size: int = 64, num_layers: int = 2, output_size: int = 3):
        super(PriceLSTMModel, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=0.2 if num_layers > 1 else 0)
        self.fc = nn.Linear(hidden_size, output_size)
    
    def forward(self, x):
        # x shape: (batch, seq_len, features)
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        
        out, _ = self.lstm(x, (h0, c0))
        
        # Take the hidden state of the last time step
        out = self.fc(out[:, -1, :])
        return out

def create_model(input_size: int, hidden_size: int = 64, num_layers: int = 1, output_size: int = 3):
    return PriceLSTMModel(input_size, hidden_size, num_layers, output_size)

def save_model(model: nn.Module, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    torch.save(model.state_dict(), path)

def load_model(path: str, input_size: int, hidden_size: int = 64, num_layers: int = 1, output_size: int = 3):
    model = create_model(input_size, hidden_size, num_layers, output_size)
    model.load_state_dict(torch.load(path))
    model.eval()
    return model
