import torch
from torch.nn import Linear
from torch_geometric.nn import GCNConv
from dataset import MyOwnDataset
import numpy as np 
# Helper function for visualization.

import networkx as nx
import matplotlib.pyplot as plt

import tensorflow as tf

converter = torch.nn.Sigmoid()  # needed for BCEWithLogits to get probability values

def print_output(pred, real):
    size = pred.size()

    p_zero = -1
    for i in range(0, size[0]):
        if real[i][0].item() == 1:
            p_zero = i

    probabilities = converter(pred)

    print("Predictions (actual patient 0 is node %d)" % p_zero)
    for i in range(size[0]):
        print("Node %d: prob. for: %.2f, prob. against: %.2f %s" % (
            i, 
            probabilities[i,0].item(),
            probabilities[i,1].item(), 
            "   <-- patient 0" if i == p_zero else ""
        ))


class GCN(torch.nn.Module):
    def __init__(self,dataset):
        super().__init__()
        torch.manual_seed(1234)
        self.conv1 = GCNConv(dataset.num_features, 4)
        self.conv2 = GCNConv(4, 4)
        
        self.conv3 = GCNConv(4, 2)
        self.classifier = Linear(2, 2)

    def forward(self, x, edge_index):
        h = self.conv1(x, edge_index)
        h = h.tanh()
        h = self.conv2(h, edge_index)
        h = h.tanh()
        h = self.conv3(h, edge_index)
        h = h.tanh()  # Final GNN embedding space.
        
        # Apply a final (linear) classifier.
        out = self.classifier(h)

        return out, h
    
def visualize_embedding(h, color, epoch=None, loss=None):
    plt.figure(figsize=(7,7))
    plt.xticks([])
    plt.yticks([])
    h = h.detach().cpu().numpy()
    plt.scatter(h[:, 0], h[:, 1], s=140, c=color, cmap="Set2")
    if epoch is not None and loss is not None:
        plt.xlabel(f'Epoch: {epoch}, Loss: {loss.item():.4f}', fontsize=16)
    plt.show()

# Loading the dataset
print("Loading dataset...")
train_dataset = MyOwnDataset(root="data/")

test_dataset = MyOwnDataset(root="data/", test = True)
model = GCN(train_dataset)
print(model)

import time
from IPython.display import Javascript,display  # Restrict height of output cell.
display(Javascript('''google.colab.output.setIframeHeight(0, true, {maxHeight: 430})'''))


criterion = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor([5.5,1],dtype=torch.float))  # Define loss criterion.
optimizer = torch.optim.Adam(model.parameters(), lr=0.01)  # Define optimizer.

#data = train_dataset[0]
def train(data):
    optimizer.zero_grad()  # Clear gradients.
    out, h = model(data.x, data.edge_index)  # Perform a single forward pass.
    loss = criterion(out, data.y.float())
    temp = data.y.unsqueeze(1).float()  # Compute the loss solely based on the training nodes.
    loss.backward()  # Derive gradients.
    optimizer.step()  # Update parameters based on gradients.
    return loss, h


def test():
      model.eval()

      #converter = torch.nn.Sigmoid()  # needed for BCEWithLogits to get probability values
      
      total_correct = 0
      total_nodes = 0
      error = []
      total_num_nodes  = 0
      # Check against ground-truth labels.
      for idx in range (0,10):
      
        data = test_dataset[idx]
        out,h = model(data.x, data.edge_index)
        # Use the class with highest probability.
        #pred = torch.round(out)
        #print(out.size())
        #print("prediction:")
        # print_tensor(converter(out))
        #print_tensor(out)
        #print("the actual data:",data.y)
        print_output(out, data.y)
        test_correct = np.count_nonzero(out == data.y)
        # for was_correct in test_correct:
        #     total_nodes += 1
        #     if was_correct:
        #         total_correct += 1
        mismatches = out.size(dim = 0) - test_correct
        total_num_nodes = total_num_nodes+out.size(dim = 0)
        error.append(mismatches)
        
      # Derive ratio of correct predictions.
      test_not_acc = sum(error) / total_num_nodes
      test_correct = 1- test_not_acc
      return test_correct

size = len(train_dataset)
for epoch in range(1,100):
    for idx in range(size):    
        data = train_dataset[idx]
        loss, h = train(data)
        if epoch % 20 == 0 and idx == size-1:
            visualize_embedding(h, color=[e[0] for e in data.y], epoch=epoch, loss=loss)
            time.sleep(0.3)

test_acc = test()
print(f'Test Accuracy: {test_acc:.4f}')
