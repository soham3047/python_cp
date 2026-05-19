import os
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader

# Ensure the mock data directory exists
os.makedirs('backend/mock_data', exist_ok=True)

class GenomicDosageDataset(Dataset):
    """Converts Pandas DataFrames into PyTorch Tensors for training."""
    def __init__(self, csv_file):
        df = pd.read_csv(csv_file)
        # Features: Drop the ID and the target dosage column
        self.X = torch.tensor(df.drop(columns=['patient_id', 'optimal_dosage']).values, dtype=torch.float32)
        # Target: The optimal dosage value
        self.y = torch.tensor(df['optimal_dosage'].values, dtype=torch.float32).unsqueeze(1)

    def __len__(self):
        return len(self.y)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

def generate_synthetic_databases(num_samples=200):
    """Generates distinct local databases to simulate data heterogeneity (Non-IID)."""
    np.random.seed(42)
    
    # 10 Simulated genetic variants (SNPs) represented as 0, 1, or 2 mutations
    features = [f'gene_marker_{i}' for i in range(10)]
    
    # --- HOSPITAL ALPHA: Tends to contain poor metabolizers (Needs Lower Dosages) ---
    alpha_data = np.random.randint(0, 3, size=(num_samples, 10))
    alpha_df = pd.DataFrame(alpha_data, columns=features)
    alpha_df.insert(0, 'patient_id', [f'ALPHA_{i}' for i in range(num_samples)])
    # Mathematical formulation for baseline dosage calculation
    alpha_df['optimal_dosage'] = 5.0 + (alpha_df['gene_marker_0'] * 1.5) - (alpha_df['gene_marker_3'] * 1.2) + np.random.normal(0, 0.5, num_samples)
    alpha_df.to_csv('backend/mock_data/hospital_alpha.csv', index=False)

    # --- HOSPITAL BETA: Tends to contain rapid metabolizers (Needs Higher Dosages) ---
    beta_data = np.random.randint(0, 3, size=(num_samples, 10))
    beta_df = pd.DataFrame(beta_data, columns=features)
    beta_df.insert(0, 'patient_id', [f'BETA_{i}' for i in range(num_samples)])
    # Different mathematical coefficient behavior to simulate real demographic shifts
    beta_df['optimal_dosage'] = 22.0 + (beta_df['gene_marker_1'] * 3.5) + (beta_df['gene_marker_5'] * 2.1) + np.random.normal(0, 1.0, num_samples)
    beta_df.to_csv('backend/mock_data/hospital_beta.csv', index=False)
    
    print("✓ Local databases populated inside backend/mock_data/")

def load_hospital_data(hospital_name, batch_size=16):
    """Helper function to turn local CSV databases into production data loops."""
    csv_path = f'backend/mock_data/hospital_{hospital_name}.csv'
    if not os.path.exists(csv_path):
        generate_synthetic_databases()
        
    dataset = GenomicDosageDataset(csv_path)
    # Split 80% training and 20% validation
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = torch.utils.data.random_split(dataset, [train_size, val_size])
    
    return DataLoader(train_dataset, batch_size=batch_size, shuffle=True), DataLoader(val_dataset, batch_size=batch_size)

if __name__ == "__main__":
    generate_synthetic_databases()