"""Tests for entity and topic extraction."""

from chat_digest.entities import (
    Entity,
    extract_dependencies,
    extract_apis,
    extract_config_values,
    extract_people,
    extract_topics,
    extract_all_entities,
    get_entity_summary,
)
from chat_digest.schemas import Message


def test_entity_creation():
    """Test Entity creation."""
    entity = Entity(
        name="FastAPI",
        entity_type="framework",
        mentions=[1, 3, 5],
        context="Web framework",
    )
    
    assert entity.name == "FastAPI"
    assert entity.entity_type == "framework"
    assert entity.mention_count == 3
    assert len(entity.mentions) == 3


def test_entity_to_dict():
    """Test Entity serialization."""
    entity = Entity("React", "framework", [1, 2])
    
    data = entity.to_dict()
    
    assert data["name"] == "React"
    assert data["type"] == "framework"
    assert data["mention_count"] == 2


def test_extract_dependencies_frameworks():
    """Test extraction of framework dependencies."""
    messages = [
        Message(order=1, role="user", content="Should we use React or Vue?", tags=[]),
        Message(order=2, role="assistant", content="Let's go with React", tags=[]),
    ]
    
    deps = extract_dependencies(messages)
    
    assert len(deps) >= 2
    names = [d.name for d in deps]
    assert "react" in names
    assert "vue" in names


def test_extract_dependencies_databases():
    """Test extraction of database dependencies."""
    messages = [
        Message(order=1, role="user", content="Use PostgreSQL for the database", tags=[]),
    ]
    
    deps = extract_dependencies(messages)
    
    assert len(deps) >= 1
    assert any(d.name == "postgresql" for d in deps)


def test_extract_dependencies_npm():
    """Test extraction of npm packages."""
    messages = [
        Message(order=1, role="assistant", content="Run: npm install express axios", tags=[]),
    ]
    
    deps = extract_dependencies(messages)
    
    names = [d.name for d in deps]
    assert "express" in names
    assert "axios" in names


def test_extract_dependencies_python():
    """Test extraction of Python packages."""
    messages = [
        Message(order=1, role="assistant", content="pip install fastapi uvicorn", tags=[]),
    ]
    
    deps = extract_dependencies(messages)
    
    names = [d.name for d in deps]
    assert "fastapi" in names
    assert "uvicorn" in names


def test_extract_apis_rest_endpoints():
    """Test extraction of REST API endpoints."""
    messages = [
        Message(order=1, role="user", content="Create GET /api/users endpoint", tags=[]),
        Message(order=2, role="assistant", content="Also add POST /api/users", tags=[]),
    ]
    
    apis = extract_apis(messages)
    
    assert len(apis) >= 2
    endpoints = [a.name for a in apis]
    assert any("/api/users" in e for e in endpoints)


def test_extract_apis_urls():
    """Test extraction of URLs."""
    messages = [
        Message(order=1, role="user", content="Call https://api.example.com/data", tags=[]),
    ]
    
    apis = extract_apis(messages)
    
    assert len(apis) >= 1
    assert any("api.example.com" in a.name for a in apis)


def test_extract_config_values_ports():
    """Test extraction of port configurations."""
    messages = [
        Message(order=1, role="assistant", content="Set PORT=3000 in your env", tags=[]),
        Message(order=2, role="user", content="The server runs on port: 8080", tags=[]),
    ]
    
    configs = extract_config_values(messages)
    
    assert len(configs) >= 1


def test_extract_config_values_env_vars():
    """Test extraction of environment variables."""
    messages = [
        Message(order=1, role="assistant", content="Set DATABASE_URL=postgres://...", tags=[]),
    ]
    
    configs = extract_config_values(messages)
    
    assert len(configs) >= 1


def test_extract_people():
    """Test extraction of @mentions."""
    messages = [
        Message(order=1, role="user", content="Hey @john, can you review this?", tags=[]),
        Message(order=2, role="assistant", content="CC @sarah as well", tags=[]),
    ]
    
    people = extract_people(messages)
    
    assert len(people) == 2
    names = [p.name for p in people]
    assert "john" in names
    assert "sarah" in names


def test_extract_topics():
    """Test topic extraction from conversation."""
    messages = [
        Message(order=1, role="user", content="Let's build an API with authentication", tags=[]),
        Message(order=2, role="assistant", content="The API will need authentication and authorization", tags=[]),
        Message(order=3, role="user", content="How do we handle authentication?", tags=[]),
    ]
    
    topics = extract_topics(messages, min_mentions=2)
    
    assert "api" in topics or "authentication" in topics


def test_extract_topics_filters_stop_words():
    """Test that topics filter out common stop words."""
    messages = [
        Message(order=1, role="user", content="The the the the the", tags=[]),
    ]
    
    topics = extract_topics(messages, min_mentions=2)
    
    assert "the" not in topics


def test_extract_all_entities():
    """Test extracting all entity types at once."""
    messages = [
        Message(order=1, role="user", content="Use React and FastAPI", tags=[]),
        Message(order=2, role="assistant", content="Call GET /api/users", tags=[]),
        Message(order=3, role="user", content="Set PORT=3000", tags=[]),
        Message(order=4, role="assistant", content="Ask @john about this", tags=[]),
    ]
    
    entities = extract_all_entities(messages)
    
    assert "dependencies" in entities
    assert "apis" in entities
    assert "configs" in entities
    assert "people" in entities
    assert "topics" in entities


def test_get_entity_summary():
    """Test entity summary generation."""
    entities = {
        "dependencies": [
            Entity("react", "framework", [1, 2, 3]),
            Entity("fastapi", "framework", [1]),
        ],
        "apis": [Entity("/api/users", "endpoint", [1])],
        "configs": [],
        "people": [Entity("john", "person", [1])],
        "topics": ["api", "authentication"],
    }
    
    summary = get_entity_summary(entities)
    
    assert summary["total_dependencies"] == 2
    assert summary["total_apis"] == 1
    assert summary["total_people"] == 1
    assert summary["total_topics"] == 2
    assert summary["most_mentioned_dependency"] == "react"


def test_entity_mention_tracking():
    """Test that entities track all mentions."""
    messages = [
        Message(order=1, role="user", content="Use React", tags=[]),
        Message(order=3, role="assistant", content="React is great", tags=[]),
        Message(order=5, role="user", content="Install React", tags=[]),
    ]
    
    deps = extract_dependencies(messages)
    
    react = next((d for d in deps if d.name == "react"), None)
    assert react is not None
    assert react.mention_count == 3
    assert react.mentions == [1, 3, 5]


def test_extract_dependencies_case_insensitive():
    """Test that dependency extraction is case-insensitive."""
    messages = [
        Message(order=1, role="user", content="Use REACT and React and react", tags=[]),
    ]
    
    deps = extract_dependencies(messages)
    
    react_deps = [d for d in deps if d.name == "react"]
    assert len(react_deps) == 1
    assert react_deps[0].mention_count == 3
