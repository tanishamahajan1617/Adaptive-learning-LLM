import torch.nn as nn


class EmotionLSTM(nn.Module):

    def __init__(
        self,
        input_size=3,
        hidden_size=64,
        num_layers=2,
        num_classes=4,
        dropout=0.2
    ):

        super().__init__()

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )

        self.fc = nn.Sequential(

    nn.Linear(
        hidden_size,
        32
    ),

    nn.ReLU(),

    nn.Linear(
        32,
        num_classes
    )
)

    def forward(self, x):

        out, _ = self.lstm(x)

        last_out = out[:, -1, :]

        logits = self.fc(last_out)

        return logits