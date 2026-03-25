from server import get_sets_list_html, get_set_data

class MockDatabase:
    def __init__(self, db_results, expected_queries):
        self.db_results = db_results
        self.expected_queries = expected_queries
        self.index = 0

    def execute_and_fetch_all(self, query, vars=None, **kwargs):
        if (query != self.expected_queries[self.index]):
            print("MockDatabase: Unexpected query!")
            print(f"Query: '{query}'")
            print(f"Expected: '{self.expected_queries[self.index]}")
            return ()
        
        result = self.db_results[self.index]
        self.index += 1
        return result
        
    def close():
        return
    
def test_get_sets_list_html():
    # Arrange
    # Setting up the mock database with return values
    set_id1 = "123-ab"
    name1 = "Lego set 1"
    set_id2 = "456-cd"
    name2 = "Lego set 2"

    db = MockDatabase(
        db_results=[((set_id1, name1), (set_id2, name2))],
        expected_queries=["select id, name from lego_set order by id"]
        )

    # Act
    # Performing the function call
    result = get_sets_list_html(db)

    # Assert
    # Check that the result is matching what we expect
    expected_result = [
        f'<tr><td><a href="/set?id={set_id1}">{set_id1}</a></td><td>{name1}</td></tr>\n',
        f'<tr><td><a href="/set?id={set_id2}">{set_id2}</a></td><td>{name2}</td></tr>\n',
    ]

    if result == expected_result:
        print("test_get_sets_list_html: Test passed!")
    else:
        print("test_get_sets_list_html: Test failed! Unexpected result.")


def test_get_set_data():
    # Arrange
    # Setting up the mock database with return values
    set_id = "123-ab"

    year = 1996
    name = "Lego set 1"
    category = "Toys"
    preview_image_url = "example.com"

    line = {
        "brick_type_id": "brick-1",
        "color_id": 0,
        "count": 1,
        "name": "Brick 1",
        "preview_image_url": "example.com/line1"
    }
    inventory = [line]

    db = MockDatabase(
        db_results=[
            ((year, name, category, preview_image_url),),
            ((set_id, line["brick_type_id"], line["color_id"], line["count"], line["name"], line["preview_image_url"]),)
        ],
        expected_queries=[
            "SELECT year, name, category, preview_image_url FROM lego_set WHERE id = %s;",
            "SELECT set_id, i.brick_type_id, i.color_id, count, name, preview_image_url " \
                "FROM (lego_inventory AS i INNER JOIN lego_brick AS b ON i.brick_type_id = b.brick_type_id AND i.color_id = b.color_id) " \
                "WHERE set_id = %s;"
        ]
        )

    # Act
    # Performing the function call
    result = get_set_data(db, set_id)

    # Assert
    # Check that the result is matching what we expect
    expected_result = {
        "set_id": set_id,
        "year": year,
        "name": name,
        "category": category,
        "preview_image_url": preview_image_url,
        "inventory": inventory
    }

    if result == expected_result:
        print("test_get_set_data: Test passed!")
    else:
        print("test_get_set_data: Test failed! Unexpected result.")


if __name__ == "__main__":
    test_get_sets_list_html()
    test_get_set_data()