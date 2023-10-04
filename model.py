import torch
from torch.nn import Linear
from torch_geometric.nn import GCNConv
from dataset import MyOwnDataset
import numpy as np 
# Helper function for visualization.

import networkx as nx
import matplotlib.pyplot as plt

import tensorflow as tf

import mlflow
import mlflow.sklearn
from mlflow.models import infer_signature
import sys

#mlflow.autolog()

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

type_graph = int(sys.argv[1])
#1 means ER graph, 2 means rgg graph
if type_graph == 1:
    train_dataset = MyOwnDataset(root="data/ER_Graph/")
    test_dataset = MyOwnDataset(root="data/ER_Graph/", test = True)
elif type_graph == 2:
    train_dataset = MyOwnDataset(root="data/RGG_Graph/")
    test_dataset = MyOwnDataset(root="data/RGG_Graph/", test = True)
else:
    raise Exception("No such Graph")

model = GCN(train_dataset)
print(model)

import time
from IPython.display import Javascript,display  # Restrict height of output cell.
display(Javascript('''google.colab.output.setIframeHeight(0, true, {maxHeight: 430})'''))



position_weight=[10,1]

position_weight1 = " "
for i in position_weight:
    position_weight1 = position_weight1 + " " +str(i) + ","
position_weight1 = position_weight1[0:-1]

lern_rate = 0.01
criterion = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(position_weight,dtype=torch.float))  # Define loss criterion.
optimizer = torch.optim.Adam(model.parameters(), lr=lern_rate)  # Define optimizer.

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
    right_prediction = 0
      # Check against ground-truth labels.
    for idx in range(len(test_dataset)):
        
        data = test_dataset[idx]
        out,h = model(data.x, data.edge_index)
        print_output(out, data.y)
        temp = []
        probabilities = converter(out)
        for i in range(out.size()[0]):
            temp.append(probabilities[i,0].item() - probabilities[i,1].item())
        p_0 = np.argmax(temp) #gives the index of the node with highest probability
        actual_p_0 = np.argmax(data.y, axis = 0)[0]
        if p_0 == actual_p_0.item():
            right_prediction += 1
    accuracy = right_prediction/len(test_dataset)

    return accuracy

size = len(train_dataset)
for epoch in range(1,100):
    for idx in range(size):    
        data = train_dataset[idx]

        loss, h = train(data)
        #if epoch % 50 == 0 and idx == size-1:
            #visualize_embedding(h, color=[e[0] for e in data.y], epoch=epoch, loss=loss)
            #time.sleep(0.3)


num_nodes = test_dataset[0].num_nodes
days = test_dataset[0].days
if type_graph == 1:
    graph_type = "ER"
elif type_graph == 2:
    graph_type = "RGG"
else: 
    pass

test_acc = test()
print(f'Test Accuracy: {test_acc:.4f}')

#mlflow.autolog(disable=True)
with mlflow.start_run():
    mlflow.set_tag("model_name", "gnn")

    params = {
        "days": days,
        "num_nodes": num_nodes,
        "learning_rate": lern_rate,
        "weight_1": position_weight[0],
        "weight_2": position_weight[1],
        "graph_type": graph_type
    }

    mlflow.log_params(params)
    mlflow.log_metric("accuracy", test_acc)
   # mlflow.log_param("days", days)
    # mlflow.log_param("num_nodes", num_nodes)
   # mlflow.log_metric("weight_1", position_weight[0])
   # mlflow.log_metric("weight_2", position_weight[1])
   # mlflow.log_metric("learning rate", lern_rate)
    #mlflow.log_metric("graph_type", graph_type)

    mlflow.pytorch.log_model(model,"gnn")
    print("test1")
print("test1")




