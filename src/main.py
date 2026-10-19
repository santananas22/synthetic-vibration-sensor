from src.dataset import read_dataset

dataset_path = "/home/santana/projects/synthetic-vibration-sensor/data/sample_dataset_small.csv"

for sample in read_dataset(dataset_path):
    print(sample)