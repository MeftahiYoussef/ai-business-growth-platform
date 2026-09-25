# SFT v2 Structural Diversity Analysis

This report goes beyond exact and near-duplicate text matching. It clusters assistant answer skeletons to detect repeated semantic templates.

## Distributions By Record Count

```json
{
  "difficulty": {
    "easy": 72,
    "hard": 108,
    "medium": 180
  },
  "language": {
    "en": 144,
    "fr": 108,
    "ru": 108
  },
  "task": {
    "business_report": 36,
    "competitor_analysis": 16,
    "safety": 144,
    "strategy": 72,
    "trend_intelligence": 92
  }
}
```

## Distributions By Assistant Word Tokens

```json
{
  "difficulty": {
    "easy": 3728,
    "hard": 5543,
    "medium": 9181
  },
  "language": {
    "en": 6600,
    "fr": 6982,
    "ru": 4870
  },
  "task": {
    "business_report": 2206,
    "competitor_analysis": 781,
    "safety": 7032,
    "strategy": 2620,
    "trend_intelligence": 5813
  }
}
```

## Length And Metadata

```json
{
  "assistant_length_words": {
    "average": 51.26,
    "count": 360,
    "max": 76,
    "median": 49.0
  },
  "critical_fact_count": {
    "average": 4.56,
    "count": 360,
    "max": 7,
    "median": 3.0
  },
  "numeric_fact_count": {
    "average": 8.0,
    "count": 360,
    "max": 8,
    "median": 8.0
  },
  "unavailable_metric_count": {
    "average": 2.0,
    "count": 360,
    "max": 2,
    "median": 2.0
  }
}
```

## Uncertainty Phrases

- Record rate with uncertainty phrase: `1.0`
- Record rate with refusal phrase: `0.6`

```json
{
  "non disponible": 108,
  "unavailable": 232,
  "недоступ": 144
}
```

## Template Clusters

- Template cluster count: `360`
- Max template cluster share: `0.0028`
- Label-pattern cluster count: `3`
- Max label-pattern share: `0.4`
- Family count: `90`
- Max family share: `0.0111`
- Shared train/validation skeleton count: `0`
- Shared train/validation label-pattern count: `3`

```json
[
  {
    "cluster": "observed facts|limitations|recommendations::2112dbb6c2",
    "count": 1
  },
  {
    "cluster": "observed facts|limitations|recommendations::c25ef298e6",
    "count": 1
  },
  {
    "cluster": "observed facts|limitations|recommendations::8aab4ba9ec",
    "count": 1
  },
  {
    "cluster": "observed facts|limitations|recommendations::70c21fbac1",
    "count": 1
  },
  {
    "cluster": "observed facts|limitations|recommendations::a5a7be7bf8",
    "count": 1
  },
  {
    "cluster": "observed facts|limitations|recommendations::88df27771f",
    "count": 1
  },
  {
    "cluster": "observed facts|limitations|recommendations::ef707a6537",
    "count": 1
  },
  {
    "cluster": "observed facts|limitations|recommendations::d3ac9858af",
    "count": 1
  },
  {
    "cluster": "observed facts|limitations|recommendations::f94caee9a8",
    "count": 1
  },
  {
    "cluster": "observed facts|limitations|recommendations::2c4cb73552",
    "count": 1
  }
]
```

## Label Pattern Clusters

```json
[
  {
    "cluster": "observed facts|limitations|recommendations",
    "count": 144
  },
  {
    "cluster": "faits observés|limites|recommandations",
    "count": 108
  },
  {
    "cluster": "наблюдаемые факты|ограничения|рекомендации",
    "count": 108
  }
]
```

## Target Quality Flags

```json
{
  "refusal_phrase_present": 216,
  "repeated_en_caution_template": 88
}
```

## Finding

The dataset is lexically unique but semantically repetitive. The repeated fact/limitation/recommendation skeleton and global uncertainty target likely taught caution as a default style instead of selective qualification.
