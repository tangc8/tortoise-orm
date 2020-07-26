from asynctest.mock import CoroutineMock, patch

from tests.schema.test_generate_schema import TestGenerateSchema
from tortoise import Tortoise
from tortoise.contrib import test
from tortoise.utils import get_schema_sql


class TestGenerateSchemaPostgresSQL(TestGenerateSchema):
    async def init_for(self, module: str, safe=False) -> None:
        try:
            with patch("asyncpg.create_pool", new=CoroutineMock()):
                await Tortoise.init(
                    {
                        "connections": {
                            "default": {
                                "engine": "tortoise.backends.asyncpg",
                                "credentials": {
                                    "database": "test",
                                    "host": "127.0.0.1",
                                    "password": "foomip",
                                    "port": 3306,
                                    "user": "root",
                                },
                            }
                        },
                        "apps": {"models": {"models": [module], "default_connection": "default"}},
                    }
                )
                self.sqls = get_schema_sql(Tortoise._connections["default"], safe).split("; ")
        except ImportError:
            raise test.SkipTest("asyncpg not installed")

    async def test_noid(self):
        await self.init_for("tests.testmodels")
        sql = self.get_sql('"noid"')
        self.assertIn('"name" VARCHAR(255)', sql)
        self.assertIn('"id" SERIAL NOT NULL PRIMARY KEY', sql)

    async def test_table_and_row_comment_generation(self):
        await self.init_for("tests.testmodels")
        sql = self.get_sql("comments")
        self.assertIn("COMMENT ON TABLE \"comments\" IS 'Test Table comment'", sql)
        self.assertIn(
            'COMMENT ON COLUMN "comments"."escaped_comment_field" IS '
            "'This column acts as it''s own comment'",
            sql,
        )
        self.assertIn(
            'COMMENT ON COLUMN "comments"."multiline_comment" IS \'Some \\n comment\'', sql
        )

    async def test_schema(self):
        self.maxDiff = None
        await self.init_for("tests.schema.models_schema_create")
        sql = get_schema_sql(Tortoise.get_connection("default"), safe=False)
        self.assertEqual(
            sql.strip(),
            """
CREATE TABLE "company" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "uuid" UUID NOT NULL UNIQUE
);
CREATE TABLE "defaultpk" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "val" INT NOT NULL
);
CREATE TABLE "employee" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "company_id" UUID NOT NULL REFERENCES "company" ("uuid") ON DELETE CASCADE
);
CREATE TABLE "inheritedmodel" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "zero" INT NOT NULL,
    "one" VARCHAR(40),
    "new_field" VARCHAR(100) NOT NULL,
    "two" VARCHAR(40) NOT NULL,
    "name" TEXT NOT NULL
);
CREATE TABLE "sometable" (
    "sometable_id" SERIAL NOT NULL PRIMARY KEY,
    "some_chars_table" VARCHAR(255) NOT NULL,
    "fk_sometable" INT REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE
);
CREATE INDEX "idx_sometable_some_ch_3d69eb" ON "sometable" ("some_chars_table");
CREATE TABLE "team" (
    "name" VARCHAR(50) NOT NULL  PRIMARY KEY,
    "key" INT NOT NULL,
    "manager_id" VARCHAR(50) REFERENCES "team" ("name") ON DELETE CASCADE
);
CREATE INDEX "idx_team_manager_676134" ON "team" ("manager_id", "key");
CREATE INDEX "idx_team_manager_ef8f69" ON "team" ("manager_id", "name");
COMMENT ON COLUMN "team"."name" IS 'The TEAM name (and PK)';
COMMENT ON TABLE "team" IS 'The TEAMS!';
CREATE TABLE "teamaddress" (
    "city" VARCHAR(50) NOT NULL,
    "country" VARCHAR(50) NOT NULL,
    "street" VARCHAR(128) NOT NULL,
    "team_id" VARCHAR(50) NOT NULL  PRIMARY KEY REFERENCES "team" ("name") ON DELETE CASCADE
);
COMMENT ON COLUMN "teamaddress"."city" IS 'City';
COMMENT ON COLUMN "teamaddress"."country" IS 'Country';
COMMENT ON COLUMN "teamaddress"."street" IS 'Street Address';
COMMENT ON TABLE "teamaddress" IS 'The Team''s address';
CREATE TABLE "tournament" (
    "tid" SMALLSERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(100) NOT NULL,
    "created" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX "idx_tournament_name_6fe200" ON "tournament" ("name");
COMMENT ON COLUMN "tournament"."name" IS 'Tournament name';
COMMENT ON COLUMN "tournament"."created" IS 'Created */''`/* datetime';
COMMENT ON TABLE "tournament" IS 'What Tournaments */''`/* we have';
CREATE TABLE "event" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "modified" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "prize" DECIMAL(10,2),
    "token" VARCHAR(100) NOT NULL UNIQUE,
    "key" VARCHAR(100) NOT NULL,
    "tournament_id" SMALLINT NOT NULL REFERENCES "tournament" ("tid") ON DELETE CASCADE,
    CONSTRAINT "uid_event_name_c6f89f" UNIQUE ("name", "prize"),
    CONSTRAINT "uid_event_tournam_a5b730" UNIQUE ("tournament_id", "key")
);
COMMENT ON COLUMN "event"."id" IS 'Event ID';
COMMENT ON COLUMN "event"."token" IS 'Unique token';
COMMENT ON COLUMN "event"."tournament_id" IS 'FK to tournament';
COMMENT ON TABLE "event" IS 'This table contains a list of all the events';
CREATE TABLE "venueinformation" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(128) NOT NULL,
    "capacity" INT NOT NULL,
    "rent" DOUBLE PRECISION NOT NULL,
    "team_id" VARCHAR(50)  UNIQUE REFERENCES "team" ("name") ON DELETE SET NULL
);
COMMENT ON COLUMN "venueinformation"."capacity" IS 'No. of seats';
CREATE TABLE "sometable_self" (
    "backward_sts" INT NOT NULL REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE,
    "sts_forward" INT NOT NULL REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE
);
CREATE TABLE "team_team" (
    "team_rel_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE,
    "team_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE
);
CREATE TABLE "teamevents" (
    "event_id" BIGINT NOT NULL REFERENCES "event" ("id") ON DELETE CASCADE,
    "team_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE
);
COMMENT ON TABLE "teamevents" IS 'How participants relate';
""".strip(),
        )

    async def test_schema_safe(self):
        self.maxDiff = None
        await self.init_for("tests.schema.models_schema_create")
        sql = get_schema_sql(Tortoise.get_connection("default"), safe=True)
        self.assertEqual(
            sql.strip(),
            """
CREATE TABLE IF NOT EXISTS "company" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "uuid" UUID NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS "defaultpk" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "val" INT NOT NULL
);
CREATE TABLE IF NOT EXISTS "employee" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "company_id" UUID NOT NULL REFERENCES "company" ("uuid") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "inheritedmodel" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "zero" INT NOT NULL,
    "one" VARCHAR(40),
    "new_field" VARCHAR(100) NOT NULL,
    "two" VARCHAR(40) NOT NULL,
    "name" TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS "sometable" (
    "sometable_id" SERIAL NOT NULL PRIMARY KEY,
    "some_chars_table" VARCHAR(255) NOT NULL,
    "fk_sometable" INT REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_sometable_some_ch_3d69eb" ON "sometable" ("some_chars_table");
CREATE TABLE IF NOT EXISTS "team" (
    "name" VARCHAR(50) NOT NULL  PRIMARY KEY,
    "key" INT NOT NULL,
    "manager_id" VARCHAR(50) REFERENCES "team" ("name") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_team_manager_676134" ON "team" ("manager_id", "key");
CREATE INDEX IF NOT EXISTS "idx_team_manager_ef8f69" ON "team" ("manager_id", "name");
COMMENT ON COLUMN "team"."name" IS 'The TEAM name (and PK)';
COMMENT ON TABLE "team" IS 'The TEAMS!';
CREATE TABLE IF NOT EXISTS "teamaddress" (
    "city" VARCHAR(50) NOT NULL,
    "country" VARCHAR(50) NOT NULL,
    "street" VARCHAR(128) NOT NULL,
    "team_id" VARCHAR(50) NOT NULL  PRIMARY KEY REFERENCES "team" ("name") ON DELETE CASCADE
);
COMMENT ON COLUMN "teamaddress"."city" IS 'City';
COMMENT ON COLUMN "teamaddress"."country" IS 'Country';
COMMENT ON COLUMN "teamaddress"."street" IS 'Street Address';
COMMENT ON TABLE "teamaddress" IS 'The Team''s address';
CREATE TABLE IF NOT EXISTS "tournament" (
    "tid" SMALLSERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(100) NOT NULL,
    "created" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_tournament_name_6fe200" ON "tournament" ("name");
COMMENT ON COLUMN "tournament"."name" IS 'Tournament name';
COMMENT ON COLUMN "tournament"."created" IS 'Created */''`/* datetime';
COMMENT ON TABLE "tournament" IS 'What Tournaments */''`/* we have';
CREATE TABLE IF NOT EXISTS "event" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "modified" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "prize" DECIMAL(10,2),
    "token" VARCHAR(100) NOT NULL UNIQUE,
    "key" VARCHAR(100) NOT NULL,
    "tournament_id" SMALLINT NOT NULL REFERENCES "tournament" ("tid") ON DELETE CASCADE,
    CONSTRAINT "uid_event_name_c6f89f" UNIQUE ("name", "prize"),
    CONSTRAINT "uid_event_tournam_a5b730" UNIQUE ("tournament_id", "key")
);
COMMENT ON COLUMN "event"."id" IS 'Event ID';
COMMENT ON COLUMN "event"."token" IS 'Unique token';
COMMENT ON COLUMN "event"."tournament_id" IS 'FK to tournament';
COMMENT ON TABLE "event" IS 'This table contains a list of all the events';
CREATE TABLE IF NOT EXISTS "venueinformation" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(128) NOT NULL,
    "capacity" INT NOT NULL,
    "rent" DOUBLE PRECISION NOT NULL,
    "team_id" VARCHAR(50)  UNIQUE REFERENCES "team" ("name") ON DELETE SET NULL
);
COMMENT ON COLUMN "venueinformation"."capacity" IS 'No. of seats';
CREATE TABLE IF NOT EXISTS "sometable_self" (
    "backward_sts" INT NOT NULL REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE,
    "sts_forward" INT NOT NULL REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "team_team" (
    "team_rel_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE,
    "team_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "teamevents" (
    "event_id" BIGINT NOT NULL REFERENCES "event" ("id") ON DELETE CASCADE,
    "team_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE
);
COMMENT ON TABLE "teamevents" IS 'How participants relate';
""".strip(),
        )