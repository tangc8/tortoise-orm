import re

from asynctest.mock import CoroutineMock, patch

from tortoise import Tortoise
from tortoise.contrib import test
from tortoise.exceptions import ConfigurationError
from tortoise.utils import get_schema_sql


class TestGenerateSchema(test.SimpleTestCase):
    async def setUp(self):
        try:
            Tortoise.apps = {}
            Tortoise._connections = {}
            Tortoise._inited = False
        except ConfigurationError:
            pass
        Tortoise._inited = False
        self.sqls = ""
        self.post_sqls = ""
        self.engine = test.getDBConfig(app_label="models", modules=[])["connections"]["models"][
            "engine"
        ]

    async def tearDown(self):
        Tortoise._connections = {}
        await Tortoise._reset_apps()

    async def init_for(self, module: str, safe=False) -> None:
        with patch(
            "tortoise.backends.sqlite.client.SqliteClient.create_connection", new=CoroutineMock()
        ):
            await Tortoise.init(
                {
                    "connections": {
                        "default": {
                            "engine": "tortoise.backends.sqlite",
                            "credentials": {"file_path": ":memory:"},
                        }
                    },
                    "apps": {"models": {"models": [module], "default_connection": "default"}},
                }
            )
            self.sqls = get_schema_sql(Tortoise._connections["default"], safe).split(";\n")

    def get_sql(self, text: str) -> str:
        return re.sub(r"[ \t\n\r]+", " ", " ".join([sql for sql in self.sqls if text in sql]))

    async def test_noid(self):
        await self.init_for("tests.testmodels")
        sql = self.get_sql('"noid"')
        self.assertIn('"name" VARCHAR(255)', sql)
        self.assertIn('"id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL', sql)

    async def test_minrelation(self):
        await self.init_for("tests.testmodels")
        sql = self.get_sql('"minrelation"')
        self.assertIn(
            '"tournament_id" SMALLINT NOT NULL REFERENCES "tournament" ("id") ON DELETE CASCADE',
            sql,
        )
        self.assertNotIn("participants", sql)

        sql = self.get_sql('"minrelation_team"')
        self.assertIn(
            '"minrelation_id" INT NOT NULL REFERENCES "minrelation" ("id") ON DELETE CASCADE', sql
        )
        self.assertIn('"team_id" INT NOT NULL REFERENCES "team" ("id") ON DELETE CASCADE', sql)

    async def test_safe_generation(self):
        """Assert that the IF NOT EXISTS clause is included when safely generating schema."""
        await self.init_for("tests.testmodels", True)
        sql = self.get_sql("")
        self.assertIn("IF NOT EXISTS", sql)

    async def test_unsafe_generation(self):
        """Assert that the IF NOT EXISTS clause is not included when generating schema."""
        await self.init_for("tests.testmodels", False)
        sql = self.get_sql("")
        self.assertNotIn("IF NOT EXISTS", sql)

    async def test_cyclic(self):
        with self.assertRaisesRegex(
            ConfigurationError, "Can't create schema due to cyclic fk references"
        ):
            await self.init_for("tests.schema.models_cyclic")

    async def test_create_index(self):
        await self.init_for("tests.testmodels")
        sql = self.get_sql("CREATE INDEX")
        self.assertIsNotNone(re.search(r"idx_tournament_created_\w+", sql))

    async def test_fk_bad_model_name(self):
        with self.assertRaisesRegex(
            ConfigurationError, 'Foreign key accepts model name in format "app.Model"'
        ):
            await self.init_for("tests.schema.models_fk_1")

    async def test_fk_bad_on_delete(self):
        with self.assertRaisesRegex(
            ConfigurationError, "on_delete can only be CASCADE, RESTRICT or SET_NULL"
        ):
            await self.init_for("tests.schema.models_fk_2")

    async def test_fk_bad_null(self):
        with self.assertRaisesRegex(
            ConfigurationError, "If on_delete is SET_NULL, then field must have null=True set"
        ):
            await self.init_for("tests.schema.models_fk_3")

    async def test_o2o_bad_on_delete(self):
        with self.assertRaisesRegex(
            ConfigurationError, "on_delete can only be CASCADE, RESTRICT or SET_NULL"
        ):
            await self.init_for("tests.schema.models_o2o_2")

    async def test_o2o_bad_null(self):
        with self.assertRaisesRegex(
            ConfigurationError, "If on_delete is SET_NULL, then field must have null=True set"
        ):
            await self.init_for("tests.schema.models_o2o_3")

    async def test_m2m_bad_model_name(self):
        with self.assertRaisesRegex(
            ConfigurationError, 'Foreign key accepts model name in format "app.Model"'
        ):
            await self.init_for("tests.schema.models_m2m_1")

    async def test_table_and_row_comment_generation(self):
        await self.init_for("tests.testmodels")
        sql = self.get_sql("comments")
        self.assertRegex(sql, r".*\/\* Upvotes done on the comment.*\*\/")
        self.assertRegex(sql, r".*\\n.*")
        self.assertIn("\\/", sql)

    async def test_schema(self):
        self.maxDiff = None
        await self.init_for("tests.schema.models_schema_create")
        sql = get_schema_sql(Tortoise.get_connection("default"), safe=False)
        self.assertEqual(
            sql.strip(),
            """
CREATE TABLE "company" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" TEXT NOT NULL,
    "uuid" CHAR(36) NOT NULL UNIQUE
);
CREATE TABLE "defaultpk" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "val" INT NOT NULL
);
CREATE TABLE "employee" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" TEXT NOT NULL,
    "company_id" CHAR(36) NOT NULL REFERENCES "company" ("uuid") ON DELETE CASCADE
);
CREATE TABLE "inheritedmodel" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "zero" INT NOT NULL,
    "one" VARCHAR(40),
    "new_field" VARCHAR(100) NOT NULL,
    "two" VARCHAR(40) NOT NULL,
    "name" TEXT NOT NULL
);
CREATE TABLE "sometable" (
    "sometable_id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "some_chars_table" VARCHAR(255) NOT NULL,
    "fk_sometable" INT REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE
);
CREATE INDEX "idx_sometable_some_ch_3d69eb" ON "sometable" ("some_chars_table");
CREATE TABLE "team" (
    "name" VARCHAR(50) NOT NULL  PRIMARY KEY /* The TEAM name (and PK) */,
    "key" INT NOT NULL,
    "manager_id" VARCHAR(50) REFERENCES "team" ("name") ON DELETE CASCADE
) /* The TEAMS! */;
CREATE INDEX "idx_team_manager_676134" ON "team" ("manager_id", "key");
CREATE INDEX "idx_team_manager_ef8f69" ON "team" ("manager_id", "name");
CREATE TABLE "teamaddress" (
    "city" VARCHAR(50) NOT NULL  /* City */,
    "country" VARCHAR(50) NOT NULL  /* Country */,
    "street" VARCHAR(128) NOT NULL  /* Street Address */,
    "team_id" VARCHAR(50) NOT NULL  PRIMARY KEY REFERENCES "team" ("name") ON DELETE CASCADE
) /* The Team's address */;
CREATE TABLE "tournament" (
    "tid" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" VARCHAR(100) NOT NULL  /* Tournament name */,
    "created" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP /* Created *\\/'`\\/* datetime */
) /* What Tournaments *\\/'`\\/* we have */;
CREATE INDEX "idx_tournament_name_6fe200" ON "tournament" ("name");
CREATE TABLE "event" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* Event ID */,
    "name" TEXT NOT NULL,
    "modified" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "prize" VARCHAR(40),
    "token" VARCHAR(100) NOT NULL UNIQUE /* Unique token */,
    "key" VARCHAR(100) NOT NULL,
    "tournament_id" SMALLINT NOT NULL REFERENCES "tournament" ("tid") ON DELETE CASCADE /* FK to tournament */,
    CONSTRAINT "uid_event_name_c6f89f" UNIQUE ("name", "prize"),
    CONSTRAINT "uid_event_tournam_a5b730" UNIQUE ("tournament_id", "key")
) /* This table contains a list of all the events */;
CREATE TABLE "venueinformation" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" VARCHAR(128) NOT NULL,
    "capacity" INT NOT NULL  /* No. of seats */,
    "rent" REAL NOT NULL,
    "team_id" VARCHAR(50)  UNIQUE REFERENCES "team" ("name") ON DELETE SET NULL
);
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
) /* How participants relate */;
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
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" TEXT NOT NULL,
    "uuid" CHAR(36) NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS "defaultpk" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "val" INT NOT NULL
);
CREATE TABLE IF NOT EXISTS "employee" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" TEXT NOT NULL,
    "company_id" CHAR(36) NOT NULL REFERENCES "company" ("uuid") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "inheritedmodel" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "zero" INT NOT NULL,
    "one" VARCHAR(40),
    "new_field" VARCHAR(100) NOT NULL,
    "two" VARCHAR(40) NOT NULL,
    "name" TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS "sometable" (
    "sometable_id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "some_chars_table" VARCHAR(255) NOT NULL,
    "fk_sometable" INT REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_sometable_some_ch_3d69eb" ON "sometable" ("some_chars_table");
CREATE TABLE IF NOT EXISTS "team" (
    "name" VARCHAR(50) NOT NULL  PRIMARY KEY /* The TEAM name (and PK) */,
    "key" INT NOT NULL,
    "manager_id" VARCHAR(50) REFERENCES "team" ("name") ON DELETE CASCADE
) /* The TEAMS! */;
CREATE INDEX IF NOT EXISTS "idx_team_manager_676134" ON "team" ("manager_id", "key");
CREATE INDEX IF NOT EXISTS "idx_team_manager_ef8f69" ON "team" ("manager_id", "name");
CREATE TABLE IF NOT EXISTS "teamaddress" (
    "city" VARCHAR(50) NOT NULL  /* City */,
    "country" VARCHAR(50) NOT NULL  /* Country */,
    "street" VARCHAR(128) NOT NULL  /* Street Address */,
    "team_id" VARCHAR(50) NOT NULL  PRIMARY KEY REFERENCES "team" ("name") ON DELETE CASCADE
) /* The Team's address */;
CREATE TABLE IF NOT EXISTS "tournament" (
    "tid" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" VARCHAR(100) NOT NULL  /* Tournament name */,
    "created" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP /* Created *\\/'`\\/* datetime */
) /* What Tournaments *\\/'`\\/* we have */;
CREATE INDEX IF NOT EXISTS "idx_tournament_name_6fe200" ON "tournament" ("name");
CREATE TABLE IF NOT EXISTS "event" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* Event ID */,
    "name" TEXT NOT NULL,
    "modified" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "prize" VARCHAR(40),
    "token" VARCHAR(100) NOT NULL UNIQUE /* Unique token */,
    "key" VARCHAR(100) NOT NULL,
    "tournament_id" SMALLINT NOT NULL REFERENCES "tournament" ("tid") ON DELETE CASCADE /* FK to tournament */,
    CONSTRAINT "uid_event_name_c6f89f" UNIQUE ("name", "prize"),
    CONSTRAINT "uid_event_tournam_a5b730" UNIQUE ("tournament_id", "key")
) /* This table contains a list of all the events */;
CREATE TABLE IF NOT EXISTS "venueinformation" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" VARCHAR(128) NOT NULL,
    "capacity" INT NOT NULL  /* No. of seats */,
    "rent" REAL NOT NULL,
    "team_id" VARCHAR(50)  UNIQUE REFERENCES "team" ("name") ON DELETE SET NULL
);
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
) /* How participants relate */;
""".strip(),
        )
