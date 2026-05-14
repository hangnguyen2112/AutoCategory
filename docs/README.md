# AutoCategory Documentation

**Version:** 1.0.0  
**Last Updated:** 2026-05-06

---

## 📚 Documentation Index

### For Developers

1. **[INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md)** - **START HERE**
   - Complete guide for frontend developers
   - API endpoints reference
   - Code examples (React, Vanilla JS)
   - Integration patterns & best practices
   - **Target:** Frontend developers integrating classification & generation APIs

2. **[DATA_STANDARDS.md](./DATA_STANDARDS.md)** - **DATA MANAGEMENT**
   - Data format specifications
   - Validation rules
   - Import/export guidelines
   - Quality standards
   - **Target:** Data engineers, admin users

### For Understanding the System

3. **[MARKETPLACE_STYLE.md](../MARKETPLACE_STYLE.md)** - **STYLE GUIDE**
   - Why marketplace casual style (not e-commerce formal)
   - Vietnamese slang dictionary
   - Prompt engineering decisions
   - Before/after examples
   - **Target:** Developers, product managers

4. **[FRONTEND_API_GUIDE.md](../FRONTEND_API_GUIDE.md)** - **API OVERVIEW**
   - Quick API reference
   - Request/response formats
   - Integration examples
   - **Target:** Frontend developers (quick reference)

### For Planning & Architecture

5. **[ADMIN_SYSTEM_PLAN.md](../ADMIN_SYSTEM_PLAN.md)** - **ENTERPRISE PLAN**
   - Complete enterprise admin system architecture
   - Database schema
   - Dashboard mockups
   - Authentication & authorization
   - Training pipeline
   - Monitoring stack
   - 12-week implementation roadmap
   - **Target:** Tech leads, architects, project managers

6. **[feedback_learning_plan.md](../feedback_learning_plan.md)** - **TRAINING PLAN**
   - Feedback learning system design
   - Data collection from user corrections
   - Model retraining pipeline
   - **Target:** ML engineers, data scientists

7. **[image_to_text_plan.md](../image_to_text_plan.md)** - **IMAGE GEN PLAN**
   - Image-to-text generation planning
   - Vision model selection
   - Implementation details
   - **Target:** ML engineers

8. **[category_pipeline.md](../category_pipeline.md)** - **PIPELINE OVERVIEW**
   - Classification pipeline architecture
   - Decision thresholds
   - Service flow
   - **Target:** Developers, architects

### Logs & Updates

9. **[UPDATE_LOG.md](../UPDATE_LOG.md)** - **CHANGELOG**
   - What changed and why
   - Before/after examples
   - Migration notes
   - **Target:** All developers

10. **[plan.md](../plan.md)** - **PROJECT PLAN**
    - Original project planning notes
    - Feature roadmap
    - **Target:** Project managers

---

## 🎯 Quick Navigation

### "I want to..."

| Goal | Document |
|------|----------|
| Integrate classification API | [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md) |
| Understand API responses | [FRONTEND_API_GUIDE.md](../FRONTEND_API_GUIDE.md) |
| Import/export category data | [DATA_STANDARDS.md](./DATA_STANDARDS.md) |
| Understand marketplace style | [MARKETPLACE_STYLE.md](../MARKETPLACE_STYLE.md) |
| Build admin dashboard | [ADMIN_SYSTEM_PLAN.md](../ADMIN_SYSTEM_PLAN.md) |
| Set up training pipeline | [feedback_learning_plan.md](../feedback_learning_plan.md) |
| Implement image generation | [image_to_text_plan.md](../image_to_text_plan.md) |
| Understand classification flow | [category_pipeline.md](../category_pipeline.md) |
| See what's changed | [UPDATE_LOG.md](../UPDATE_LOG.md) |

---

## 🚀 Getting Started

### For Frontend Developers

1. Read [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md) - Complete integration guide
2. Get API key from admin
3. Check [FRONTEND_API_GUIDE.md](../FRONTEND_API_GUIDE.md) for quick reference
4. Start with Pattern 1 (User Writes → Auto-Classify)
5. Implement Pattern 2 (Image Upload → Auto-Generate)

### For Backend/ML Developers

1. Read [ADMIN_SYSTEM_PLAN.md](../ADMIN_SYSTEM_PLAN.md) - System architecture
2. Understand [category_pipeline.md](../category_pipeline.md) - Pipeline flow
3. Review [MARKETPLACE_STYLE.md](../MARKETPLACE_STYLE.md) - Why casual style
4. Plan training with [feedback_learning_plan.md](../feedback_learning_plan.md)
5. Implement image gen with [image_to_text_plan.md](../image_to_text_plan.md)

### For Data Engineers

1. Read [DATA_STANDARDS.md](./DATA_STANDARDS.md) - Data specifications
2. Validate data before import
3. Follow quality guidelines
4. Set up category sync pipeline

### For Project Managers

1. Review [ADMIN_SYSTEM_PLAN.md](../ADMIN_SYSTEM_PLAN.md) - Full requirements
2. Check 12-week roadmap
3. Understand costs ($60-110/month)
4. Prioritize phases based on business needs

---

## 📊 System Overview

### Core Features (Current)

1. **Auto-Classification** - Classify products to categories
   - Understanding via LLM (gemma4-e4b)
   - Embedding via nomic-embed-text
   - Vector search via Qdrant
   - Reranking via LLM
   - 4 decision types: auto_assign, preselect, suggest_top3, manual_select

2. **Auto-Generation** - Generate ad content from images
   - Vision model: llama3.2-vision:11b or llava:13b
   - Generates: title, description, price suggestion, category
   - Marketplace casual style
   - Prefers single image for performance

### Enterprise Features (Planned - ADMIN_SYSTEM_PLAN.md)

3. **Admin Dashboard** - System management UI
   - User management & API keys
   - System monitoring & control
   - Configuration management
   - Training data management

4. **Training Pipeline** - Continuous improvement
   - Collect feedback from user corrections
   - Validate & clean data
   - Retrain models
   - A/B testing

5. **Monitoring** - System health & metrics
   - Prometheus + Grafana
   - API metrics, model metrics, system metrics
   - Alerts & notifications

---

## 🔧 Tech Stack

### Current
- **Backend:** FastAPI (Python 3.12)
- **LLM:** gemma4-e4b via llama-server
- **Embedding:** nomic-embed-text via Ollama
- **Vector DB:** Qdrant
- **Containerization:** Docker + docker-compose

### Planned (Enterprise)
- **Database:** PostgreSQL
- **Cache:** Redis
- **Monitoring:** Prometheus + Grafana
- **Frontend:** React + Tailwind CSS
- **Auth:** JWT + RBAC

---

## 📝 Documentation Standards

All documentation in this project follows these conventions:

### File Naming
- `UPPERCASE_WORDS.md` - Major guides, standards, plans
- `lowercase_words.md` - Technical notes, logs, minor docs

### Structure
- **Version & Date** at top
- **Table of Contents** for long docs
- **Code Examples** with syntax highlighting
- **Visual Indicators:** ✅ ❌ ⚠️ for do/don't/warning

### Language
- **Vietnamese** for user-facing content & examples
- **English** for technical terms & code
- **Mixed** for documentation (English structure, Vietnamese examples)

---

## 🤝 Contributing

### Adding New Documentation

1. Create file in appropriate location:
   - `/docs/` for guides, standards, references
   - Root for plans, logs, overviews

2. Follow naming conventions

3. Update this README index

4. Add cross-references to related docs

### Updating Existing Documentation

1. Update version number & date
2. Add changes to changelog section (if exists)
3. Update cross-references if structure changed
4. Notify team of significant changes

---

## 📞 Support

**Questions about documentation?**
- Check this index first
- Search within specific documents
- Contact development team

**Found outdated information?**
- Create issue or PR
- Tag with `documentation` label
- Mention specific file & section

---

## 🗺️ Roadmap

### Phase 1: Core Features (✅ Complete)
- Auto-classification
- Auto-generation
- Basic API

### Phase 2: Enterprise (🚧 In Planning)
- Admin dashboard
- Authentication & API keys
- Training pipeline
- Monitoring

### Phase 3: Advanced (📅 Planned)
- Multi-language support
- Advanced analytics
- Custom models per tenant
- Real-time feedback loop

---

**Last Updated:** 2026-05-06  
**Maintained By:** AutoCategory Team
