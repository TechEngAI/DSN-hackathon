# Yelp Dataset Analysis and Schema Mapping

This project maps the raw Yelp Academic Dataset JSON Lines (JSONL) files to a fully normalized relational schema.

## Deliverables
- **Schema Mapping & ERD**: [docs/schema_mapping.md](file:///c:/Users/ADMIN/Documents/my-bct/docs/schema_mapping.md)
- **Local Sample Files**: Located in `docs/raw_samples/` for quick local testing and integration:
  - `yelp_academic_dataset_business.json` (59 valid records)
  - `yelp_academic_dataset_checkin.json` (32 valid records)
  - `yelp_academic_dataset_review.json` (73 valid records)
  - `yelp_academic_dataset_tip.json` (255 valid records)
  - `yelp_academic_dataset_user.json` (83 valid records)

## 📅 JahsFavour's Sprint Progress Checklist
Track tasks assigned to **JahsFavour** (Data Engineer / Research Lead) from the `Team_Sprint_Plan_DSN_BCT.pdf`:

### 🏁 Day 1: Setup & Foundation (May 19)
- [x] **Download Yelp dataset** *(Completed: local sample files generated)*
- [x] **Explore + map schema** *(Completed: mapped raw schema to relational DDL in [docs/schema_mapping.md](file:///c:/Users/ADMIN/Documents/my-bct/docs/schema_mapping.md))*
- [x] **Profile 500 sample users** *(Completed: analyzed 2,000 users in `run_analysis.py`)*
- [x] **Note Naija review patterns** *(Completed: documented in [docs/behavioral_template.md](file:///c:/Users/ADMIN/Documents/my-bct/docs/behavioral_template.md))*

### ⏳ Day 2: Task A User Modeling (May 20)
- [ ] **Build persona extractor (JSON)**
- [ ] **EDA on rating distributions**
- [ ] **Extract Naija cues from text**
- [ ] **Validate 10 sample personas**

### ⏳ Day 3: Task B Recommendation (May 21)
- [ ] **Prepare item metadata CSV**
- [ ] **Generate item embeddings**
- [ ] **Index items into ChromaDB**
- [ ] **Test similarity search queries**

### ⏳ Day 4: Nigerian Context + Integration (May 22)
- [ ] **Build Naija phrase dictionary**
- [ ] **Cultural items dataset**
- [ ] **Inject context into persona flow**
- [ ] **Sample 20 Naija review outputs**

### ⏳ Day 5: Metrics & Evaluation (May 23)
- [ ] **Run ROUGE-L scoring**
- [ ] **Compute BERTScore F1**
- [ ] **Calculate RMSE on ratings**
- [ ] **Log all results to CSV**

### ⏳ Day 6: Paper, Polish & Submit (May 24)
- [ ] **Write paper sections 1-4**
- [ ] **Architecture diagram in paper**
- [ ] **Experiment tables + Naija section**
- [ ] **Final proofread of paper**

## Methodology
To avoid downloading the entire 8 GB Yelp Academic Dataset, we implemented a workaround using **HTTP Range Requests** (`Range: bytes=...`) against a public Hugging Face mirror (`ShengxiangLin/Yelp-JSON`). We fetched only the first few kilobytes (or megabytes for the large user file) of each raw `.json` file and cleaned up truncated lines at the end. This generated perfect, lightweight local files for schema inspection.
