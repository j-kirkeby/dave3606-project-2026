# DAVE3606 - Project Report
Group member: Jarle Kirkeby (jakir1503@oslomet.no)

## Task 1: Add database constraints
### Table: `lego_brick`
This table has four columns: 
* `brick_type_id` (text)
* `color_id` (integer)
* `name` (text)
* `preview_image_url` (text)

`preview_image_url` and `name` are not suitable primary keys because their values might change, and they could also not be unique.

`brick_type_id` and `color_id` we can assume will not change, but only a combination of the two would be unique. So we need to make a decision on the order. The first value in the primary key will always be indexed, but the second will only have an automatic index when the searched in combination with the first. What will be the more common pattern?
* Searching for all bricks of a certain color? Then making the first value of the composite key `color_id` would make sense, since it would be sorted by this value first.
* Searching for all the colors for a certain brick? Then we would want the first value to be `brick_type_id`.

I decided to make the composite key `brick_type_id`-`color_id` because I think the second pattern will be more common. Users will look up sets, then go to the individual bricks and look at color variations for that brick. Finding all bricks of a certain color is a more niche request, but an index can be made for the color column if necessary.

To add the primary key I connected to the database, and used the command:
```
ALTER TABLE lego_brick ADD PRIMARY KEY (brick_type_id, color_id);
```

### Table: `lego_inventory`
This table also has four columns:
* `set_id` (text)
* `brick_type_id` (text)
* `color_id` (integer)
* `count` (integer)

The `count` value is not an identifier as many combinations of sets, bricks and color can have the same count. So here it is clear that the primary key should be some combination of `set_id`, `brick_type_id` and `color_id`. I have already decided how to best combine brick and color, so where should we put the set?
* Sort by set first? Then we will have the table sorted by set -> brick -> color. Which is suitable if the primary use case is to retrieve sets, then their bricks and color.
* Sort by brick/color first? Then we would expect users to look for specific bricks and colors, and then wanting to find all sets that use them.

Sorting by set seems to support the most common use case: "finding a set, and then viewing the inventory for that set". The other option is more niche, but can be supported by manually adding indexes.

```
ALTER TABLE lego_inventory ADD PRIMARY KEY (set_id, brick_type_id, color_id);
```
When I tried to add this constraint, I got an error:
```
ERROR:  could not create unique index "lego_inventory_pkey"
DETAIL:  Key (set_id, brick_type_id, color_id)=(10218-1, 48729b, 11) is duplicated.
```
I investigated the specific IDs and found that the set had multiple counts for the same brick:
```
lego-db=# SELECT * FROM lego_inventory WHERE set_id = '10218-1' AND brick_type_id = '48729b';
 set_id  | brick_type_id | color_id | count 
---------+---------------+----------+-------
 10218-1 | 48729b        |       11 |     2
 10218-1 | 48729b        |       86 |     2
 10218-1 | 48729b        |       11 |     1
 10218-1 | 48729b        |       86 |     1
(4 rows)
```

To solve this we need to either change the data (combine the lines into single lines with 3 count for each). If we don't we must introduce a surrogate key since there are no valid natural keys for the table.

I chose to combine the rows since I don't consider it necessary to store multiple counts for a combination of set/brick/color. If this is necessary a bag (or brick group) id should be added to group bricks within a set together.

```
DELETE FROM lego_inventory WHERE set_id = '10218-1' AND brick_type_id = '48729b';
INSERT INTO lego_inventory VALUES ('10218-1', '48729b', 11, 3), ('10218-1', '48729b', 86, 3);

# Etter endring:
 set_id  | brick_type_id | color_id | count 
---------+---------------+----------+-------
 10218-1 | 48729b        |       11 |     3
 10218-1 | 48729b        |       86 |     3
(2 rows)
```
After combining I found that there were more rows in the table where the same issue prevented creating the primary key. So I used this transaction to combine all of them:
```
BEGIN;
CREATE TEMP TABLE temp_lego_inventory AS (SELECT set_id, brick_type_id, color_id, SUM(count) as count FROM lego_inventory GROUP BY set_id, brick_type_id, color_id);
# Feedback from server: SELECT 1199929

DELETE FROM lego_inventory;
# Feedback form server: DELETE 1301257

INSERT INTO lego_inventory (set_id, brick_type_id, color_id, count) SELECT set_id, brick_type_id, color_id, count FROM temp_lego_inventory;
# Feedback from server: INSERT 0 1199929

DROP TABLE temp_lego_inventory;
COMMIT;
```
Based on the feedback we can see the `1301257 - 1199929 = 101318` lines where combined. Which is around 7% if the table, so this is a pretty big decision to make - maybe the separation of these values had some meaning in the original data which has now been removed (but that link was already severed when the data was changed into its current state for the assignment before the lines were combined).

I was able to add the primary key after making these changes.

### Table: `lego_set`
This table has an `id` column that already fulfills the requirements for a primary key, so I added that as the primary key:
```
ALTER TABLE lego_set ADD PRIMARY KEY (id);
```

## Task 2: Design indexes for flexible queries
### Query: Which LEGO sets contain a specific brick type regardless of color?
Testing with the first, middle (OFFSET 500000) and last `brick_type_id` in the `lego_inventory` table: *29bc01*, *3062*, *sw0517a*
```
SELECT set_id FROM lego_inventory WHERE brick_type_id = '29bc01';
# (32 rows)
# Time: 131.496 ms

SELECT set_id FROM lego_inventory WHERE brick_type_id = '3062';
# (7640 rows)
# Time: 123.281 ms

SELECT set_id FROM lego_inventory WHERE brick_type_id = 'sw0517a';
# (1 row)
# Time: 130.074 ms
```
The query will have to go visit each `set_id` since that's the first value in the composite key. But within each set the rows are sorted on `brick_type_id`, so the database should be able to quickly check if the brick is in that set or not (binary search). If the composite key had `brick_type_id` as its first value this search would be optimized for (table would be sorted by bricktype).

I added an index for `brick_type_id`:
```
CREATE INDEX ON lego_inventory(brick_type_id);
```
And re-tested the queries:
```
SELECT set_id FROM lego_inventory WHERE brick_type_id = '29bc01';
# (32 rows)
# Time: 4.305 ms

SELECT set_id FROM lego_inventory WHERE brick_type_id = '3062';
# (7640 rows)
# Time: 88.073 ms

SELECT set_id FROM lego_inventory WHERE brick_type_id = 'sw0517a';
# (1 row)
# Time: 0.440 ms
```
We see quite large improvements for the brick types with few results as the database is quickly able to find the bricks, and then get the sets for each. For the second result the improvement was OK, but would have expected more. Maybe if I indexed on both `brick_type_id` and `set_id` I would see more improvement:
```
CREATE INDEX ON lego_inventory(brick_type_id, set_id);

SELECT set_id FROM lego_inventory WHERE brick_type_id = '29bc01';
# (32 rows)
# Time: 0.417 ms

SELECT set_id FROM lego_inventory WHERE brick_type_id = '3062';
# (7640 rows)
# Time: 1.930 ms

SELECT set_id FROM lego_inventory WHERE brick_type_id = 'sw0517a';
# (1 row)
# Time: 0.440 ms
```
This improved the queries (especially the second) because now the database also knows the sets are ordered in the index and can quickly get all the sets for a brick type in order.

### Query: Which LEGO sets contain bricks of a specific color, regardless of type?
I used a query to find which `color_id`s were most used, least used and median used:
```
SELECT color_id, COUNT(set_id) AS count FROM lego_inventory GROUP BY color_id ORDER BY count DESC; 
# (212 rows)
# Most used: 11 (205682 times)
# Least used: 132 (1 time) -- others also had 1 occurence

# Using offset to find the 106th element
SELECT color_id, COUNT(set_id) AS count FROM lego_inventory GROUP BY color_id ORDER BY count DESC LIMIT 1 OFFSET 105;
# Median used: 102 (68 times) 
```
So we will use these `color_id`s to test the query before and after adding the index: *11*, *102*, *132*.
```
SELECT set_id FROM lego_inventory WHERE color_id = 11;
# Time: 424.356 ms

SELECT set_id FROM lego_inventory WHERE color_id = 102;
# Time: 135.844 ms

SELECT set_id FROM lego_inventory WHERE color_id = 132;
# Time: 139.596 ms
```
Now we add an index for `(color_id, set_id)` to speed up the query and re-test:
```
CREATE INDEX ON lego_inventory(color_id, set_id);

SELECT set_id FROM lego_inventory WHERE color_id = 11;
# Time: 35.528 ms

SELECT set_id FROM lego_inventory WHERE color_id = 102;
# Time: 0.332 ms

SELECT set_id FROM lego_inventory WHERE color_id = 132;
# Time: 0.409 ms
```
Again we see a large improvement, and for colors used in few sets the database can resolve the query almost instantly.



