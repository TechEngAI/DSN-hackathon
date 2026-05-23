def format_relational_row_for_chroma(business_row: dict, domain: str = "yelp") -> dict:
    """
    Transforms a joined relational database row containing business metadata,
    categories, and attributes into a flat shape optimized for ChromaDB collections.
    """
    # 1. Extract Unique ID
    item_id = str(business_row.get("business_id"))
    
    # 2. Build the Semantic Document (Natural Language Prose)
    name = business_row.get("name", "Unknown Business")
    categories = business_row.get("categories", "Uncategorized")
    city = business_row.get("city", "Unknown City")
    state = business_row.get("state", "")
    
    # Format attributes dictionary into a readable string snippet
    attributes_dict = business_row.get("attributes", {})
    attr_strings = [f"{k}: {v}" for k, v in attributes_dict.items()]
    attributes_text = ", ".join(attr_strings) if attr_strings else "None listed"
    
    document_text = (
        f"Name: {name}. "
        f"Category: {categories}. "
        f"Location: {city}, {state}. "
        f"Features: {attributes_text}."
    )
    
    # 3. Build the Flat Metadata Dictionary (Strict primitive types only)
    # ChromaDB metadata expressions do not support nested dicts or arrays.
    metadata = {
        "domain": domain,
        "city": city,
        "state": state,
        "stars": float(business_row.get("stars", 0.0)),
        "is_open": bool(business_row.get("is_open", True)),
        "review_count": int(business_row.get("review_count", 0)),
        # Pull a primary category anchor for fast indexing/filtering
        "primary_category": categories.split(",")[0].strip() if categories else "General"
    }
    
    return {
        "id": item_id,
        "document": document_text,
        "metadata": metadata
    }

# Quick validation mock execution
if __name__ == "__main__":
    mock_sql_row = {
        "business_id": "Pns2l4eNsfO8kk83dixA6A",
        "name": "Abby Rappoport, LAC, CMQ",
        "city": "Santa Barbara",
        "state": "CA",
        "stars": 5.0,
        "review_count": 7,
        "is_open": 1,
        "categories": "Doctors, Nutritionists",
        "attributes": {"ByAppointmentOnly": "True", "BusinessAcceptsCreditCards": "True"}
    }
    
    chroma_ready_payload = format_relational_row_for_chroma(mock_sql_row)
    print("--- CHROMA DOCUMENT SHAPE ---")
    print(chroma_ready_payload["document"])
    print("\n--- CHROMA METADATA SHAPE ---")
    print(chroma_ready_payload["metadata"])
