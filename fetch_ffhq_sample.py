from datasets import load_dataset
import os

os.makedirs("ffhq_test", exist_ok=True)

ds = load_dataset("nuwandaa/ffhq128", split="train", streaming=True)

for i, example in enumerate(ds):
    if i >= 30:  # grab 30 images
        break
    img = example["image"]
    img.save(f"ffhq_test/ffhq_{i}.png")

print("Done — 30 images saved to ffhq_test/")