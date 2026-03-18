import struct
import argparse
import json

parser = argparse.ArgumentParser(description="A simple script for printing a binary file of lego set data")

parser.add_argument("file", help="The binary file")

args = parser.parse_args()

with open(args.file, "rb", buffering=512) as f:
    set = {}

    set_id_length = struct.unpack(">H", f.read(2))[0]
    set["set_id"] = f.read(set_id_length).decode("utf-8")
    
    set["year"] = None
    year_is_included = struct.unpack(">B", f.read(1))[0]
    if year_is_included:
        set["year"] = struct.unpack(">H", f.read(2))[0]
    
    name_length = struct.unpack(">H", f.read(2))[0]
    set["name"] = f.read(name_length).decode("utf-8")

    set["category"] = None
    category_is_included = struct.unpack(">B", f.read(1))[0]
    if category_is_included:
        category_length = struct.unpack(">H", f.read(2))[0]
        set["category"] = f.read(category_length).decode("utf-8")

    set["preview_image_url"] = None
    preview_image_url_is_included = struct.unpack(">B", f.read(1))[0]
    if preview_image_url_is_included:
        preview_image_url_length = struct.unpack(">H", f.read(2))[0]
        set["preview_image_url"] = f.read(preview_image_url_length).decode("utf-8")

    inventory = []
    # Loops as long as it's able to read the first bytes of an inventory line
    while first_bytes := f.read(2):
        item = {}

        brick_type_id_length = struct.unpack(">H", first_bytes)[0]
        item["brick_type_id"] = f.read(brick_type_id_length).decode("utf-8")

        item["color_id"] = struct.unpack(">B", f.read(1))[0]

        item["count"] = struct.unpack(">H", f.read(2))[0]

        name_length = struct.unpack(">H", f.read(2))[0]

        item["name"] = f.read(name_length).decode("utf-8")

        item["preview_image_url"] = None
        preview_image_url_is_included = struct.unpack(">B", f.read(1))[0]
        if preview_image_url_is_included:
            preview_image_url_length = struct.unpack(">H", f.read(2))[0]
            item["preview_image_url"] = f.read(preview_image_url_length).decode("utf-8")
        
        inventory.append(item)

    set["inventory"] = inventory

    json_format = json.dumps(set, indent=4)
    print(json_format)
    
    


    



