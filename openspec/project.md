# Project Context

## Purpose
This project is to write code that will look at cookidoo recipes (Thermomix) in a relational Database and make user recommendations about meals based on his query.

## Tech Stack
- This project is going to use Google Cloud Heavily. You will take the service account JSON file which already has the necessary permissions to operate on Google Cloud.
- The relational Database that has cookidoo recipes is Google Cloud Alloy DB. There are a number of tables in this DB which were created as below:
```
CREATE EXTENSION IF NOT EXISTS vector;

        CREATE TABLE IF NOT EXISTS recipes (
            id SERIAL PRIMARY KEY,
            recipe_id VARCHAR(255) UNIQUE NOT NULL,
            title TEXT,
            url TEXT,
            prep_time_minutes INTEGER,
            cook_time_minutes INTEGER,
            total_time_minutes INTEGER,
            servings INTEGER,
            difficulty VARCHAR(50),
            nutrition_calories_kcal FLOAT,
            nutrition_protein_g FLOAT,
            nutrition_carbs_g FLOAT,
            nutrition_fat_g FLOAT,
            rating FLOAT,
            rating_count INTEGER,
            image_url TEXT,
            scraped_at TIMESTAMP,
            embedding vector(768)
        );

        CREATE TABLE IF NOT EXISTS recipe_thermomix_versions (
            id SERIAL PRIMARY KEY,
            recipe_id VARCHAR(255) REFERENCES recipes(recipe_id),
            version VARCHAR(50)
        );

        CREATE TABLE IF NOT EXISTS recipe_ingredients (
            id SERIAL PRIMARY KEY,
            recipe_id VARCHAR(255) REFERENCES recipes(recipe_id),
            ingredient TEXT
        );

        CREATE TABLE IF NOT EXISTS recipe_steps (
            id SERIAL PRIMARY KEY,
            recipe_id VARCHAR(255) REFERENCES recipes(recipe_id),
            step_number INTEGER,
            step_description TEXT
        );

        CREATE TABLE IF NOT EXISTS recipe_tags (
            id SERIAL PRIMARY KEY,
            recipe_id VARCHAR(255) REFERENCES recipes(recipe_id),
            tag VARCHAR(255)
        );

        CREATE TABLE IF NOT EXISTS recipe_dietary_tags (
            id SERIAL PRIMARY KEY,
            recipe_id VARCHAR(255) REFERENCES recipes(recipe_id),
            dietary_tag VARCHAR(255)
        );
```
As you can tell the `recipes` table has all the vector embeddings needed. The embeddings were created by the following python code
```
    for recipe in recipes:
        title = recipe.get("title", "")
        ingredients = ", ".join(recipe.get("ingredients", []))
        steps = ", ".join(recipe.get("steps", []))
        tags = ", ".join(recipe.get("tags", []))
        rating = recipe.get("rating", 0)
        rating_count = recipe.get("rating_count", 0)
        texts_for_embedding.append(
            f"Title: {title}\nIngredients: {ingredients}\nSteps: {steps}\nTags: {tags}\nRating: {rating} out of 5 stars from {rating_count} reviews."
        )
```
- Write all the code in Python. Use the python interpreter available at `/Users/gaikwadk/miniforge3/bin/python3` if you need to test.
- We will be using Gemini for all the work related to AI.
- Since, this is a relational Database I want to make use of NL2SQL in addition to AI to make recommendations to users for his queries. e.g., if a users asks for a vegetarian recipes, you can look at the `ingredients` or `tags` first to make sure you first only retrieve vegetarian recipes and then make recommendations based on AI.

## Project Conventions

### Code Style
Use standard python coding conventions

### Architecture Patterns
Make use of python modules and `requirements.txt` file

### Testing Strategy
Write tests to sanity check your results. e.g., you can write queries like 'give me 5 drink` recipes and then you can make sure that all the results are drinks (and not meals)

### Git Workflow
use git flow style branch name conventions.

## Domain Context
This is purely a personal project to make meal planning easy since I use cookidoo (Thermomix) heavily. I have the TM6 model, so make sure that all the results retrieved are TM6 compatible unless specified else explicitly.

## Important Constraints
I am running on a VPN so it may be possible that we'll have connetion issues.

## External Dependencies
The main extenal system here is Google Cloud. More specifically Alloy DB and verted AI (Gemini)
