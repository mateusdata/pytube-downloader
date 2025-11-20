import torch
import torch.nn as nn
import torch.optim as optim
import random
import numpy as np

# reproducibilidade
torch.manual_seed(0)
np.random.seed(0)
random.seed(0)

# cria dataset: pares (a, b) -> alvo a + b
N = 1000
X = np.random.uniform(-10, 10, size=(N, 2)).astype(np.float32)
y = (X.sum(axis=1, keepdims=True)).astype(np.float32)

X_tensor = torch.from_numpy(X)
y_tensor = torch.from_numpy(y)

# modelo simples (pode ser apenas uma camada linear)
model = nn.Sequential(
    nn.Linear(2, 32),
    nn.ReLU(),
    nn.Linear(32, 1)
)

loss_fn = nn.MSELoss()
optimizer = optim.Adam(model.parameters(), lr=0.01)

# treinamento
epochs = 1000
for epoch in range(1, epochs + 1):
    model.train()
    optimizer.zero_grad()
    preds = model(X_tensor)
    loss = loss_fn(preds, y_tensor)
    loss.backward()
    optimizer.step()

    if epoch % 100 == 0 or epoch == 1:
        print(f"Epoch {epoch:4d} - Loss: {loss.item():.6f}")

# testar alguns exemplos
model.eval()
tests = torch.tensor([[1.0, 2.0], [5.5, -2.5], [10.0, 3.0], [-4.0, -6.0]])
with torch.no_grad():
    out = model(tests).numpy().flatten()
for inp, pred in zip(tests.numpy(), out):
    print(f"{inp[0]} + {inp[1]} -> modelo: {pred:.4f}  (esperado: {inp[0] + inp[1]:.4f})")
