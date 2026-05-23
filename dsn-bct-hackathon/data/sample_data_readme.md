# Sample Data For Judges

`sample_data.json` contains a compact, ready-to-run dataset for the FastAPI recommendation system. It includes 15 indexed business-style records, 30 Nigerian-style reviews, and 10 test scenarios split across Task A and Task B. The data is designed to work without the full Yelp or Amazon datasets.

## Test Users

- `user_001_naija_foodie`: generous Lagos-style foodie who loves suya, buka food, jollof, pepper, and practical products.
- `user_002_lagos_explorer`: likes Lagos cafes, late-night food, premium restaurants, WiFi, ambience, and stylish lifestyle items.
- `user_003_abuja_critic`: more analytical Abuja reviewer who rewards clean service and quality but notes weak sauce, dry food, or small portions.
- `user_004_ph_foodlover`: Port Harcourt seafood and native soup lover who prefers bold spice and fresh fish.
- `user_005_ibadan_local`: Ibadan comfort-food reviewer who likes dodo, palmwine, local chill spots, and useful lifestyle items.

## How To Use

When the full Yelp files are missing, startup loads `data/sample_data.json`. The `test_scenarios` section contains request bodies you can paste directly into curl, Postman, or the FastAPI docs.

Task A endpoint:

```bash
curl -X POST http://localhost:8080/task-a/generate-review \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user_001_naija_foodie","item_id":"NGBIZZ0000000000000003","persona":{},"language_mode":"naija"}'
```

```bash
curl -X POST http://localhost:8080/task-a/generate-review \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user_004_ph_foodlover","item_id":"NGBIZZ0000000000000004","persona":{},"language_mode":"pidgin"}'
```

Task B endpoint:

```bash
curl -X POST http://localhost:8080/task-b/recommend \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user_001_naija_foodie","query":"spicy suya and local buka food","top_k":5,"is_cold_start":false,"language_mode":"naija"}'
```

```bash
curl -X POST http://localhost:8080/task-b/recommend \
  -H "Content-Type: application/json" \
  -d '{"user_id":"brand_new_user_001","query":"jollof rice and pepper soup in Abuja","top_k":5,"is_cold_start":true,"language_mode":"naija","user_responses":{"1":"jollof rice and pepper soup","2":"sit-down restaurants","3":"medium budget","4":"try new things","5":"Abuja"}}'
```

```bash
curl -X POST http://localhost:8080/task-b/recommend \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user_003_abuja_critic","query":"beauty products and good food","top_k":5,"is_cold_start":false,"language_mode":"naija"}'
```

For production use, add the full Yelp business and review files to `data/` with their expected filenames. The app will use those larger files automatically when they are present.
