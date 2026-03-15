import json
import html
import psycopg
import gzip
from flask import Flask, Response, request
from time import perf_counter

app = Flask(__name__)

DB_CONFIG = {
    "host": "localhost",
    "port": 9876,
    "dbname": "lego-db",
    "user": "lego",
    "password": "bricks",
}


@app.route("/")
def index():
    with open("templates/index.html").read() as f:
        template = f.read()
        
    return Response(template)


@app.route("/sets")
def sets():
    valid_encodings = ['UTF-16-LE', 'UTF-16-BE', 'UTF-32-LE', 'UTF-32-BE', 'UTF-16', 'UTF-8']

    requested_encoding = request.args.get('encoding', default='UTF-8')

    encoding = requested_encoding if requested_encoding in valid_encodings else 'UTF-8' 

    with open("templates/sets.html").read() as f:
        template = f.read()
    rows = [] # List to hold the rows to avoid painter's algorithm

    start_time = perf_counter()
    conn = psycopg.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("select id, name from lego_set order by id")
            for row in cur.fetchall():
                html_safe_id = html.escape(row[0])
                html_safe_name = html.escape(row[1])
                rows.append(f'<tr><td><a href="/set?id={html_safe_id}">{html_safe_id}</a></td><td>{html_safe_name}</td></tr>\n')
        print(f"Time to render all sets: {perf_counter() - start_time}")
    finally:
        conn.close()

    result = "".join(rows) # Combine the strings efficiently, all at once
    page_html = template.replace("{ROWS}", result).replace("{ENCODING}", encoding)

    # Manually encode the bytes
    response_bytes = page_html.encode(encoding)
    compressed_bytes = gzip.compress(response_bytes)

    return Response(
        compressed_bytes, 
        headers = {
            'Content-Type': f'text/html; charset={encoding}',
            'Content-Encoding': 'gzip'      
        })


@app.route("/set")
def legoSet():  # We don't want to call the function `set`, since that would hide the `set` data type.
    with open("templates/set.html").read() as f:
        template = f.read()
    return Response(template)


@app.route("/api/set")
def apiSet():
    set_id = request.args.get("id")
    result = {"set_id": set_id}
    json_result = json.dumps(result, indent=4)
    return Response(json_result, content_type="application/json")


if __name__ == "__main__":
    app.run(port=5000, debug=True)

# Note: If you define new routes, they have to go above the call to `app.run`.
