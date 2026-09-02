from pathlib import Path

import cv2


import numpy as np
import torch
import albumentations as A

from src.Models.eyesegementation_model import UNet


class EyeSegmentationService:

    def __init__(self):

        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        print(
            f"Loading eye segmentation model on {self.device}"
        )

        self.model = UNet(
            in_channels=1,
            num_classes=4
        )

        model_path = (
            Path(__file__).resolve().parents[2]
            / "best_unet_model.pth"
        )

        if not model_path.exists():
            raise FileNotFoundError(
                f"Eye segmentation model not found: {model_path}"
            )

        self.model.load_state_dict(
            torch.load(
                model_path,
                map_location=self.device
            )
        )

        self.model.to(self.device)
        self.model.eval()

        # EXACTLY same preprocessing as val_transform
        self.transform = A.Compose([
            A.Resize(
                height=256,
                width=256
            ),
            A.Normalize(
                mean=(0.5,),
                std=(0.5,),
                max_pixel_value=255.0
            ),
        ])

        print(
            "Eye segmentation model loaded successfully."
        )

    def predict(self, image_bytes: bytes):

        # -----------------------------------------
        # Decode image
        # -----------------------------------------

        image_array = np.frombuffer(
            image_bytes,
            dtype=np.uint8
        )

        image = cv2.imdecode(
            image_array,
            cv2.IMREAD_GRAYSCALE
        )

        if image is None:
            raise ValueError(
                "Unable to decode input image."
            )

        # -----------------------------------------
        # Same preprocessing as validation
        # -----------------------------------------

        transformed = self.transform(
            image=image
        )

        image_tensor = transformed["image"]

        # H,W -> 1,H,W
        image_tensor = torch.from_numpy(
            image_tensor
        ).float()

        if image_tensor.ndim == 2:
            image_tensor = image_tensor.unsqueeze(0)

        # 1,H,W -> 1,1,H,W
        image_tensor = image_tensor.unsqueeze(0)

        image_tensor = image_tensor.to(
            self.device
        )

        # -----------------------------------------
        # Inference
        # -----------------------------------------

        with torch.no_grad():

            logits = self.model(
                image_tensor
            )

            probabilities = torch.softmax(
                logits,
                dim=1
            )

            mask = torch.argmax(
                probabilities,
                dim=1
            )

        # -----------------------------------------
        # Remove batch dimension
        # -----------------------------------------

        mask = mask.squeeze(0).cpu().numpy()

        probabilities = (
            probabilities
            .squeeze(0)
            .cpu()
            .numpy()
        )

        return {
            "mask": mask,
            "probabilities": probabilities
        }