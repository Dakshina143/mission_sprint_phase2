-- Run as a PostgreSQL superuser, e.g.:  psql -U postgres -f database/create_database.sql
-- Replace CHANGE_ME with a strong password, and use the same value in your .env DATABASE_URL.
CREATE ROLE missionsprint LOGIN PASSWORD 'CHANGE_ME';
CREATE DATABASE missionsprint OWNER missionsprint;
