import snap


# -*- coding: utf-8 -*-
"""colab3_zahan_parekh.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1kDUttioYopRlfZJZQS_vDSJu8GnBt1gq

<a href="https://colab.research.google.com/github/huangtinglin/test_colab/blob/main/CPSC483_colab2_wo_output.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>

## GNN for link prediction and graph classification task

Last time we explore a standard benchmark datase Cora, and implement a classic graph neural network GCN(Kipf et al. (2017)) for node classification task. In this Colab, we are going to explore two kinds of graph learning task: **link prediction** and **graph classification**. We will apply GCN to both of these two tasks. All of these implementations are still based on the [PyG](https://pytorch-geometric.readthedocs.io/en/latest/).

## Outline

- Link prediction task
- Graph classification task
"""

# import the pytorch library into environment and check its version
import os
import torch
print("Using torch", torch.__version__)

"""Let's start installing PyG by `pip`. The version of PyG should match the current version of PyTorch. Here we follow the [instruction](https://pytorch-geometric.readthedocs.io/en/latest/notes/installation.html) of PyG:"""

!pip install torch-scatter torch-sparse torch-cluster torch-spline-conv torch-geometric -f https://data.pyg.org/whl/torch-1.12.0+cu113.html
!pip install ogb  # for datasets

"""Import some required libraries into our environment:"""

from torch_geometric.data import Data
from torch_geometric.datasets import Planetoid
from torch_geometric import nn
import torch_geometric.transforms as T

"""## Link prediction task

### Dataset preprocess

As shown in the following figure, link prediction is to predict whether two nodes in a graph have a link, which can be considered as a binary classification task. We will construct a link prediction dataset containing training, validation, and test set based on Cora.

<br/>
<center>
<img src="https://github.com/Graph-and-Geometric-Learning/CPSC483-colab/blob/main/fig/link_prediction_example.png?raw=1" height="200" width="200"/>
</center>
<br/>

Given a graph, we divide the initial edge set into three distinct edge sets which represent the training, validation, and test set. Training set and validation set share a same graph structure. Test set contains some edges which does not exist in training and validation set to prevent data leakage.
<!-- Training set does not include edges in validation and test set, and the validation split does not include edges in the test split. Validation and test data should not be leaked into the training set. -->

<br/>
<center>
<img src="https://github.com/Graph-and-Geometric-Learning/CPSC483-colab/blob/main/fig/link_prediction_dataset_split(2).png?raw=1" height="200" width="350"/>
</center>
<br/>

Our model will be optimized on the training set. We can use `transforms` function in PyG to easily generate the data splits:
"""

transform = T.Compose([
    T.RandomLinkSplit(num_val=0.05,  # ratio of edges including in the validation set
                      num_test=0.2,  # ratio of edges including in the test set
                      is_undirected=True,
                      add_negative_train_samples=False),
])

"""Loading the Cora dataset:"""

dataset = Planetoid('/tmp/cora', 'cora', transform=transform)

"""The data will be transformed from a data object to three tuples, where each element represents the corresponding split:"""

train_data, val_data, test_data = dataset[0]

"""Now data object has two attributes of edge: `edge_index` and `edge_label_index`. `edge_index` denotes the graph structure used for performing message passing in GNN. `edge_label_index` denotes the edge index used to calculate loss in training set, or to evaluate the model in validation and test set.

Printing the statistics of data:
"""

print("Number of the nodes in training, validation and test data are", train_data.num_nodes, val_data.num_nodes, test_data.num_nodes)
print("Number of the edges in training, validation and test data are", train_data.num_edges, val_data.num_edges, test_data.num_edges)
print("Number of the edge_label_index in training, validation and test data are", train_data.edge_label_index.shape[1], 
                                                                                  val_data.edge_label_index.shape[1],
                                                                                  test_data.edge_label_index.shape[1])

"""### Pipeline

We constructed the GCN by PyG in the last Colab, and now we simply use the same architecture:
"""

from torch_geometric.nn import GCNConv

class GCN(torch.nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels):
        super().__init__()

        self.conv1 = GCNConv(in_channels, hidden_channels)
        self.conv2 = GCNConv(hidden_channels, out_channels)
        self.act = torch.nn.ReLU()

    def forward(self, node_feature, edge_index):

        output = self.conv1(node_feature, edge_index)
        output = self.act(output)
        output = self.conv2(output, edge_index)

        return output

"""Initializing a GCN model:"""

model = GCN(dataset.num_features, hidden_channels=128, out_channels=64)

"""Define an optimizer for model:"""

optimizer = torch.optim.Adam(params=model.parameters(), lr=0.01)

"""Similar as the what we do in the node classification task, we first apply the GCN model to produce the representation of each node in the graph. Usually we will use **inner product** to measure the similarity between two node representations to determine how likely it is for these two nodes to be connected.

#### Question 1

Following the instruction and implement the function to calculate the inner product:
"""

def compute_similarity(node_embs, edge_index):
    result = torch.tensor([0.] * len(edge_index[0]))

    # TODO: Define similarity function.
    # 1. calculate the inner product between all the pairs in the edge_index
    # Note: the shape of node_embs is [n, h] where n is the number of nodes, and h is the embedding size
    # the shape of edge_index is [2, m] where m is the number of edges

    ############# Your code here ############
    ## (~1 line of code)
    node_embs = torch.nn.functional.normalize(node_embs)
    for i in range(len(edge_index[0])):
      result[i] = torch.dot(node_embs[edge_index[0][i]], node_embs[edge_index[1][i]])
    

    #########################################

    return result

n, h = 5, 10  # number of nodes and embedding size
node_embs = torch.rand(n, h)
edge_index = torch.tensor([[0, 1, 2, 3], 
                           [2, 3, 0, 1]])  # compute the similarity of (0, 2), (1, 3), (2, 0), (3, 1)
similarity = compute_similarity(node_embs, edge_index)
print("Similairty:", similarity)

"""We optimize the model by minimizing the loss function. Here we consider the link prediction task as a binary classification task (edge exists or no), and apply binary cross entropy loss:"""

loss_fn = torch.nn.BCEWithLogitsLoss()

"""The edges in the graph will be taken as the positive examples with label=1 in the loss function. To prevent model from collapse, we usually will feed some **negative examples** to the loss function, which is the non-existing edges in the graph. The number of negative examples should equal to the number of positive ones.

With the help of PyG, we can easily perform the negative sampling. Here is an example:
"""

from torch_geometric.utils import negative_sampling

neg_edge_index = negative_sampling(
      edge_index=train_data.edge_index,  # positive edges in the graph
      num_nodes=train_data.num_nodes,  # number of nodes
      num_neg_samples=5,  # number of negative examples
    )

print("shape of neg_edge_index:", neg_edge_index.shape)  # [2, num_neg_samples]
print("negative examples:", neg_edge_index)

"""Positive examples (`edge_label_index`) will be assigned the label 1, and negative ones will be assigned the label 0. We can obtain the label of positive examples like this:"""

print("positive examples' labels:", train_data.edge_label)

"""Now we can construct training and testing pipeline, which is similar to what we do in the last Colab.

#### Question 2

Please follow the instruction and implement a function that trains a model.
"""

def train(model, data, optimizer, loss_fn):

    loss = 0

    # TODO: Define train function.
    # 1. put the model into train mode
    # 2. clear the gradients calculated from the last batch
    # 3. use 'edge_index' to get the node representation by model
    # 4. sample the negative examples with the same number of positive ones (edge_label_index)
    # 5. concatenate the positive edges and negative edges
    # 6. concatenate the labels of positive edges and negative edges
    # 7. calculate the similarity between two end nodes to determine the probability that the corresponding edge is present on the graph.
    # 8. feed the probability and edge label to the loss function
    # 9. calculate the gradients of each parameter
    # 10. update the parameters by taking an optimizer step

    ############# Your code here ############
    ## (~10 line of code)
    model.train()
    optimizer.zero_grad()
    y_pred = model(data.x, data.edge_index)
    
    neg_edge_index = negative_sampling(
      edge_index=train_data.edge_index,  # positive edges in the graph
      num_nodes=train_data.num_nodes,  # number of nodes
      num_neg_samples=len(data.edge_label),  # number of negative examples
    )
    # print(neg_edge_index.shape)
    train_edge_index = torch.cat((data.edge_label_index, neg_edge_index), dim=1)
    train_edge_label = torch.cat((data.edge_label, torch.tensor([0] * len(train_data.edge_label_index[0]))))
    # print(train_edge_index.shape)
    pred = compute_similarity(data.x, train_edge_index)
    loss = loss_fn(pred.clone().detach().requires_grad_(True), train_edge_label)
    loss.backward()
    optimizer.step()


    #########################################

    return loss

"""We usually use [AUC score](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.roc_auc_score.html) to evaluate the performance of model on binary classification task. The test function is as followed:"""

from sklearn.metrics import roc_auc_score

@torch.no_grad()
def test(model, data):
    model.eval()
    out = model(data.x, data.edge_index)  # use `edge_index` to perform message passing
    out = compute_similarity(out, data.edge_label_index).view(-1).sigmoid()  # use `edge_label_index` to compute the loss
    return roc_auc_score(data.edge_label.cpu().numpy(), out.cpu().numpy())

"""Now we can start to train our model based on `train` and `test` function:"""

epochs = 50

best_val_auc = final_test_auc = 0
for epoch in range(1, epochs + 1):
    loss = train(model, train_data, optimizer, loss_fn)
    valid_auc = test(model, val_data)
    test_auc = test(model, test_data)
    if valid_auc > best_val_auc:
        best_val_auc = valid_auc
        final_test_auc = test_auc
    print(f'Epoch: {epoch:03d}, Loss: {loss:.4f}, Val: {valid_auc:.4f}, Test: {test_auc:.4f}')

"""## Graph classification task

Now let's have a closer look at the task of graph classification. Graph classification refers to the problem of classifiying entire graphs, given a dataset of graphs. Here, we will apply GNN to embed entire graphs.

### Dataset preprocess

One of the most common benchmark dataset of graph classification is [TUDatasets](https://chrsmrrs.github.io/datasets/) which are collected by TU Dortmund University. Each graph in this dataset is a molecule, and the task is to infer whether a molecule inhibits HIV virus replication or not. We can load this dataset by PyG. In this colab, we mainly focus on one of the smaller ones in TUDatasets: MUTAG dataset.
"""

from torch_geometric.datasets import TUDataset

dataset = TUDataset(root='/tmp/mutag', name='MUTAG')
print(dataset)

"""We can obtain its number of graphs, classes, node features:"""

print(f'number of graphs: {len(dataset)}')
print(f'number of classes: {dataset.num_classes}')
print(f'Number of node features: {dataset.num_node_features}')

"""There 188 graphs in this dataset, and we can get the graph object with any id. For example:"""

data = dataset[5]
print(f'5-th graph object: {data}')

"""We can obtain some statistics for each graph object:"""

print(f'Number of nodes: {data.num_nodes}')
print(f'Number of edges: {data.num_edges}')
print(f'Average node degree: {data.num_edges / data.num_nodes:.2f}')
print(f'Has isolated nodes: {data.has_isolated_nodes()}')
print(f'Has self-loops: {data.has_self_loops()}')
print(f'Is undirected: {data.is_undirected()}')

"""We will divide the dataset into training set and test set, and there is no duplicate graph in these two sets. We can randomly pick 150 graphs to form training set, and the remaining ones will be the test set:"""

dataset = dataset.shuffle()

train_dataset = dataset[:150]
test_dataset = dataset[150:]

"""### Mini-batching of graphs

To fully utilize GPU, we will conduct mini-batch training which can be achieved by PyG. A batch of graphs will be grouped in a giant graph that holds multiple isolated subgraphs, and node features are simply concatenated. `dataloader` object in PyG can easily finish the aboved process:
"""

from torch_geometric.loader import DataLoader

train_loader = DataLoader(train_dataset, batch_size=128, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=128, shuffle=False)

"""Here is an example to show how dataloader works. We can observe that multiple graphs are included in a giant graph."""

for step, data in enumerate(train_loader):
    print(f'Step {step + 1}, number of graphs in the current batch: {data.num_graphs}')
    print(f'Step {step + 1}, number of nodes in the current batch: {data.num_nodes}')
    print(f'Step {step + 1}, the graph id to which each node belongs is: {data.batch}')
    print()

"""The graph id of every node to which it belongs is indicated by the `batch` attribute.

### Model Implementation

First we perform message passing to embed each node in the graph, then aggregate the node embeddings into a graph embedding by pooling method. Finally the graph embedding will be fed to a classifier to conduct graph classification.

We will apply mean pooling method which is to simply take the average of node embeddings. Here is an example of mean pooling:
"""

from torch_geometric.nn import global_mean_pool

x = torch.rand(5, 4)  # embeddings of 5 nodes

# graph id. The first two nodes belong to first graph, 
# the 3rd node belongs to the second graph, 
# and the last two nodes belong to the last graph
batch = torch.tensor([0, 0, 1, 2, 2])

x = global_mean_pool(x, batch)  # node embedding and the graph id to which each node belongs to
print(f"shape of graph embedding: {x.shape}")

"""#### Question 3

Follow the instruments and implement the GNN model for graph classifiation task.
"""

from torch_geometric.nn.glob import global_max_pool
from torch.nn import Linear
import torch.nn.functional as F
from torch_geometric.nn import GCNConv
from torch_geometric.nn import global_mean_pool


class GCN(torch.nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels):
        super(GCN, self).__init__()
        
        # TODO: Define two GCNConv modules, a linear classifier and a ReLU function.
        # The input size and output size of first GCNConv module should be in_channels and hidden_channels
        # The input size and output size of second GCNConv module should be hidden_channels and hidden_channels
        # The input size and output size of Linear module should be hidden_channels and out_channels

        ############# Your code here ############
        ## (~4 line of code)
        self.conv1 = GCNConv(in_channels, hidden_channels)
        self.conv2 = GCNConv(hidden_channels, out_channels)
        self.relu = torch.nn.ReLU()
        self.linear = Linear(hidden_channels, out_channels)
        #########################################

    def forward(self, x, edge_index, batch):

        output = None

        # TODO: Use the modules you define in __init__ to perform message passing.
        # ReLU function should be used in the middle of two GCNConv modules.
        # Apply global_mean_pool module to generate graph embeddings
        # Apply linear classifier to predict the label

        ############# Your code here ############
        ## (~3 line of code)
        node_representation = self.conv1(x, edge_index)
        node_representation = self.relu(node_representation)
        node_representation = self.conv2(node_representation, edge_index)
        node_representation = global_mean_pool(node_representation, batch)
        output = self.linear(node_representation)

        #########################################
        return output

"""Initialize a model and optimizer:"""

model = GCN(in_channels=dataset.num_node_features, hidden_channels=2, out_channels=dataset.num_classes)
optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
print(model)

"""### Pipeline

Here we use cross entropy loss to optimize:
"""

loss_func = torch.nn.CrossEntropyLoss()

"""#### Question 4

Now we are going to implement `train` function. Please follow the instrution:
"""

def train(model, loader, optimizer, loss_func):

    loss = 0

    # TODO: Define train function.
    # 1. put the model into train mode
    # 2. iterate over the dataloader
    # 3. obtain the predicted result by model
    # 4. compute the loss
    # 5. loss backward
    # 6. update the parameters by taking an optimizer step
    # 7. clear the gradients calculated from the last batch

    ############# Your code here ############
    ## (~7 line of code)
    model.train()
    print(loader)
    for step, data in enumerate(loader):
      y_pred = model(data.x, data.edge_index, data.batch)
      loss = loss_fn(y_pred, data.y)
      loss.backward()
      optimizer.step()
      optimizer.zero_grad()
    

    #########################################

    return model

"""The `test` function is implemented as followed:"""

def test(model, loader):
     model.eval()

     correct = 0
     for data in loader:  # Iterate in batches over the training/test dataset.
         out = model(data.x, data.edge_index, data.batch)  
         pred = out.argmax(dim=1)  # Use the class with highest probability.
         correct += int((pred == data.y).sum())  # Check against ground-truth labels.
     return correct / len(loader.dataset)  # Derive ratio of correct predictions.

"""Now we can train and evaluate our model on graph classification task:

"""

epochs = 100

for epoch in range(1, epochs):
    model = train(model, train_loader, optimizer, loss_func)
    test_acc = test(model, test_loader)
    print(f'Epoch: {epoch:03d}, Test Acc: {test_acc:.4f}')

"""## Submission

Make sure to run all the cells and save a copy of this colab in your driver. If you complete this notebook, download the colab and upload your work to canvas to submit it.
"""