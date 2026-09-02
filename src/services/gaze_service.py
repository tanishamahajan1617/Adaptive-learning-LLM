from pathlib import Path

import torch
from PIL import Image
from torchvision import transforms

from Models.gaze_model import GazeModel


class GazeService:

    def __init__(self):

        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        print(f"Loading gaze model on {self.device}")

        self.model = GazeModel()

        model_path = (
            Path(__file__).resolve().parents[2]
            / "Models"
            / "best_gaze_model.pth"
        )

        if not model_path.exists():
            raise FileNotFoundError(
                f"Gaze weights not found: {model_path}"
            )

        self.model.load_state_dict(
            torch.load(
                model_path,
                map_location=self.device
            )
        )

        self.model.to(self.device)
        self.model.eval()

        # EXACTLY same as training
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.5, 0.5, 0.5],
                std=[0.5, 0.5, 0.5]
            )
        ])

        print("Gaze model loaded successfully.")

    def predict(self, image: Image.Image):

        image = image.convert("RGB")

        tensor = self.transform(image)

        tensor = tensor.unsqueeze(0)

        tensor = tensor.to(self.device)

        with torch.no_grad():

            prediction = self.model(tensor)

        gaze_x = float(prediction[0][0].item())
        gaze_y = float(prediction[0][1].item())

        return {
            "gaze_x": gaze_x,
            "gaze_y": gaze_y
        }