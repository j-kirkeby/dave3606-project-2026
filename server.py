import json
import html
import gzip
import struct
from simplecache import SimpleCache
from database import Database
from flask import Flask, Response, request
from time import perf_counter

app = Flask(__name__)

# Cache - see SimpleCache.py
cache = SimpleCache(capacity = 100)

@app.route("/")
def index():
    with open("templates/index.html") as f:
        template = f.read()
        
    return Response(template)


@app.route("/sets")
def sets():
    valid_encodings = ['UTF-16-LE', 'UTF-16-BE', 'UTF-32-LE', 'UTF-32-BE', 'UTF-16', 'UTF-8']

    requested_encoding = request.args.get('encoding', default='UTF-8')

    encoding = requested_encoding if requested_encoding in valid_encodings else 'UTF-8' 

    with open("templates/sets.html") as f:
        template = f.read()

    db = Database()
    try:
        rows = get_sets_list_html(db)
    finally:
        db.close()

    result = "".join(rows) # Combine the strings efficiently, all at once
    page_html = template.replace("{ROWS}", result).replace("{ENCODING}", encoding)

    # Manually encode the bytes
    response_bytes = page_html.encode(encoding)
    compressed_bytes = gzip.compress(response_bytes)

    return Response(
        compressed_bytes, 
        headers = {
            'Content-Type': f'text/html; charset={encoding}',
            'Content-Encoding': 'gzip',
            'Cache-Control': 'max-age=60'
        })


@app.route("/set")
def legoSet():  # We don't want to call the function `set`, since that would hide the `set` data type.
    set_id = request.args.get("id")

    if set_id is None:
        set_id = "Default"
    
    start_time = perf_counter()
    cache_result = cache.get(set_id)
    if cache_result:
        print(f"Cache hit: {(perf_counter() - start_time)*1000} ms")
        return cache_result

    # Not in cache:
    with open("templates/set.html") as f:
        template = f.read()
    response = Response(template)
    cache.put(set_id, response) # Add to cache
    print(f"Cache miss: {(perf_counter() - start_time)*1000} ms")
    return response

@app.route("/api/set/bin")
def apiSetBin():
    set_id = request.args.get("id")

    db = Database()
    try:
        set = get_set_data(db, set_id)
    finally:
        db.close()

    binary = write_set_to_binary(set)

    return Response(binary, content_type="application/octet-stream")
    



@app.route("/api/set")
def apiSet():
    set_id = request.args.get("id")

    db = Database()
    try:
        result = get_set_data_for_html()
    finally:
        db.close()
    
    json_result = json.dumps(result, indent=4)
    return Response(json_result, content_type="application/json")

if __name__ == "__main__":
    app.run(port=5000, debug=True)

# Note: If you define new routes, they have to go above the call to `app.run`.

# Helper method to write a set to binary
def write_set_to_binary(set):
    # set_id - text / not null
    encoded_set_id = set["set_id"].encode("utf-8")
    encoded_set_id_length = len(encoded_set_id)
    binary = struct.pack(">H", encoded_set_id_length) # Storing the length of the following string
    binary += encoded_set_id

    # year - integer / can be null
    if set["year"] is None:
        # The single byte holds 0 if null
        binary += struct.pack(">B", 0)
    else:
        binary += struct.pack(">BH", 1, set["year"])
    
    # name - text / not null
    encoded_name = set["name"].encode("utf-8")
    encoded_name_length = len(encoded_name)
    binary += struct.pack(">H", encoded_name_length)
    binary += encoded_name

    # category - text / can be null
    if set["category"] is None:
        # The single byte holds 0 if null
        binary += struct.pack(">B", 0)
    else:
        encoded_category = set["category"].encode("utf-8")
        encoded_category_length = len(encoded_category)
        binary += struct.pack(">BH", 1, encoded_category_length)
        binary += encoded_category
    
    # preview_image_url - text / can be null
    if set["preview_image_url"] is None:
        # The single byte holds 0 if null
        binary += struct.pack(">B", 0)
    else:
        encoded_preview_image_url = set["preview_image_url"].encode("utf-8")
        encoded_preview_image_url_length = len(encoded_preview_image_url)
        binary += struct.pack(">BH", 1, encoded_preview_image_url_length)
        binary += encoded_preview_image_url

    for line in set["inventory"]:
        # brick_type_id - text / not null
        encoded_brick_type_id = line["brick_type_id"].encode("utf-8")
        encoded_brick_type_id_length = len(encoded_brick_type_id)
        binary += struct.pack(">H", encoded_brick_type_id_length)
        binary += encoded_brick_type_id

        # color_id - integer / not null
        # The color_id can be packed into an unsigned char, since values are 0-255
        binary += struct.pack(">B", line["color_id"])

        # count - integer / not null
        binary += struct.pack(">H", line["count"])

        # name - text / not null
        encoded_name = line["name"].encode("utf-8")
        encoded_name_length = len(encoded_name)
        binary += struct.pack(">H", encoded_name_length)
        binary += encoded_name

        # preview_image_url - text / can be null
        if line["preview_image_url"] is None:
            # The single byte holds 0 if null
            binary += struct.pack(">B", 0) 
        else:
            encoded_preview_image_url = set["preview_image_url"].encode("utf-8")
            encoded_preview_image_url_length = len(encoded_preview_image_url)
            binary += struct.pack(">BH", 1, encoded_preview_image_url_length)
            binary += encoded_preview_image_url

    return binary


def get_sets_list_html(db):
    rows = [] # List to hold the rows to avoid painter's algorithm

    start_time = perf_counter()
    db_result = db.execute_and_fetch_all("select id, name from lego_set order by id")

    for row in db_result:
        html_safe_id = html.escape(row[0])
        html_safe_name = html.escape(row[1])
        rows.append(f'<tr><td><a href="/set?id={html_safe_id}">{html_safe_id}</a></td><td>{html_safe_name}</td></tr>\n')
    
    print(f"Time to render all sets: {(perf_counter() - start_time)}")
    return rows

# Gets set data and inventory for the binary endpoint, doesn't html.escape()
def get_set_data(db, set_id):
    start_time = perf_counter()

    db_result_set = db.execute_and_fetch_all("SELECT year, name, category, preview_image_url FROM lego_set WHERE id = %s;",
            [set_id],
            prepare=True)

    result = db_result_set[0]
    year = result[0]
    name = result[1]
    category = result[2]
    preview_image_url = result[3]

    # Retrieve inventory and brick information
    # Using prepared statement to avoid SQL injection
    inventory = []
    db_result_inventory = db.execute_and_fetch_all("SELECT set_id, i.brick_type_id, i.color_id, count, name, preview_image_url " \
        "FROM (lego_inventory AS i INNER JOIN lego_brick AS b ON i.brick_type_id = b.brick_type_id AND i.color_id = b.color_id) " \
        "WHERE set_id = %s;",
        [set_id],
        prepare=True)
    
    for line in db_result_inventory:
        item = {}
        item["brick_type_id"] = line[1]
        item["color_id"] = line[2]
        item["count"] = line[3]
        item["name"] = line[4]
        item["preview_image_url"] = line[5]
        
        # Add the item to the inventory
        inventory.append(item)

    print(f"Time to retrieve set info and inventory: {perf_counter() - start_time}")

    return {
        "set_id": set_id,
        "year": year,
        "name": name,
        "category": category,
        "preview_image_url": preview_image_url,
        "inventory": inventory
    }

# Returns set data with inventory with data safe for html
def get_set_data_for_html(db, set_id):
    start_time = perf_counter()

    # Retrieve set information
    # Using prepared statement to avoid SQL injection
    result = db.execute_and_fetch_all(
        "SELECT year, name, category, preview_image_url FROM lego_set WHERE id = %s;",
        [set_id],
        prepare=True)[0]
    html_safe_year = result[0] # No need for html.escape() on integers
    html_safe_name = html.escape(result[1])
    html_safe_category = html.escape(result[2])
    html_safe_preview_image_url = html.escape(result[3])

    # Retrieve inventory and brick information
    # Using prepared statement to avoid SQL injection
    html_safe_inventory = []
    result_inventory = db.execute_and_fetch_all(
        "SELECT set_id, i.brick_type_id, i.color_id, count, name, preview_image_url " \
        "FROM (lego_inventory AS i INNER JOIN lego_brick AS b ON i.brick_type_id = b.brick_type_id AND i.color_id = b.color_id) " \
        "WHERE set_id = %s;",
        [set_id],
        prepare=True)
    
    for item in result_inventory:
        html_safe_item = {}
        html_safe_item["brick_type_id"] = html.escape(item[1])
        html_safe_item["color_id"] = item[2]
        html_safe_item["count"] = item[3]
        html_safe_item["name"] = html.escape(item[4])
        html_safe_item["preview_image_url"] = html.escape(item[5])
        
        # Add the item to the inventory
        html_safe_inventory.append(html_safe_item)
    print(f"Time to retrieve set info and inventory: {perf_counter() - start_time}")

    return {
        "set_id": set_id,
        "year": html_safe_year,
        "name": html_safe_name,
        "category": html_safe_category,
        "preview_image_url": html_safe_preview_image_url,
        "inventory": html_safe_inventory
    }
    
