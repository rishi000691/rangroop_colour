import json

new_items = [
    # Light Summer (Deep Rose)
    {"id": "C119", "name": "Deep Rose Blazer", "category": "blazer", "color_hex": "#C05077", "image_url": "/static/clothing/placeholder_blazer_drose.png", "gender": "female"},
    {"id": "C120", "name": "Deep Rose Cotton Shirt", "category": "shirt", "color_hex": "#BD5379", "image_url": "/static/clothing/placeholder_shirt_drose.png", "gender": "unisex"},
    {"id": "C121", "name": "Deep Rose Midi Dress", "category": "dress", "color_hex": "#C54B74", "image_url": "/static/clothing/placeholder_dress_drose.png", "gender": "female"},

    # Light Summer (Spruce Green)
    {"id": "C122", "name": "Spruce Green Trousers", "category": "pants", "color_hex": "#2C7273", "image_url": "/static/clothing/placeholder_pants_spruce.png", "gender": "unisex"},
    {"id": "C123", "name": "Spruce Green Formal Shirt", "category": "shirt", "color_hex": "#2E7576", "image_url": "/static/clothing/placeholder_shirt_spruce.png", "gender": "unisex"},
    {"id": "C124", "name": "Spruce Green Silk Saree", "category": "saree", "color_hex": "#296E6F", "image_url": "/static/clothing/placeholder_saree_spruce.png", "gender": "female"},

    # Light Summer (Plum)
    {"id": "C125", "name": "Soft Plum Blazer", "category": "blazer", "color_hex": "#DCA2DF", "image_url": "/static/clothing/placeholder_blazer_plum.png", "gender": "female"},
    {"id": "C126", "name": "Plum Cotton Kurta", "category": "kurta", "color_hex": "#DB9DDB", "image_url": "/static/clothing/placeholder_kurta_plum.png", "gender": "unisex"},

    # Light Summer (Celadon Green)
    {"id": "C127", "name": "Celadon Green Linen Shirt", "category": "shirt", "color_hex": "#AEE2B2", "image_url": "/static/clothing/placeholder_shirt_celadon.png", "gender": "unisex"},
    {"id": "C128", "name": "Celadon Green Midi Dress", "category": "dress", "color_hex": "#A9DEAE", "image_url": "/static/clothing/placeholder_dress_celadon.png", "gender": "female"},

    # Soft Autumn (Mahogany)
    {"id": "C129", "name": "Mahogany Chinos", "category": "pants", "color_hex": "#C04000", "image_url": "/static/clothing/placeholder_pants_mahogany.png", "gender": "unisex"},
    {"id": "C130", "name": "Mahogany Wrap Dress", "category": "dress", "color_hex": "#C44404", "image_url": "/static/clothing/placeholder_dress_mahogany.png", "gender": "female"},
    {"id": "C131", "name": "Mahogany Linen Blazer", "category": "blazer", "color_hex": "#BC3D00", "image_url": "/static/clothing/placeholder_blazer_mahogany.png", "gender": "unisex"},

    # Soft Autumn (Deep Olive)
    {"id": "C132", "name": "Deep Olive T-Shirt", "category": "t-shirt", "color_hex": "#4A5D23", "image_url": "/static/clothing/placeholder_tshirt_dolive2.png", "gender": "unisex"},
    {"id": "C133", "name": "Deep Olive Cargo Pants", "category": "pants", "color_hex": "#4C6025", "image_url": "/static/clothing/placeholder_pants_dolive2.png", "gender": "unisex"},
    {"id": "C134", "name": "Deep Olive Kurta", "category": "kurta", "color_hex": "#485A21", "image_url": "/static/clothing/placeholder_kurta_dolive2.png", "gender": "unisex"},

    # Soft Autumn (Sienna)
    {"id": "C135", "name": "Sienna Midi Skirt", "category": "skirt", "color_hex": "#A25530", "image_url": "/static/clothing/placeholder_skirt_sienna.png", "gender": "female"},
    {"id": "C136", "name": "Sienna Knit Sweater", "category": "sweater", "color_hex": "#9E4F2B", "image_url": "/static/clothing/placeholder_sweater_sienna.png", "gender": "unisex"},

    # Soft Autumn (Cocoa)
    {"id": "C137", "name": "Cocoa Brown Blazer", "category": "blazer", "color_hex": "#987B6C", "image_url": "/static/clothing/placeholder_blazer_cocoa.png", "gender": "unisex"},
    {"id": "C138", "name": "Cocoa Chiffon Dress", "category": "dress", "color_hex": "#947666", "image_url": "/static/clothing/placeholder_dress_cocoa.png", "gender": "female"}
]

with open('app/data/clothing_items.json', 'r') as f:
    data = json.load(f)

# Filter out if already added (idempotent)
existing_ids = {item['id'] for item in data['items']}
new_items = [i for i in new_items if i['id'] not in existing_ids]

if new_items:
    data['items'].extend(new_items)
    data['_meta']['total_items'] = len(data['items'])

    with open('app/data/clothing_items.json', 'w') as f:
        json.dump(data, f, indent=4)
    print(f"Added {len(new_items)} items. Total is now {len(data['items'])}.")
else:
    print("Items already added.")
