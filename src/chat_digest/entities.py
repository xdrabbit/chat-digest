"""Entity and topic extraction from conversations."""

from __future__ import annotations

import re
from collections import Counter
from typing import List, Set

from .schemas import Message


class Entity:
    """Represents an extracted entity (API, dependency, config, etc.)."""
    
    def __init__(
        self,
        name: str,
        entity_type: str,  # api, dependency, config, file, person, etc.
        mentions: List[int],  # Message orders where mentioned
        context: str = "",
    ):
        self.name = name
        self.entity_type = entity_type
        self.mentions = mentions
        self.context = context
        self.mention_count = len(mentions)
    
    def __repr__(self) -> str:
        return f"<Entity {self.entity_type}:'{self.name}' ({self.mention_count} mentions)>"
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.entity_type,
            "mentions": self.mentions,
            "mention_count": self.mention_count,
            "context": self.context,
        }


def extract_dependencies(messages: List[Message]) -> List[Entity]:
    """
    Extract software dependencies mentioned in the conversation.
    
    Detects: npm packages, Python packages, libraries, frameworks.
    """
    dependencies = {}
    
    # Patterns for common dependency mentions
    patterns = [
        (r'\b(react|vue|angular|svelte|next\.js|nuxt|gatsby)\b', 'framework'),
        (r'\b(express|fastapi|flask|django|rails|spring)\b', 'backend_framework'),
        (r'\b(postgresql|mysql|mongodb|redis|sqlite)\b', 'database'),
        (r'\b(axios|fetch|requests|urllib)\b', 'http_client'),
        (r'npm install\s+([a-z0-9\-\s]+)', 'npm_package'),  # Captures all packages
        (r'pip install\s+([a-z0-9\-_\s]+)', 'python_package'),  # Captures all packages
        (r'import\s+([a-z0-9_]+)', 'python_import'),
        (r'from\s+([a-z0-9_]+)\s+import', 'python_import'),
    ]
    
    for msg in messages:
        content_lower = msg.content.lower()
        
        for pattern, dep_type in patterns:
            matches = re.finditer(pattern, content_lower, re.IGNORECASE)
            for match in matches:
                dep_names_str = match.group(1) if match.lastindex else match.group(0)
                
                # For npm/pip install, split by spaces to get individual packages
                if dep_type in ['npm_package', 'python_package']:
                    dep_names = dep_names_str.split()
                else:
                    dep_names = [dep_names_str]
                
                for dep_name in dep_names:
                    dep_name = dep_name.strip()
                    if not dep_name:
                        continue
                    
                    if dep_name not in dependencies:
                        dependencies[dep_name] = Entity(
                            name=dep_name,
                            entity_type=dep_type,
                            mentions=[msg.order],
                        )
                    else:
                        dependencies[dep_name].mentions.append(msg.order)
                        dependencies[dep_name].mention_count += 1
    
    return list(dependencies.values())


def extract_apis(messages: List[Message]) -> List[Entity]:
    """
    Extract API endpoints and services mentioned.
    
    Detects: REST endpoints, GraphQL, external services.
    """
    apis = {}
    
    # Patterns for API mentions
    patterns = [
        r'(GET|POST|PUT|DELETE|PATCH)\s+(/[a-z0-9/\-_{}:]+)',  # REST endpoints
        r'https?://[a-z0-9\-\.]+\.[a-z]{2,}(/[a-z0-9/\-_]*)?',  # URLs
        r'api\.[a-z0-9\-]+\.[a-z]{2,}',  # API domains
        r'/api/v?\d+/[a-z0-9/\-_]+',  # Versioned API paths
    ]
    
    for msg in messages:
        for pattern in patterns:
            matches = re.finditer(pattern, msg.content, re.IGNORECASE)
            for match in matches:
                api_name = match.group(0)
                
                if api_name not in apis:
                    apis[api_name] = Entity(
                        name=api_name,
                        entity_type='api_endpoint',
                        mentions=[msg.order],
                    )
                else:
                    apis[api_name].mentions.append(msg.order)
                    apis[api_name].mention_count += 1
    
    return list(apis.values())


def extract_config_values(messages: List[Message]) -> List[Entity]:
    """
    Extract configuration values and settings.
    
    Detects: env vars, ports, URLs, keys.
    """
    configs = {}
    
    # Patterns for config mentions
    patterns = [
        (r'PORT\s*=\s*(\d+)', 'port'),
        (r'port:\s*(\d+)', 'port'),
        (r'([A-Z_]+)=([^\s]+)', 'env_var'),
        (r'API_KEY|SECRET_KEY|DATABASE_URL', 'secret'),
    ]
    
    for msg in messages:
        for pattern, config_type in patterns:
            matches = re.finditer(pattern, msg.content)
            for match in matches:
                config_name = match.group(0)
                
                if config_name not in configs:
                    configs[config_name] = Entity(
                        name=config_name,
                        entity_type=config_type,
                        mentions=[msg.order],
                    )
                else:
                    configs[config_name].mentions.append(msg.order)
                    configs[config_name].mention_count += 1
    
    return list(configs.values())


def extract_people(messages: List[Message]) -> List[Entity]:
    """
    Extract people mentioned in the conversation.
    
    Detects: @mentions, names in context.
    """
    people = {}
    
    # Pattern for @mentions
    mention_pattern = r'@([a-zA-Z0-9_\-]+)'
    
    for msg in messages:
        matches = re.finditer(mention_pattern, msg.content)
        for match in matches:
            person_name = match.group(1)
            
            if person_name not in people:
                people[person_name] = Entity(
                    name=person_name,
                    entity_type='person',
                    mentions=[msg.order],
                )
            else:
                people[person_name].mentions.append(msg.order)
                people[person_name].mention_count += 1
    
    return list(people.values())


def extract_topics(messages: List[Message], min_mentions: int = 2) -> List[str]:
    """
    Extract main topics from conversation using keyword frequency.
    
    Returns list of topics sorted by relevance.
    """
    # Common stop words to ignore
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
        'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this',
        'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
        'what', 'which', 'who', 'when', 'where', 'why', 'how', 'all', 'each',
        'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no',
        'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just',
    }
    
    # Extract words
    word_counts = Counter()
    
    for msg in messages:
        # Tokenize and clean
        words = re.findall(r'\b[a-z]{3,}\b', msg.content.lower())
        for word in words:
            if word not in stop_words:
                word_counts[word] += 1
    
    # Filter by minimum mentions and return top topics
    topics = [word for word, count in word_counts.items() if count >= min_mentions]
    topics.sort(key=lambda w: word_counts[w], reverse=True)
    
    return topics[:20]  # Top 20 topics


def extract_all_entities(messages: List[Message]) -> dict:
    """
    Extract all entity types at once.
    
    Returns dict with all entity categories.
    """
    return {
        "dependencies": extract_dependencies(messages),
        "apis": extract_apis(messages),
        "configs": extract_config_values(messages),
        "people": extract_people(messages),
        "topics": extract_topics(messages),
    }


def get_entity_summary(entities: dict) -> dict:
    """
    Generate summary statistics for extracted entities.
    """
    return {
        "total_dependencies": len(entities.get("dependencies", [])),
        "total_apis": len(entities.get("apis", [])),
        "total_configs": len(entities.get("configs", [])),
        "total_people": len(entities.get("people", [])),
        "total_topics": len(entities.get("topics", [])),
        "most_mentioned_dependency": _get_most_mentioned(entities.get("dependencies", [])),
        "most_mentioned_api": _get_most_mentioned(entities.get("apis", [])),
    }


def _get_most_mentioned(entities: List[Entity]) -> str | None:
    """Get the most frequently mentioned entity."""
    if not entities:
        return None
    return max(entities, key=lambda e: e.mention_count).name
