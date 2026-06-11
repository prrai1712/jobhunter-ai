"""Skills database — curated taxonomy of tech skills with aliases and categories."""

from __future__ import annotations

# Comprehensive skill taxonomy mapping canonical names to aliases
SKILL_ALIASES: dict[str, list[str]] = {
    # Languages
    "python": ["python3", "py", "python 3", "cpython"],
    "javascript": ["js", "ecmascript", "es6", "es2015+", "vanilla js"],
    "typescript": ["ts"],
    "java": ["jdk", "jvm"],
    "golang": ["go", "go lang", "go-lang"],
    "rust": ["rust lang", "rustlang"],
    "c++": ["cpp", "c plus plus"],
    "c#": ["csharp", "c sharp", ".net c#"],
    "ruby": ["rb"],
    "php": ["php7", "php8"],
    "scala": ["scala lang"],
    "kotlin": ["kt"],
    "swift": ["swift lang"],
    "r": ["r lang", "r programming"],
    "sql": ["structured query language"],
    "html": ["html5"],
    "css": ["css3"],
    "bash": ["shell", "shell scripting", "sh", "zsh"],

    # Frameworks & Libraries
    "django": ["django framework", "django web"],
    "django rest framework": ["drf", "django-rest-framework", "django rest"],
    "flask": ["flask framework"],
    "fastapi": ["fast api", "fast-api"],
    "react": ["reactjs", "react.js", "react js"],
    "angular": ["angularjs", "angular.js"],
    "vue": ["vuejs", "vue.js", "vue js"],
    "nextjs": ["next.js", "next js"],
    "express": ["expressjs", "express.js"],
    "spring": ["spring boot", "spring framework", "springboot"],
    "rails": ["ruby on rails", "ror"],
    "laravel": ["laravel framework"],
    "nodejs": ["node.js", "node js", "node"],
    "celery": ["celery task", "celery worker"],
    "asyncio": ["async io", "python asyncio"],

    # Databases
    "postgresql": ["postgres", "psql", "pgsql"],
    "mysql": ["mariadb", "maria db"],
    "mongodb": ["mongo", "mongo db"],
    "redis": ["redis cache", "redis server"],
    "elasticsearch": ["elastic search", "elastic", "es"],
    "cassandra": ["apache cassandra"],
    "dynamodb": ["dynamo db", "aws dynamodb"],
    "sqlite": ["sqlite3"],
    "oracle db": ["oracle database", "oracle"],
    "sql server": ["mssql", "ms sql", "microsoft sql"],

    # Cloud & DevOps
    "aws": ["amazon web services", "amazon aws"],
    "gcp": ["google cloud", "google cloud platform"],
    "azure": ["microsoft azure", "azure cloud"],
    "docker": ["docker container", "containerization"],
    "kubernetes": ["k8s", "kube"],
    "terraform": ["terraform iac"],
    "ansible": ["ansible automation"],
    "jenkins": ["jenkins ci"],
    "github actions": ["gh actions", "github ci"],
    "gitlab ci": ["gitlab ci/cd"],
    "circleci": ["circle ci"],
    "nginx": ["nginx server"],
    "apache": ["apache server", "httpd"],
    "linux": ["unix", "gnu/linux"],

    # Data & ML
    "pandas": ["pandas library"],
    "numpy": ["np"],
    "scikit-learn": ["sklearn", "scikit learn"],
    "tensorflow": ["tf"],
    "pytorch": ["torch"],
    "spark": ["apache spark", "pyspark"],
    "airflow": ["apache airflow"],
    "kafka": ["apache kafka"],
    "rabbitmq": ["rabbit mq"],

    # Tools
    "git": ["git version control", "github", "gitlab", "bitbucket"],
    "jira": ["atlassian jira"],
    "confluence": ["atlassian confluence"],
    "postman": ["postman api"],
    "swagger": ["openapi", "swagger ui"],
    "graphql": ["graph ql"],
    "grpc": ["g-rpc"],
    "websocket": ["websockets", "ws"],

    # Concepts
    "rest apis": ["rest api", "restful", "restful api", "rest", "api development"],
    "microservices": ["micro services", "microservice architecture"],
    "distributed systems": ["distributed computing", "distributed architecture"],
    "web scraping": ["web crawling", "scraping", "data scraping"],
    "backend engineering": ["backend development", "backend", "server side"],
    "ci/cd": ["cicd", "ci cd", "continuous integration", "continuous deployment"],
    "agile": ["agile methodology", "scrum", "kanban"],
    "tdd": ["test driven development", "test-driven development"],
    "oop": ["object oriented programming", "object-oriented"],
    "solid": ["solid principles"],
    "design patterns": ["design pattern", "software patterns"],
    "system design": ["system architecture", "architecture design"],
    "data structures": ["data structures and algorithms", "dsa"],
    "algorithms": ["algorithm design"],
    "caching": ["cache", "caching strategies"],
    "message queues": ["message queue", "mq", "pub sub", "pub/sub"],
    "load balancing": ["load balancer"],
    "monitoring": ["observability", "apm"],
    "logging": ["structured logging", "log management"],
    "security": ["cybersecurity", "appsec", "application security"],
    "authentication": ["auth", "oauth", "jwt", "sso"],
    "authorization": ["rbac", "abac", "permissions"],
}

# Build reverse index: alias -> canonical name
ALIAS_TO_CANONICAL: dict[str, str] = {}
for canonical, aliases in SKILL_ALIASES.items():
    ALIAS_TO_CANONICAL[canonical.lower()] = canonical.lower()
    for alias in aliases:
        ALIAS_TO_CANONICAL[alias.lower()] = canonical.lower()

# Skill categories for reporting
SKILL_CATEGORIES: dict[str, list[str]] = {
    "languages": [
        "python", "javascript", "typescript", "java", "golang", "rust",
        "c++", "c#", "ruby", "php", "scala", "kotlin", "swift", "r",
        "sql", "html", "css", "bash",
    ],
    "frameworks": [
        "django", "django rest framework", "flask", "fastapi", "react",
        "angular", "vue", "nextjs", "express", "spring", "rails",
        "laravel", "nodejs", "celery", "asyncio",
    ],
    "databases": [
        "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
        "cassandra", "dynamodb", "sqlite", "oracle db", "sql server",
    ],
    "cloud_devops": [
        "aws", "gcp", "azure", "docker", "kubernetes", "terraform",
        "ansible", "jenkins", "github actions", "gitlab ci", "circleci",
        "nginx", "apache", "linux",
    ],
    "data_ml": [
        "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch",
        "spark", "airflow", "kafka", "rabbitmq",
    ],
    "tools": [
        "git", "jira", "confluence", "postman", "swagger", "graphql",
        "grpc", "websocket",
    ],
    "concepts": [
        "rest apis", "microservices", "distributed systems", "web scraping",
        "backend engineering", "ci/cd", "agile", "tdd", "oop", "solid",
        "design patterns", "system design", "data structures", "algorithms",
        "caching", "message queues", "load balancing", "monitoring",
        "logging", "security", "authentication", "authorization",
    ],
}


def normalize_skill(skill: str) -> str:
    """Normalize a skill name to its canonical form."""
    return ALIAS_TO_CANONICAL.get(skill.lower().strip(), skill.lower().strip())


def get_all_skills() -> set[str]:
    """Get the set of all known canonical skill names."""
    return set(SKILL_ALIASES.keys())
