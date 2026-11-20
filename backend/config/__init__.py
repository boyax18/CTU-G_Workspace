# Allow MySQL 8.0+ for local development
from django.db.backends.mysql.features import DatabaseFeatures

DatabaseFeatures.minimum_database_version = (8, 0, 0)
