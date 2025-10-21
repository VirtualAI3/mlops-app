from dataset_generator import run_dataset_generator as GenerarDataset
from train import run_train as Reentrenar

if __name__ == "__main__":
    GenerarDataset()
    Reentrenar()