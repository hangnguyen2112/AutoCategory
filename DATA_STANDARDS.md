# Data Standards - AutoCategory

## Overview

This document defines the data formats, validation rules, and quality standards for the AutoCategory system.

---

## Table of Contents

1. [Category Data Format](#category-data-format)
2. [Training Data Format](#training-data-format)
3. [Classification Input Format](#classification-input-format)
4. [Validation Rules](#validation-rules)
5. [Data Quality Guidelines](#data-quality-guidelines)
6. [Import/Export Formats](#importexport-formats)

---

## Category Data Format

### JSON Structure

```json
{
  "id": 123,
  "name": "Điện thoại > Apple iPhone > iPhone 14 Series",
  "slug": "dien-thoai-apple-iphone-14-series",
  "parent_id": 122,
  "level": 3,
  "is_leaf": true,
  "is_active": true,
  "description": "Các sản phẩm thuộc dòng iPhone 14",
  "keywords": ["iphone 14", "apple", "smartphone"],
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### Field Specifications

| Field | Type | Required | Max Length | Description |
|-------|------|----------|------------|-------------|
| `id` | integer | Yes | - | Unique category identifier |
| `name` | string | Yes | 200 | Full category path separated by ' > ' |
| `slug` | string | Yes | 200 | URL-friendly version of name |
| `parent_id` | integer | No | - | Parent category ID (null for root) |
| `level` | integer | Yes | - | Depth in category tree (0 = root) |
| `is_leaf` | boolean | Yes | - | True if category has no children |
| `is_active` | boolean | Yes | - | True if category is visible |
| `description` | string | No | 1000 | Category description in Vietnamese |
| `keywords` | array[string] | No | - | Search keywords for category |
| `created_at` | datetime | Yes | - | ISO 8601 format |
| `updated_at` | datetime | Yes | - | ISO 8601 format |

### Category Tree Rules

1. **Root Categories:** `parent_id` is `null`, `level` is `0`
2. **Child Categories:** Must reference valid parent, `level = parent.level + 1`
3. **Leaf Categories:** `is_leaf = true`, cannot have children
4. **Active Status:** If parent is inactive, all children should be inactive
5. **Name Path:** Must include full path from root, separated by ` > `

Example hierarchy:
```
Điện thoại (id=1, level=0, parent_id=null)
└─ Apple iPhone (id=10, level=1, parent_id=1)
   └─ iPhone 14 Series (id=123, level=2, parent_id=10, is_leaf=true)
```

---

## Training Data Format

### JSON Structure

```json
{
  "id": 456,
  "title": "iPhone 14 Pro Max 256GB Deep Purple",
  "description": "iPhone 14 Pro Max with 256GB storage, Deep Purple color. Brand new, sealed box with Apple warranty. Includes charging cable and documentation.",
  "price": 25000000.00,
  "actual_category_id": 123,
  "predicted_category_id": 123,
  "confidence": 0.95,
  "is_validated": true,
  "source": "feedback",
  "created_at": "2024-01-10T14:30:00Z",
  "validated_at": "2024-01-11T09:00:00Z"
}
```

### Field Specifications

| Field | Type | Required | Max Length | Description |
|-------|------|----------|------------|-------------|
| `id` | integer | Auto | - | Unique sample identifier |
| `title` | string | Yes | 500 | Product title |
| `description` | string | No | 5000 | Product description |
| `price` | float | No | - | Price in VND (0 if unknown) |
| `actual_category_id` | integer | Yes | - | Correct category ID |
| `predicted_category_id` | integer | No | - | Model's prediction |
| `confidence` | float | No | - | Prediction confidence (0.0-1.0) |
| `is_validated` | boolean | Yes | - | Human validation status |
| `source` | string | Yes | 50 | Origin: feedback/manual/import |
| `created_at` | datetime | Auto | - | ISO 8601 format |
| `validated_at` | datetime | Auto | - | When validated (null if not) |

### Training Data Quality Requirements

1. **Title:** Must be descriptive, in Vietnamese, no spam/nonsense
2. **Description:** Should provide context, features, condition
3. **Category:** Must be a leaf category that is currently active
4. **Validation:** Only validated samples are used for training
5. **Balance:** Aim for at least 10 samples per category

---

## Classification Input Format

### Request Structure

```json
{
  "title": "iPhone 14 Pro Max 256GB",
  "description": "Brand new, sealed, with warranty",
  "price": 25000000
}
```

### Field Specifications

| Field | Type | Required | Max Length | Validation |
|-------|------|----------|------------|------------|
| `title` | string | Yes | 500 | Non-empty, no special chars only |
| `description` | string | No | 5000 | Can be empty or null |
| `price` | float | No | - | Must be >= 0 if provided |

### Response Structure

```json
{
  "category_id": 123,
  "category_name": "Điện thoại > Apple iPhone > iPhone 14 Series",
  "confidence": 0.95,
  "alternatives": [
    {
      "category_id": 124,
      "category_name": "Điện thoại > Smartphone cao cấp",
      "confidence": 0.87
    }
  ],
  "processing_time_ms": 234,
  "model_version": "v2024.01.15"
}
```

---

## Validation Rules

### Title Validation

```python
def validate_title(title: str) -> bool:
    if not title or len(title.strip()) == 0:
        return False, "Title cannot be empty"
    
    if len(title) > 500:
        return False, "Title too long (max 500 chars)"
    
    # Must contain at least some alphanumeric characters
    if not any(c.isalnum() for c in title):
        return False, "Title must contain alphanumeric characters"
    
    # Block spam patterns
    spam_patterns = ['***', '!!!', 'click here', 'buy now']
    if any(pattern in title.lower() for pattern in spam_patterns):
        return False, "Title contains spam patterns"
    
    return True, "OK"
```

### Description Validation

```python
def validate_description(description: str) -> bool:
    if description and len(description) > 5000:
        return False, "Description too long (max 5000 chars)"
    
    return True, "OK"
```

### Price Validation

```python
def validate_price(price: float) -> bool:
    if price < 0:
        return False, "Price cannot be negative"
    
    if price > 1000000000:  # 1 billion VND
        return False, "Price unreasonably high"
    
    return True, "OK"
```

### Category Validation

```python
def validate_category(category_id: int, categories: dict) -> bool:
    if category_id not in categories:
        return False, "Category does not exist"
    
    category = categories[category_id]
    
    if not category.is_active:
        return False, "Category is inactive"
    
    if not category.is_leaf:
        return False, "Must use leaf category (not parent)"
    
    return True, "OK"
```

---

## Data Quality Guidelines

### Training Data Quality Score

Each training sample is scored 0-100 based on:

| Criterion | Weight | Scoring |
|-----------|--------|---------|
| Title length | 20% | 10-50 chars = 100%, <10 or >100 = penalty |
| Description present | 15% | Has description = 100%, empty = 0% |
| Description length | 15% | 50-500 chars = 100% |
| Price present | 10% | Has price = 100%, missing = 50% |
| Is validated | 30% | Validated = 100%, not = 0% |
| No duplicates | 10% | Unique = 100%, duplicate = 0% |

```python
def calculate_quality_score(sample: dict) -> float:
    score = 0.0
    
    # Title length
    title_len = len(sample.get('title', ''))
    if 10 <= title_len <= 50:
        score += 20
    elif 50 < title_len <= 100:
        score += 15
    elif title_len > 100:
        score += 10
    
    # Description
    desc = sample.get('description', '')
    if desc:
        score += 15
        desc_len = len(desc)
        if 50 <= desc_len <= 500:
            score += 15
        elif desc_len > 500:
            score += 10
    
    # Price
    if sample.get('price') is not None:
        score += 10
    else:
        score += 5
    
    # Validation
    if sample.get('is_validated'):
        score += 30
    
    # Uniqueness (checked separately)
    if sample.get('is_unique', True):
        score += 10
    
    return score
```

### Minimum Quality Thresholds

- **For Training:** Quality score >= 60
- **For Production:** Quality score >= 70
- **For Validation:** Quality score >= 50

---

## Import/Export Formats

### Category Import Format

**File:** JSON array

```json
[
  {
    "id": 123,
    "name": "Điện thoại > Apple iPhone > iPhone 14 Series",
    "parent_id": 122,
    "level": 3,
    "is_leaf": true,
    "is_active": true,
    "description": "Các sản phẩm thuộc dòng iPhone 14"
  }
]
```

### Training Data Export Format

**File:** JSONL (JSON Lines)

```jsonl
{"id": 1, "title": "iPhone 14", "category_id": 123, "is_validated": true}
{"id": 2, "title": "Samsung S23", "category_id": 456, "is_validated": true}
```

### CSV Export Format

**Columns:**
```csv
id,title,description,price,category_id,category_name,confidence,is_validated,source,created_at
1,"iPhone 14","New phone",25000000,123,"Điện thoại > Apple",0.95,true,feedback,2024-01-15T10:00:00Z
```

---

## Best Practices

1. **Always validate input** before storing or processing
2. **Normalize text** (lowercase, remove extra spaces, normalize Vietnamese)
3. **Check for duplicates** before adding training samples
4. **Maintain category tree integrity** when updating
5. **Version control** category changes
6. **Backup regularly** before bulk operations
7. **Log all changes** for audit trail

---

## Appendix: Vietnamese Text Normalization

```python
import unicodedata

def normalize_vietnamese(text: str) -> str:
    # Normalize Unicode (NFD -> NFC)
    text = unicodedata.normalize('NFC', text)
    
    # Lowercase
    text = text.lower()
    
    # Remove extra spaces
    text = ' '.join(text.split())
    
    # Remove special characters (keep Vietnamese)
    allowed = set('abcdefghijklmnopqrstuvwxyz0123456789 àáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ')
    text = ''.join(c for c in text if c in allowed)
    
    return text
```
